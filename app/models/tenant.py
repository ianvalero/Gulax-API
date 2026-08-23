from typing import TYPE_CHECKING
from datetime import datetime, timezone

from sqlalchemy import Column, String, Index, text, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.knowledge_space import KnowledgeSpaceDB


class TenantDB(SQLModel, table=True):
    __tablename__ = "tenants"

    __table_args__ = (
        Index(
            "uq_tenants_active_name",
            text("lower(name)"),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=255)
    is_global_retrieval: bool = Field(default=False)
    roles: list[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    created_by: str
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

    knowledge_spaces: list["KnowledgeSpaceDB"] = Relationship(back_populates="tenant")