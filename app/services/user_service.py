import logging
import secrets
from datetime import datetime, timezone

from sqlmodel import Session

from app.repositories.user import UserRepository
from app.schemas.user import UserSSO, UserLoginResponse, User
from app.models.user import UserDB
from app.exceptions import InvalidApiKeyError, UserNotFoundError


class UserService:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.user_repository = UserRepository()
        self.logger.info("User Service initialized")

    def authenticate_sso_user(self, session: Session, user: UserSSO) -> UserLoginResponse:
        user_db = self.user_repository.update_or_create_user(session, user)

        if not user_db.api_key:
            self.__generate_api_key(session=session, db_user=user_db)
        else:
            if user_db.api_key_expires_at < datetime.now(timezone.utc):
                raise InvalidApiKeyError("API key expired")
            self.user_repository.update_api_key_expiration_date(session=session, user=user_db)

        session.commit()
        session.refresh(user_db)

        return UserLoginResponse(
            id=user_db.id,
            username=user_db.username,
            api_key=user_db.api_key,
            api_key_expires_at=user_db.api_key_expires_at
        )

    def get_current_user(self, session: Session, raw_api_key: str) -> User:
        user_db = self.user_repository.get_by_api_key(session, raw_api_key)

        if not user_db or not user_db.is_active:
            raise InvalidApiKeyError("Invalid or inactive API key")

        if user_db.api_key_expires_at < datetime.now(timezone.utc):
            raise InvalidApiKeyError("API key expired")

        self.user_repository.update_api_key_expiration_date(session, user_db)
        return User(
            username=user_db.username,
            email=user_db.email,
            name=user_db.name,
            roles=user_db.roles,
            is_admin=user_db.is_admin,
            is_automation=user_db.is_automation
        )

    def generate_new_api_key(self, session: Session, username: str) -> UserLoginResponse:
        user_db = self.user_repository.get_by_username(session, username)

        if not user_db:
            raise UserNotFoundError(f"User {username} not found")

        self.__generate_api_key(session, user_db)
        session.commit()
        session.refresh(user_db)

        return UserLoginResponse(
            id=user_db.id,
            username=user_db.username,
            api_key=user_db.api_key,
            api_key_expires_at=user_db.api_key_expires_at
        )

    def __generate_api_key(self, session: Session, db_user: UserDB) -> str:
        new_api_key = secrets.token_urlsafe(32)
        self.user_repository.set_api_key(session=session, user=db_user, api_key=new_api_key)
        return new_api_key