from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersionDB
    from app.models.knowledge_space import KnowledgeSpaceDB

class DocumentDB(SQLModel, table=True):
    __tablename__ = "documents"

    id: int | None = Field(default=None, primary_key=True)
    knowledge_space_id: int = Field(foreign_key="knowledge_spaces.id", index=True)
    description: str = Field(index=True, max_length=255)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    created_by: str = Field(index=True)
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    knowledge_space: "KnowledgeSpaceDB" = Relationship()
    documents_versions: list["DocumentVersionDB"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={"order_by": "DocumentVersionDB.id.desc()"}
    )