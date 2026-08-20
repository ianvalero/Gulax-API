from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    username: str
    email: str
    name: str
    roles: list[str]
    is_admin: bool
    is_automation: bool

class UserSSO(BaseModel):
    sso_id: str
    username: str
    email: str
    name: str
    roles: list[str]

class UserLoginResponse(BaseModel):
    id: int
    username: str
    api_key: str
    api_key_expires_at: datetime