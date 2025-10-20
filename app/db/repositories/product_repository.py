"""Product repository with cache integration.

Provides product-specific queries with automatic Redis caching:
- Get by seller
- Search with full-text
- Filter by category/feed type
- Cache invalidation for feeds, search, and seller pages
"""

import hashlib
import json
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.cache_keys import CacheKeys
from app.core.cache.redis_manager import RedisManager
from app.db.repositories.base_repository import BaseRepository
from app.models.product import FeedType, Product, ProductCategory


class ProductRepository(BaseRepository[Product]):
    """Product repository with cache-aware queries.

    Extends BaseRepository with product-specific methods:
    - get_by_seller(): Get seller's products with pagination
    - search(): Full-text search with filters
    - get_by_category(): Get products by category and feed type
    - get_available(): Get only available (not sold) products
    """

    def __init__(self, db: AsyncSession, redis: RedisManager):
        """Initialize product repository.

        Args:
            db: SQLAlchemy async session
            redis: Redis manager instance
        """
        super().__init__(
            db=db,
            redis=redis,
            model=Product,
            cache_prefix="product",
            default_ttl=900,  # 15 minutes for products
        )

    async def get_by_seller(
        self,
        seller_id: UUID | str,
        offset: int = 0,
        limit: int = 20,
        use_cache: bool = True,
    ) -> List[Product]:
        """Get products by seller with caching.

        Args:
            seller_id: Seller's user ID
            offset: Pagination offset
            limit: Page size
            use_cache: Whether to use cache

        Returns:
            List of products
        """
        seller_id_str = str(seller_id)
        cache_key = CacheKeys.seller_products(seller_id_str, page=offset // limit)

        # Check cache
        if use_cache:
            cached = await self.redis.get(cache_key)
            if cached:
                # Cached IDs only, fetch full entities
                product_ids = cached
                return await self.get_many(product_ids, use_cache=True)

        # Query DB
        result = await self.db.execute(
            select(Product)
            .filter(Product.seller_id == seller_id)
            .filter(Product.is_available == True)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        products = list(result.scalars().all())

        # Cache product IDs
        if use_cache and products:
            product_ids = [str(p.id) for p in products]
            await self.redis.set(cache_key, product_ids, ttl=600)  # 10 min

        return products

    async def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        offset: int = 0,
        limit: int = 20,
        use_cache: bool = True,
    ) -> List[Product]:
        """Full-text search with caching.

        Args:
            query: Search query string
            filters: Optional filters (category, min_price, max_price, etc.)
            offset: Pagination offset
            limit: Page size
            use_cache: Whether to use cache

        Returns:
            List of matching products
        """
        # Build cache key
        cache_data = {
            "query": query.lower().strip(),
            "filters": filters or {},
            "offset": offset,
            "limit": limit,
        }
        cache_hash = hashlib.md5(
            json.dumps(cache_data, sort_keys=True).encode()
        ).hexdigest()[:12]
        cache_key = f"search:results:{cache_hash}"

        # Check cache
        if use_cache:
            cached = await self.redis.get(cache_key)
            if cached:
                # Return cached product IDs, fetch full entities
                product_ids = cached
                return await self.get_many(product_ids, use_cache=True)

        # Build query (simplified - would use full-text search in production)
        stmt = select(Product).filter(
            Product.title.ilike(f"%{query}%") | Product.description.ilike(f"%{query}%")
        )

        # Apply filters
        if filters:
            if "category" in filters:
                stmt = stmt.filter(Product.category == filters["category"])
            if "feed_type" in filters:
                stmt = stmt.filter(Product.feed_type == filters["feed_type"])
            if "min_price" in filters:
                stmt = stmt.filter(Product.price >= filters["min_price"])
            if "max_price" in filters:
                stmt = stmt.filter(Product.price <= filters["max_price"])

        stmt = stmt.filter(Product.is_available == True)
        stmt = stmt.offset(offset).limit(limit)

        # Execute
        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        # Cache results (IDs only)
        if use_cache and products:
            product_ids = [str(p.id) for p in products]
            await self.redis.set(cache_key, product_ids, ttl=600)  # 10 min

        return products

    async def get_by_category(
        self,
        category: ProductCategory,
        feed_type: Optional[FeedType] = None,
        offset: int = 0,
        limit: int = 20,
        use_cache: bool = True,
    ) -> List[Product]:
        """Get products by category and feed type.

        Args:
            category: Product category
            feed_type: Optional feed type (discover/community)
            offset: Pagination offset
            limit: Page size
            use_cache: Whether to use cache

        Returns:
            List of products in category
        """
        page = offset // limit
        cache_key = CacheKeys.category_products(category.value, page)

        # Check cache
        if use_cache:
            cached = await self.redis.get(cache_key)
            if cached:
                product_ids = cached
                return await self.get_many(product_ids, use_cache=True)

        # Query DB
        stmt = select(Product).filter(Product.category == category)

        if feed_type:
            stmt = stmt.filter(Product.feed_type == feed_type)

        stmt = (
            stmt.filter(Product.is_available == True)
            .order_by(Product.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        products = list(result.scalars().all())

        # Cache results
        if use_cache and products:
            product_ids = [str(p.id) for p in products]
            await self.redis.set(cache_key, product_ids, ttl=600)  # 10 min

        return products

    async def get_available(
        self,
        feed_type: Optional[FeedType] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Product]:
        """Get available (not sold) products.

        Args:
            feed_type: Optional feed type filter
            offset: Pagination offset
            limit: Page size

        Returns:
            List of available products
        """
        stmt = select(Product).filter(Product.is_available == True)

        if feed_type:
            stmt = stmt.filter(Product.feed_type == feed_type)

        stmt = stmt.order_by(Product.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ========== Cache Invalidation ==========

    async def _invalidate_related_caches(self, entity: Product) -> None:
        """Invalidate product-related caches.

        Clears:
        - Product detail cache
        - Feed caches (product appears in feeds)
        - Seller's product list
        - Search results
        - Category caches

        Args:
            entity: Product instance
        """
        # Specific product cache
        await self.redis.delete(f"product:{entity.id}")

        # Feed caches (product may appear in discover/community feeds)
        await self.redis.delete_pattern("feed:*")

        # Seller's products
        await self.redis.delete_pattern(
            CacheKeys.seller_products_pattern(str(entity.seller_id))
        )

        # Search caches
        await self.redis.delete_pattern("search:results:*")

        # Category caches
        await self.redis.delete_pattern(CacheKeys.category_pattern(entity.category.value))

        # List caches (from base repository)
        await self.redis.delete_pattern("product:list:*")
