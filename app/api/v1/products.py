"""Product CRUD endpoints for marketplace listings.

This module provides endpoints for:
- Creating new product listings
- Retrieving product details
- Updating products (owner/admin only)
- Deleting products (soft delete)
- Finding similar products
- Marking products as sold
"""
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_active_user, get_db, require_admin_role, require_seller_role
from app.models.product import Product
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductDetailResponse,
    ProductLocation,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.user import UserResponse
from app.utils.geospatial import calculate_distance, point_from_coordinates

router = APIRouter(prefix="/products", tags=["products"])

# Product limit per user
MAX_PRODUCTS_PER_USER = 50


def _convert_product_to_response(product: Product, requester_location: ProductLocation | None = None) -> dict:
    """Convert Product model to response dict with seller info and location.

    Args:
        product: Product model instance
        requester_location: Optional requester's location for distance calculation

    Returns:
        Dictionary with product data, seller info, and location
    """
    # Convert location from PostGIS to coordinates
    location_data = None
    if product.location:
        point = to_shape(product.location)
        location_data = {
            "latitude": point.y,
            "longitude": point.x,
            "neighborhood": product.neighborhood,
            "building_name": None,  # Building name not stored at product level
        }

        # Calculate distance if requester location provided
        if requester_location:
            distance_km = calculate_distance(
                requester_location.latitude,
                requester_location.longitude,
                point.y,
                point.x,
            )
            location_data["distance_km"] = round(distance_km, 2)

    # Construct response
    return {
        "id": str(product.id),
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "original_price": product.original_price,
        "currency": product.currency,
        "category": product.category,
        "condition": product.condition,
        "feed_type": product.feed_type,
        "neighborhood": product.neighborhood,
        "is_available": product.is_available,
        "view_count": product.view_count,
        "like_count": product.like_count,
        "image_urls": product.image_urls,
        "video_url": product.video_url,
        "video_thumbnail_url": product.video_thumbnail_url,
        "tags": product.tags,
        "sold_at": product.sold_at,
        "seller": UserResponse.model_validate(product.seller),
        "location": location_data,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_seller_role)],
):
    """Create new product listing.

    Requires seller role. Validates product count limit and creates new listing.

    Args:
        product_data: Product creation data
        session: Database session
        current_user: Authenticated user with seller role

    Returns:
        Created product with ID and platform fee information

    Raises:
        HTTPException 403: If product limit exceeded
    """
    # Check product limit
    count_result = await session.execute(
        select(func.count()).select_from(Product).where(Product.seller_id == current_user.id)
    )
    product_count = count_result.scalar_one()

    if product_count >= MAX_PRODUCTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Maximum of {MAX_PRODUCTS_PER_USER} products allowed per user",
        )

    # Location temporarily disabled (PostGIS not available)
    # TODO: Re-enable when Google Maps API is integrated
    location_str = None
    neighborhood = None
    if product_data.location:
        # Store as WKT string for now
        location_str = f"POINT({product_data.location.longitude} {product_data.location.latitude})"
        neighborhood = product_data.location.neighborhood

    # Create product
    new_product = Product(
        seller_id=current_user.id,
        title=product_data.title,
        description=product_data.description,
        price=product_data.price,
        original_price=product_data.original_price,
        currency=product_data.currency,
        category=product_data.category,
        condition=product_data.condition,
        feed_type=product_data.feed_type,
        location=location_str,  # Store as WKT string, not PostGIS geometry
        neighborhood=neighborhood,
        image_urls=product_data.image_urls,
        video_url=product_data.video_url,
        video_thumbnail_url=product_data.video_thumbnail_url,
        tags=[tag.model_dump() for tag in product_data.tags],
    )

    session.add(new_product)
    await session.commit()
    await session.refresh(new_product, ["seller"])

    return ProductResponse(**_convert_product_to_response(new_product))


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
):
    """Get product details by ID.

    Increments view count and calculates distance from requester if authenticated.

    Args:
        product_id: Product UUID
        session: Database session
        current_user: Optional authenticated user

    Returns:
        Product details with seller info, location, and similar products

    Raises:
        HTTPException 404: If product not found
    """
    # Fetch product with seller relationship
    result = await session.execute(
        select(Product).options(selectinload(Product.seller)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Increment view count
    product.view_count += 1
    await session.commit()

    # Get requester location for distance calculation
    requester_location = None
    if current_user and current_user.location:
        user_point = to_shape(current_user.location)
        requester_location = ProductLocation(
            latitude=user_point.y,
            longitude=user_point.x,
            neighborhood=current_user.neighborhood,
        )

    # Find similar products
    similar_query = (
        select(Product.id)
        .where(
            and_(
                Product.id != product_id,
                Product.category == product.category,
                Product.is_available == True,  # noqa: E712
                Product.price.between(product.price * 0.7, product.price * 1.3),
            )
        )
        .limit(10)
    )

    # Add location filter if product has location
    if product.location:
        # Find products within 5km
        similar_query = similar_query.where(
            func.ST_DWithin(
                func.cast(Product.location, "geography"),
                func.cast(product.location, "geography"),
                5000,  # 5km in meters
            )
        )

    similar_result = await session.execute(similar_query)
    similar_product_ids = [str(row[0]) for row in similar_result.all()]

    # Construct response
    response_data = _convert_product_to_response(product, requester_location)
    response_data["related_products"] = similar_product_ids

    return ProductDetailResponse(**response_data)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    update_data: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Update product listing.

    Only owner or admin can update. Cannot change feed_type after creation.

    Args:
        product_id: Product UUID
        update_data: Fields to update
        session: Database session
        current_user: Authenticated user

    Returns:
        Updated product data

    Raises:
        HTTPException 404: If product not found
        HTTPException 403: If not owner or admin
        HTTPException 400: If trying to change feed_type
    """
    # Fetch product
    result = await session.execute(
        select(Product).options(selectinload(Product.seller)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate ownership
    if product.seller_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this product")

    # Validate feed_type cannot change
    if update_data.feed_type and update_data.feed_type != product.feed_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change feed_type after creation"
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    # Handle location update
    if "location" in update_dict and update_dict["location"]:
        loc_data = update_dict.pop("location")
        point = Point(loc_data["longitude"], loc_data["latitude"])
        product.location = from_shape(point, srid=4326)
        product.neighborhood = loc_data.get("neighborhood")

    # Update other fields
    for field, value in update_dict.items():
        if field == "tags" and value is not None:
            # Convert tag objects to dicts
            setattr(product, field, [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in value])
        else:
            setattr(product, field, value)

    await session.commit()
    await session.refresh(product, ["seller"])

    return ProductResponse(**_convert_product_to_response(product))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Soft delete product (set is_available = false).

    Only owner or admin can delete. Cannot delete if active transactions exist.

    Args:
        product_id: Product UUID
        session: Database session
        current_user: Authenticated user

    Raises:
        HTTPException 404: If product not found
        HTTPException 403: If not owner or admin
        HTTPException 400: If active transactions exist
    """
    # Fetch product
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate ownership
    if product.seller_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this product")

    # Check for active transactions
    tx_result = await session.execute(
        select(Transaction).where(
            and_(
                Transaction.product_id == product_id,
                Transaction.status.in_(["pending", "processing"]),
            )
        )
    )
    active_transactions = tx_result.scalar_one_or_none()

    if active_transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete product with active transactions",
        )

    # Soft delete
    product.is_available = False
    await session.commit()


@router.get("/{product_id}/similar", response_model=list[ProductResponse])
async def get_similar_products(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_active_user)] = None,
):
    """Find similar products based on category, price, and location.

    Finds products in same category, similar price range (±30%), and nearby (within 5km).

    Args:
        product_id: Product UUID
        session: Database session
        current_user: Optional authenticated user

    Returns:
        List of similar products (max 10)

    Raises:
        HTTPException 404: If product not found
    """
    # Fetch original product
    result = await session.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Build similar products query
    query = (
        select(Product)
        .options(selectinload(Product.seller))
        .where(
            and_(
                Product.id != product_id,
                Product.category == product.category,
                Product.is_available == True,  # noqa: E712
                Product.price.between(product.price * 0.7, product.price * 1.3),
            )
        )
        .limit(10)
    )

    # Add location filter if available
    if product.location:
        query = query.where(
            func.ST_DWithin(
                func.cast(Product.location, "geography"),
                func.cast(product.location, "geography"),
                5000,  # 5km
            )
        )

    # Order by relevance (price similarity)
    query = query.order_by(func.abs(Product.price - product.price))

    result = await session.execute(query)
    similar_products = result.scalars().all()

    # Get requester location
    requester_location = None
    if current_user and current_user.location:
        user_point = to_shape(current_user.location)
        requester_location = ProductLocation(
            latitude=user_point.y,
            longitude=user_point.x,
        )

    return [
        ProductResponse(**_convert_product_to_response(p, requester_location)) for p in similar_products
    ]


@router.patch("/{product_id}/mark-sold", response_model=ProductResponse)
async def mark_product_sold(
    product_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """Mark product as sold.

    Sets sold_at timestamp and is_available = false.
    Notifies interested users (future implementation).

    Args:
        product_id: Product UUID
        session: Database session
        current_user: Authenticated user

    Returns:
        Updated product data

    Raises:
        HTTPException 404: If product not found
        HTTPException 403: If not owner or admin
        HTTPException 400: If already sold
    """
    # Fetch product
    result = await session.execute(
        select(Product).options(selectinload(Product.seller)).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate ownership
    if product.seller_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to mark this product as sold"
        )

    # Check if already sold
    if product.sold_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already marked as sold")

    # Mark as sold
    product.sold_at = datetime.now()
    product.is_available = False

    await session.commit()
    await session.refresh(product, ["seller"])

    # TODO: Notify interested users (who messaged or made offers)
    # This will be implemented in Phase 3 (Messaging & Offers)

    return ProductResponse(**_convert_product_to_response(product))
