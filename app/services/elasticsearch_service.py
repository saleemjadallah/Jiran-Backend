"""
Elasticsearch service for advanced search capabilities.
Provides full-text search, geospatial queries, autocomplete, and faceted search.
"""

from typing import Dict, List, Optional, Tuple
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
import logging
from datetime import datetime

from app.models.product import Product
from app.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Service for Elasticsearch operations"""

    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.index_name = "products"

    async def connect(self):
        """Initialize Elasticsearch connection"""
        try:
            self.client = AsyncElasticsearch(
                [settings.ELASTICSEARCH_URL],
                verify_certs=False,
                ssl_show_warn=False,
            )
            # Test connection
            await self.client.ping()
            logger.info("Connected to Elasticsearch")

            # Create index if it doesn't exist
            if not await self.client.indices.exists(index=self.index_name):
                await self._create_index()
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            self.client = None

    async def disconnect(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Elasticsearch")

    async def _create_index(self):
        """Create products index with mapping and analyzer"""
        mapping = {
            "settings": {
                "analysis": {
                    "analyzer": {
                        "autocomplete": {
                            "tokenizer": "autocomplete_tokenizer",
                            "filter": ["lowercase"]
                        },
                        "autocomplete_search": {
                            "tokenizer": "lowercase"
                        }
                    },
                    "tokenizer": {
                        "autocomplete_tokenizer": {
                            "type": "edge_ngram",
                            "min_gram": 2,
                            "max_gram": 10,
                            "token_chars": ["letter", "digit"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "autocomplete": {
                                "type": "text",
                                "analyzer": "autocomplete",
                                "search_analyzer": "autocomplete_search"
                            }
                        }
                    },
                    "description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "price": {"type": "float"},
                    "currency": {"type": "keyword"},
                    "category": {"type": "keyword"},
                    "condition": {"type": "keyword"},
                    "feed_type": {"type": "keyword"},
                    "location": {"type": "geo_point"},
                    "neighborhood": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "seller": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "username": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword"}
                                }
                            },
                            "is_verified": {"type": "boolean"},
                            "rating": {"type": "float"}
                        }
                    },
                    "is_available": {"type": "boolean"},
                    "view_count": {"type": "integer"},
                    "like_count": {"type": "integer"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

        await self.client.indices.create(
            index=self.index_name,
            body=mapping
        )
        logger.info(f"Created Elasticsearch index: {self.index_name}")

    async def index_product(self, product: Product) -> bool:
        """
        Index a single product in Elasticsearch

        Args:
            product: Product model instance

        Returns:
            bool: Success status
        """
        if not self.client:
            logger.warning("Elasticsearch not connected")
            return False

        try:
            # Convert product to Elasticsearch document
            doc = {
                "id": str(product.id),
                "title": product.title,
                "description": product.description,
                "price": float(product.price),
                "currency": product.currency,
                "category": product.category,
                "condition": product.condition,
                "feed_type": product.feed_type,
                "neighborhood": product.neighborhood,
                "tags": product.tags or [],
                "seller": {
                    "id": str(product.seller_id),
                    "username": product.seller.username if product.seller else None,
                    "is_verified": product.seller.is_verified if product.seller else False,
                    "rating": float(product.seller.rating) if product.seller and product.seller.rating else 0.0
                },
                "is_available": product.is_available,
                "view_count": product.view_count,
                "like_count": product.like_count,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            }

            # Add location if available
            if product.location:
                # PostGIS Point format: POINT(lng lat)
                # Elasticsearch expects: {"lat": y, "lon": x}
                coords = product.location.split("(")[1].split(")")[0].split()
                doc["location"] = {
                    "lat": float(coords[1]),
                    "lon": float(coords[0])
                }

            await self.client.index(
                index=self.index_name,
                id=str(product.id),
                document=doc
            )
            logger.debug(f"Indexed product: {product.id}")
            return True

        except Exception as e:
            logger.error(f"Error indexing product {product.id}: {e}")
            return False

    async def update_product(self, product_id: str, fields: Dict) -> bool:
        """
        Update specific fields of a product document

        Args:
            product_id: Product ID
            fields: Dictionary of fields to update

        Returns:
            bool: Success status
        """
        if not self.client:
            return False

        try:
            await self.client.update(
                index=self.index_name,
                id=product_id,
                doc=fields
            )
            logger.debug(f"Updated product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating product {product_id}: {e}")
            return False

    async def delete_product(self, product_id: str) -> bool:
        """
        Remove product from index

        Args:
            product_id: Product ID

        Returns:
            bool: Success status
        """
        if not self.client:
            return False

        try:
            await self.client.delete(
                index=self.index_name,
                id=product_id
            )
            logger.debug(f"Deleted product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting product {product_id}: {e}")
            return False

    async def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        location: Optional[Tuple[float, float]] = None,
        radius_km: Optional[float] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = "relevance"
    ) -> Dict:
        """
        Perform advanced search with filters

        Args:
            query: Search query string
            filters: Filter criteria (category, condition, price range, etc.)
            location: (latitude, longitude) tuple for geospatial search
            radius_km: Search radius in kilometers
            page: Page number (1-indexed)
            per_page: Results per page
            sort_by: Sort criteria (relevance, recent, price_low, price_high, nearest)

        Returns:
            dict: Search results with hits, facets, and metadata
        """
        if not self.client:
            return {"hits": [], "total": 0, "facets": {}}

        try:
            # Build query
            must_clauses = []
            filter_clauses = []

            # Full-text search
            if query and query.strip():
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",  # Boost title matches
                            "title.autocomplete^2",
                            "description",
                            "seller.username",
                            "tags^2"
                        ],
                        "fuzziness": "AUTO",
                        "operator": "or"
                    }
                })

            # Always filter by available products
            filter_clauses.append({"term": {"is_available": True}})

            # Apply filters
            if filters:
                # Category filter
                if filters.get("category"):
                    filter_clauses.append({"term": {"category": filters["category"]}})

                # Condition filter
                if filters.get("condition"):
                    if isinstance(filters["condition"], list):
                        filter_clauses.append({"terms": {"condition": filters["condition"]}})
                    else:
                        filter_clauses.append({"term": {"condition": filters["condition"]}})

                # Feed type filter
                if filters.get("feed_type"):
                    filter_clauses.append({"term": {"feed_type": filters["feed_type"]}})

                # Price range filter
                if filters.get("min_price") is not None or filters.get("max_price") is not None:
                    price_range = {}
                    if filters.get("min_price") is not None:
                        price_range["gte"] = filters["min_price"]
                    if filters.get("max_price") is not None:
                        price_range["lte"] = filters["max_price"]
                    filter_clauses.append({"range": {"price": price_range}})

                # Verified sellers only
                if filters.get("verified_sellers_only"):
                    filter_clauses.append({"term": {"seller.is_verified": True}})

                # Neighborhood filter
                if filters.get("neighborhood"):
                    filter_clauses.append({"term": {"neighborhood": filters["neighborhood"]}})

            # Geospatial filter
            if location and radius_km:
                filter_clauses.append({
                    "geo_distance": {
                        "distance": f"{radius_km}km",
                        "location": {
                            "lat": location[0],
                            "lon": location[1]
                        }
                    }
                })

            # Build complete query
            body = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses
                    }
                },
                "from": (page - 1) * per_page,
                "size": per_page
            }

            # Sorting
            if sort_by == "recent":
                body["sort"] = [{"created_at": "desc"}]
            elif sort_by == "price_low":
                body["sort"] = [{"price": "asc"}]
            elif sort_by == "price_high":
                body["sort"] = [{"price": "desc"}]
            elif sort_by == "nearest" and location:
                body["sort"] = [{
                    "_geo_distance": {
                        "location": {
                            "lat": location[0],
                            "lon": location[1]
                        },
                        "order": "asc",
                        "unit": "km"
                    }
                }]
            else:  # relevance (default)
                body["sort"] = ["_score"]

            # Add aggregations for facets
            body["aggs"] = {
                "categories": {
                    "terms": {"field": "category", "size": 20}
                },
                "conditions": {
                    "terms": {"field": "condition", "size": 10}
                },
                "price_ranges": {
                    "range": {
                        "field": "price",
                        "ranges": [
                            {"key": "under_100", "to": 100},
                            {"key": "100_500", "from": 100, "to": 500},
                            {"key": "500_1000", "from": 500, "to": 1000},
                            {"key": "1000_5000", "from": 1000, "to": 5000},
                            {"key": "5000_10000", "from": 5000, "to": 10000},
                            {"key": "over_10000", "from": 10000}
                        ]
                    }
                }
            }

            # Execute search
            response = await self.client.search(
                index=self.index_name,
                body=body
            )

            # Format results
            hits = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                result = {
                    "id": source["id"],
                    "title": source["title"],
                    "description": source.get("description"),
                    "price": source["price"],
                    "currency": source.get("currency", "AED"),
                    "category": source["category"],
                    "condition": source["condition"],
                    "feed_type": source["feed_type"],
                    "neighborhood": source.get("neighborhood"),
                    "seller": source.get("seller"),
                    "is_available": source.get("is_available", True),
                    "view_count": source.get("view_count", 0),
                    "like_count": source.get("like_count", 0),
                    "created_at": source.get("created_at"),
                    "score": hit["_score"]
                }

                # Add distance if geospatial sort
                if sort_by == "nearest" and "sort" in hit:
                    result["distance_km"] = round(hit["sort"][0], 2)

                hits.append(result)

            # Format facets
            facets = {
                "categories": [
                    {"key": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["categories"]["buckets"]
                ],
                "conditions": [
                    {"key": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["conditions"]["buckets"]
                ],
                "price_ranges": [
                    {"key": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["price_ranges"]["buckets"]
                ]
            }

            return {
                "hits": hits,
                "total": response["hits"]["total"]["value"],
                "page": page,
                "per_page": per_page,
                "facets": facets,
                "took_ms": response["took"]
            }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"hits": [], "total": 0, "facets": {}}

    async def autocomplete(
        self,
        query: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get autocomplete suggestions

        Args:
            query: Partial search query
            limit: Maximum number of suggestions

        Returns:
            list: Autocomplete suggestions
        """
        if not self.client or not query or len(query) < 2:
            return []

        try:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "title.autocomplete": {
                                        "query": query,
                                        "operator": "and"
                                    }
                                }
                            }
                        ],
                        "filter": [
                            {"term": {"is_available": True}}
                        ]
                    }
                },
                "size": limit,
                "_source": ["title"]
            }

            response = await self.client.search(
                index=self.index_name,
                body=body
            )

            suggestions = []
            seen = set()
            for hit in response["hits"]["hits"]:
                title = hit["_source"]["title"]
                if title not in seen:
                    suggestions.append(title)
                    seen.add(title)

            return suggestions

        except Exception as e:
            logger.error(f"Autocomplete error: {e}")
            return []

    async def bulk_index_products(self, products: List[Product]) -> Tuple[int, int]:
        """
        Bulk index multiple products

        Args:
            products: List of Product instances

        Returns:
            tuple: (success_count, error_count)
        """
        if not self.client:
            return 0, len(products)

        try:
            actions = []
            for product in products:
                doc = {
                    "_index": self.index_name,
                    "_id": str(product.id),
                    "_source": {
                        "id": str(product.id),
                        "title": product.title,
                        "description": product.description,
                        "price": float(product.price),
                        "currency": product.currency,
                        "category": product.category,
                        "condition": product.condition,
                        "feed_type": product.feed_type,
                        "neighborhood": product.neighborhood,
                        "tags": product.tags or [],
                        "seller": {
                            "id": str(product.seller_id),
                            "username": product.seller.username if product.seller else None,
                            "is_verified": product.seller.is_verified if product.seller else False,
                            "rating": float(product.seller.rating) if product.seller and product.seller.rating else 0.0
                        },
                        "is_available": product.is_available,
                        "view_count": product.view_count,
                        "like_count": product.like_count,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None
                    }
                }

                # Add location if available
                if product.location:
                    coords = product.location.split("(")[1].split(")")[0].split()
                    doc["_source"]["location"] = {
                        "lat": float(coords[1]),
                        "lon": float(coords[0])
                    }

                actions.append(doc)

            success, errors = await async_bulk(self.client, actions)
            logger.info(f"Bulk indexed {success} products, {len(errors)} errors")
            return success, len(errors)

        except Exception as e:
            logger.error(f"Bulk index error: {e}")
            return 0, len(products)


# Global Elasticsearch service instance
elasticsearch_service = ElasticsearchService()
