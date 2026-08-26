from datetime import datetime

from sqlmodel import SQLModel
from pydantic import ConfigDict, Field

from app.schemas.pagination import PaginationParams
from app.schemas.ingestion_run import IngestionRunRead
from app.enums import DocumentVersionStatus, DocumentVersionsSortField, SortDirection


class DocumentVersionQueryParams(PaginationParams):
    filename: str | None = None
    status: DocumentVersionStatus | None = None
    upload_by: str | None = None
    upload_at_from: datetime | None = None
    upload_at_to: datetime | None = None

    sort_by: DocumentVersionsSortField = DocumentVersionsSortField.ID
    sort_order: SortDirection = SortDirection.ASC

class DocumentVersionRead(SQLModel):
    id: int
    document_id: int
    filename: str
    version_number: int
    uploaded_by: str
    uploaded_at: datetime
    status: DocumentVersionStatus

    model_config = ConfigDict(from_attributes=True)

class DocumentVersionReadDetail(DocumentVersionRead):
    file_path: str
    file_size: int
    mime_type: str
    activated_at: datetime | None = Field(default=None)
    archived_at: datetime | None = Field(default=None)

    ingestion_runs: list[IngestionRunRead] = Field(default_factory=list)