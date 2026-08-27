from datetime import datetime

from sqlmodel import SQLModel
from pydantic import ConfigDict, Field

from app.schemas.pagination import PaginationParams
from app.schemas.knowledge_space import KnowledgeSpaceRead, KnowledgeSpaceReadDetail
from app.enums import TenantSortField, SortDirection


class TenantQueryParams(PaginationParams):
    name: str | None = None
    description: str | None = None
    roles: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None

    include_knowledge_spaces: bool = False
    include_deleted: bool = False

    sort_by: TenantSortField = TenantSortField.ID
    sort_order: SortDirection = SortDirection.ASC


class TenantRead(SQLModel):
    id: int
    name: str
    description: str | None
    is_global_retrieval: bool
    roles: list[str]

    model_config = ConfigDict(from_attributes=True)

class TenantReadDetails(TenantRead):
    created_at: datetime
    created_by: str
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None


class TenantReadDetailsWithKnowledgeSpaces(TenantReadDetails):
    knowledge_spaces: list[KnowledgeSpaceRead] = Field(default_factory=list)


class TenantCreate(SQLModel):
    name: str = Field(min_length=1)
    description: str | None = Field(default=None)
    is_global_retrieval: bool = Field(default=False)
    roles: list[str] = Field(min_length=1)


class TenantUpdate(SQLModel):
    description: str | None = Field(default=None, max_length=255)
    is_global_retrieval: bool | None = Field(default=None)
    roles: list[str] | None = Field(default=None, min_length=1)


KnowledgeSpaceReadDetail.model_rebuild()