"""Common response envelope and shared schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard JSON envelope for all API responses."""

    data: T
    meta: dict[str, Any] = {}


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
