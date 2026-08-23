from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Index, text, DateTime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.tenant import TenantDB


class KnowledgeSpaceDB(SQLModel, table=True):
    __tablename__ = "knowledge_spaces"

    __table_args__ = (
        Index(
            "uq_knowledge_spaces_active_tenant_name",
            "tenant_id",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: int = Field(foreign_key="tenants.id", index=True)
    name: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    created_by: str = Field(index=True)
    updated_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    updated_by: str | None = Field(default=None)
    deleted_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
    )
    deleted_by: str | None = Field(default=None)

    tenant: "TenantDB" = Relationship(back_populates="knowledge_spaces")