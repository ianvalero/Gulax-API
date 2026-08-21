from datetime import datetime
from sqlmodel import SQLModel
from pydantic import ConfigDict, Field

from app.schemas.pagination import PaginationParams
from app.schemas.knowledge_space import KnowledgeSpaceRead
from app.schemas.document_version import DocumentVersionRead
from app.enums import DocumentSortField, SortDirection


class DocumentQueryParams(PaginationParams):
    knowledge_space_id: int | None = Field(default=None, gt=0)
    knowledge_space_name: str | None = None
    description: str | None = None
    roles: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    include_deleted: bool = False

    sort_by: DocumentSortField = DocumentSortField.ID
    sort_order: SortDirection = SortDirection.ASC


class DocumentRead(SQLModel):
    id: int
    description: str
    knowledge_space: KnowledgeSpaceRead
    created_at: datetime
    created_by: str
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    document_versions: list[DocumentVersionRead] = list()

    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(SQLModel):
    description: str

class DocumentUpdate(SQLModel):
    description: str