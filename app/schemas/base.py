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

