from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from app.models.user import UserDB
from app.schemas.user import UserSSO


class UserRepository:
    def get_by_sso_id(self, session: Session, sso_id: str) -> UserDB | None:
        statement = (
            select(UserDB)
            .where(UserDB.sso_id == sso_id)
        )
        return session.exec(statement).first()

    def get_by_api_key(self, session: Session, raw_api_key: str) -> UserDB | None:
        statement = (
            select(UserDB)
            .where(UserDB.api_key == raw_api_key)
        )
        return session.exec(statement).first()

    def get_by_username(self, session: Session, username: str) -> UserDB | None:
        statement = (
            select(UserDB)
            .where(UserDB.username == username)
        )
        return session.exec(statement).first()

    def update_or_create_user(self, session: Session, user: UserSSO) -> UserDB:
        user_db = self.get_by_sso_id(session, user.sso_id)
        if not user_db:
            user_db = UserDB(
                sso_id=user.sso_id,
                username=user.username,
                name=user.name,
                email=user.email,
                roles=user.roles
            )
            session.add(user_db)
        else:
            user_db.username = user.username
            user_db.name = user.name
            user_db.email = user.email
            user_db.roles = user.roles
            user_db.is_active = True

        session.flush()
        return user_db

    def set_api_key(self, session: Session, user: UserDB, api_key: str) -> bool:
        user.api_key = api_key
        self.update_api_key_expiration_date(session, user)
        return True

    def update_api_key_expiration_date(self, session: Session, user: UserDB) -> bool:
        user.api_key_expires_at = datetime.now(timezone.utc) + relativedelta(months=3)
        session.add(user)
        session.flush()
        return True