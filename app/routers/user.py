from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.config.settings import settings
from app.database import get_session
from app.schemas.user import UserSSO, UserLoginResponse
from app.services.user_service import UserService
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post(
    "/login",
    response_model=UserLoginResponse,
    dependencies=[Depends(dependencies_auth.require_automation)],
    summary="User login"
)
async def login(
    body: UserSSO,
    session: Session = Depends(get_session),
    user_service: UserService = Depends(dependencies_services.get_user_service),
):
    return user_service.authenticate_sso_user(session=session, user=body)

@router.patch(
    "/{username}/api-key",
    response_model=UserLoginResponse,
    dependencies=[Depends(dependencies_auth.require_automation)],
    summary="Generate new user api key"
)
async def generate_api_key(
    username: str,
    session: Session = Depends(get_session),
    user_service: UserService = Depends(dependencies_services.get_user_service),
):
    return user_service.generate_new_api_key(session=session, username=username)

