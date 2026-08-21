from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum as SAEnum
from sqlmodel import SQLModel, Field, Relationship

from app.enums import IngestionRunStatus

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersionDB

class IngestionRunDB(SQLModel, table=True):
    __tablename__ = "ingestion_runs"

    id: int | None = Field(default=None, primary_key=True)
    document_version_id: int = Field(foreign_key="document_versions.id", index=True)
    status: IngestionRunStatus = Field(
        default=IngestionRunStatus.PENDING,
        sa_column=Column(
            SAEnum(
                IngestionRunStatus,
                values_callable=lambda enum: [
                    enum_value.value for enum_value in enum
                ],
                native_enum=False,
            ),
            nullable=False,
        ),
    )
    retry_count: int = Field(default=0)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )

    document_version: "DocumentVersionDB" = Relationship(back_populates="ingestion_runs")