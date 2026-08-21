from sqlalchemy import Column, Enum as SAEnum
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

from app.enums import DocumentVersionStatus
from app.models.document import DocumentDB

class DocumentVersionDB(SQLModel, table=True):
    __tablename__ = "documents_versions"

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documents.id", index=True)
    version_number: int = Field(index=True)
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=datetime.now)
    task_id: str | None = Field(default=None, index=True)
    attempts: int = 0
    error_message: str | None = None
    status: DocumentVersionStatus = Field(
        default=DocumentVersionStatus.PENDING,
        sa_column=Column(
            SAEnum(
                DocumentVersionStatus,
                values_callable=lambda enum: [enum_value.value for enum_value in enum],
                native_enum=False)
        )
    )

    document: DocumentDB = Relationship(back_populates="documents_versions")