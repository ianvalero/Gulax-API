from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from app.models.tenant import TenantDB

class KnowledgeSpaceDB(SQLModel, table=True):
    __tablename__ = "knowledge_spaces"

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenants.id")
    name: str = Field(unique=True, index=True)
    description: str | None = Field(default=None, max_length=255, index=True)
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    created_by: str = Field(index=True)
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    tenant: "TenantDB" = Relationship(back_populates="knowledge_spaces")