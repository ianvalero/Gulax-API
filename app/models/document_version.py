from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, text, Enum as SAEnum
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint

from app.enums import DocumentVersionStatus

if TYPE_CHECKING:
    from app.models.document import DocumentDB
    from app.models.ingestion_run import IngestionRunDB


class DocumentVersionDB(SQLModel, table=True):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_version",
        ),
        Index(
            "uq_document_versions_active_document",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="documents.id", index=True)
    version_number: int = Field(gt=0)
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    uploaded_by: str
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    status: DocumentVersionStatus = Field(
        default=DocumentVersionStatus.PENDING,
        sa_column=Column(
            SAEnum(
                DocumentVersionStatus,
                values_callable=lambda enum: [
                    enum_value.value for enum_value in enum
                ],
                native_enum=False,
            ),
            nullable=False,
        ),
    )
    activated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    document: "DocumentDB" = Relationship(back_populates="document_versions")
    ingestion_runs: list["IngestionRunDB"] = Relationship(back_populates="document_version")