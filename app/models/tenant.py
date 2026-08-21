from typing import TYPE_CHECKING
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from app.models.knowledge_space import KnowledgeSpaceDB


class TenantDB(SQLModel, table=True):
    __tablename__ = "tenants"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str | None = Field(default=None, max_length=255, index=True)
    is_global: bool = Field(default=False, index=True)
    roles: list[str] = Field(sa_column=Column(ARRAY(String)))
    created_at: datetime = Field(default_factory=datetime.now, index=True)
    created_by: str = Field(index=True)
    updated_at: datetime | None = None
    updated_by: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    knowledge_spaces: list["KnowledgeSpaceDB"] = Relationship(back_populates="tenant")