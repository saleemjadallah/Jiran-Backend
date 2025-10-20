from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SuccessResponse(BaseModel, Generic[T]):
    """Generic success response wrapper."""

    success: bool = True
    data: T


class APIResponse(BaseModel, Generic[T]):
    """API response wrapper with success flag, data, and optional message."""

    success: bool = True
    data: T
    message: Optional[str] = None


class StandardResponse(BaseModel, Generic[T]):
    """Standard API response with success, data, and message."""

    success: bool = True
    data: T
    message: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response with success, data, pagination info, and message."""

    success: bool = True
    data: T
    page: int
    per_page: int
    total: int
    message: Optional[str] = None

    @property
    def total_pages(self) -> int:
        """Calculate total pages"""
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        """Check if there's a next page"""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page"""
        return self.page > 1

