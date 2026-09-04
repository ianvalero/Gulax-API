from datetime import datetime

from sqlmodel import SQLModel
from pydantic import ConfigDict, Field

from app.schemas.pagination import PaginationParams
from app.enums import KnowledgeSpaceSortField, SortDirection


class KnowledgeSpaceRetrievableQueryParams(PaginationParams):
    tenant_id: int | None = Field(default=None, gt=0)
    name: str | None = None
    description: str | None = None

    sort_by: KnowledgeSpaceSortField = KnowledgeSpaceSortField.ID
    sort_order: SortDirection = SortDirection.ASC

class KnowledgeSpaceQueryParams(KnowledgeSpaceRetrievableQueryParams):
    roles: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    include_deleted: bool = False


class KnowledgeSpaceRead(SQLModel):
    id: int
    tenant_id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSpaceRetrievableRead(SQLModel):
    id: int
    tenant_id: int
    name: str
    description: str | None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeSpaceReadDetail(KnowledgeSpaceRead):
    created_at: datetime
    created_by: str
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    tenant: "TenantRead"


class KnowledgeSpaceCreate(SQLModel):
    name: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=255)


class KnowledgeSpaceUpdate(SQLModel):
    description: str | None = Field(default=None, max_length=255)