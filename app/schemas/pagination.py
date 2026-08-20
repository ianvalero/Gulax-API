from pydantic import BaseModel, Field
from typing import Generic, TypeVar


class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class Pagination(BaseModel):
    offset: int
    limit: int
    total: int
    has_next: bool
    has_prev: bool

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: Pagination