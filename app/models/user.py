from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import SQLModel, Field


class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    sso_id: str = Field(unique=True, index=True)
    username: str = Field(unique=True)
    name: str
    email: str
    roles: list[str] = Field(sa_column=Column(ARRAY(String)))
    api_key: str | None = Field(default=None, unique=True, index=True)
    api_key_expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    is_active: bool = Field(default=True)
    last_login: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def is_admin(self) -> bool:
        return "ROLE_ADMIN" in self.roles

    @property
    def is_automation(self) -> bool:
        return "ROLE_AUTOMATION" in self.roles