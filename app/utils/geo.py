from dataclasses import dataclass
from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point


@dataclass
class Coordinates:
    latitude: float
    longitude: float


def point_from_coordinates(latitude: float, longitude: float) -> WKBElement:
    point = Point(float(longitude), float(latitude))
    return from_shape(point, srid=4326)


def point_to_coordinates(geom: Any) -> Coordinates | None:
    if not geom:
        return None
    shape = to_shape(geom)
    return Coordinates(latitude=shape.y, longitude=shape.x)

