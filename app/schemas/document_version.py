from typing import Any
from datetime import datetime
from sqlmodel import SQLModel
from pydantic import ConfigDict, BaseModel

from app.enums import DocumentVersionStatus


class DocumentVersionFilters(BaseModel):
    filename: str | None = None
    status: DocumentVersionStatus | None = None
    upload_by: str | None = None
    upload_at_from: datetime | None = None
    upload_at_to: datetime | None = None

class DocumentVersionRead(SQLModel):
    id: int
    document_id: int
    version_number: int
    filename: str
    uploaded_by: str
    uploaded_at: datetime
    task_id: str | None = None
    error_message: str | None
    status: DocumentVersionStatus

    model_config = ConfigDict(from_attributes=True)

class DocumentVersionReadDetail(DocumentVersionRead):
    file_path: str
    file_size: int
    mime_type: str
    qdrant_point_ids: list[str] | None
    attempts: int


class DocumentVersionTaskRead(SQLModel):
    task_id: str
    status: str
    result: Any | None = None