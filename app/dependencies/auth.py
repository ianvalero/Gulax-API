from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
from sqlmodel import Session

from app.database import get_session
from app.services.user_service import UserService
from app.dependencies.services import get_user_service
from app.schemas.user import User
from app.models.user import UserDB

api_key_header = APIKeyHeader(name="X-Api-Key", scheme_name="ApiKeyAuth", auto_error=False)

def get_current_user(
    x_api_key: str = Security(api_key_header),
    session: Session = Depends(get_session),
    user_service: UserService = Depends(get_user_service),
) -> User:
    return user_service.get_current_user(session, x_api_key)

def require_admin(current_user: UserDB = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} is not authorized to perform this action"
        )
    return current_user

def require_automation(current_user: UserDB = Depends(get_current_user)) -> User:
    if not current_user.is_admin and not current_user.is_automation:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=f"User {current_user.username} is not authorized to perform this action"
        )
    return current_user