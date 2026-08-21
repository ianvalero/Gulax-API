from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import DateTime

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersionDB
    from app.models.knowledge_space import KnowledgeSpaceDB


class DocumentDB(SQLModel, table=True):
    __tablename__ = "documents"

    id: int | None = Field(default=None, primary_key=True)
    knowledge_space_id: int = Field(foreign_key="knowledge_spaces.id", index=True)
    description: str = Field(max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True)
    )
    created_by: str
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    updated_by: str | None = None
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    deleted_by: str | None = None

    knowledge_space: "KnowledgeSpaceDB" = Relationship()
    document_versions: list["DocumentVersionDB"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={"order_by": "DocumentVersionDB.id.desc()"}
    )