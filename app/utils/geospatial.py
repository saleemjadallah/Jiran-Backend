"""Geospatial utility functions using PostGIS.

This module provides utilities for working with geographic data:
- Distance calculations
- Coordinate conversions
- Point creation for PostGIS
- Spatial queries
"""
import math
from typing import Any

from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import literal_column

from app.models.product import Product


def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points using Haversine formula.

    Args:
        lat1: Latitude of first point
        lng1: Longitude of first point
        lat2: Latitude of second point
        lng2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_distance_label(distance_km: float) -> str:
    """Get human-readable distance label.

    Args:
        distance_km: Distance in kilometers

    Returns:
        Human-readable distance label
    """
    if distance_km < 0.1:
        return "Same building"
    elif distance_km < 0.5:
        return "Walking distance"
    elif distance_km < 2:
        return "Same neighborhood"
    elif distance_km < 5:
        return "Nearby"
    else:
        return f"{distance_km:.1f} km away"


def point_from_coordinates(latitude: float, longitude: float) -> str:
    """Create PostGIS POINT geometry from lat/lng coordinates.

    Args:
        latitude: Latitude (-90 to 90)
        longitude: Longitude (-180 to 180)

    Returns:
        WKT format: "POINT(lng lat)"

    Note:
        PostGIS uses (longitude, latitude) order, not (latitude, longitude)
    """
    if not validate_coordinates(latitude, longitude):
        raise ValueError("Invalid coordinates")

    return f"POINT({longitude} {latitude})"


def point_to_coordinates(point_wkt: str) -> tuple[float, float]:
    """Extract lat/lng from PostGIS POINT WKT string.

    Args:
        point_wkt: WKT format "POINT(lng lat)"

    Returns:
        Tuple of (latitude, longitude)
    """
    # Remove "POINT(" and ")" and split
    coords = point_wkt.replace("POINT(", "").replace(")", "").split()
    longitude = float(coords[0])
    latitude = float(coords[1])
    return (latitude, longitude)


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate geographic coordinates.

    Args:
        latitude: Latitude value
        longitude: Longitude value

    Returns:
        True if valid, False otherwise
    """
    return -90 <= latitude <= 90 and -180 <= longitude <= 180


async def get_products_within_radius(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float,
    filters: dict[str, Any] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[tuple[Product, float]]:
    """Query products within radius using PostGIS ST_DWithin.

    Args:
        db: Database session
        latitude: Center point latitude
        longitude: Center point longitude
        radius_km: Search radius in kilometers
        filters: Optional filters (category, feed_type, etc.)
        limit: Maximum results to return
        offset: Pagination offset

    Returns:
        List of (Product, distance_km) tuples ordered by distance
    """
    if not validate_coordinates(latitude, longitude):
        raise ValueError("Invalid coordinates")

    # Convert km to meters for PostGIS
    radius_m = radius_km * 1000

    # Create point using ST_MakePoint (longitude, latitude)
    user_point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

    # Build query with distance calculation
    query = select(
        Product,
        # ST_Distance returns meters, divide by 1000 for km
        (ST_Distance(cast(Product.location, "geography"), cast(user_point, "geography")) / 1000).label(
            "distance_km"
        ),
    ).where(
        # ST_DWithin for efficient spatial filtering
        ST_DWithin(cast(Product.location, "geography"), cast(user_point, "geography"), radius_m),
        Product.is_available == True,  # noqa: E712
    )

    # Apply additional filters
    if filters:
        if "category" in filters:
            query = query.where(Product.category == filters["category"])
        if "feed_type" in filters:
            query = query.where(Product.feed_type == filters["feed_type"])
        if "min_price" in filters:
            query = query.where(Product.price >= filters["min_price"])
        if "max_price" in filters:
            query = query.where(Product.price <= filters["max_price"])
        if "condition" in filters:
            query = query.where(Product.condition == filters["condition"])

    # Order by distance and apply pagination
    query = query.order_by(literal_column("distance_km")).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.all()
