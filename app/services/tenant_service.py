import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.tenant import TenantDB
from app.repositories.tenant import TenantRepository
from app.schemas.user import User
import app.schemas.tenant as TenantSchema
from app.exceptions import TenantNotFoundError, TenantPermissionError, TenantNameConflictError


class TenantService:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.tenant_repository = TenantRepository()
        self.logger.info("Tenant Service initialized")

    async def get_manageable_tenants(
        self,
        session: Session,
        user: User,
        params: TenantSchema.TenantQueryParams
    ) -> tuple[list[TenantSchema.TenantRead | TenantSchema.TenantReadDetails], int]:
        tenants_db, total = self.tenant_repository.get_tenants(
            session=session,
            roles=user.roles,
            params=params,
            is_admin=user.is_admin
        )

        if params.include_knowledge_spaces:
            tenants = [
                TenantSchema.TenantReadDetails.model_validate(tenant_db)
                for tenant_db in tenants_db
            ]
        else:
            tenants = [
                TenantSchema.TenantRead.model_validate(tenant_db)
                for tenant_db in tenants_db
            ]

        return tenants, total

    async def get_manageable_tenant_ids(self, session: Session, user: User) -> list[int]:
        return self.tenant_repository.get_tenant_ids(
            session=session,
            roles=user.roles,
            is_admin=user.is_admin
        )

    async def get_tenant(self, session: Session, user: User, tenant_id: int) -> TenantSchema.TenantReadDetails:
        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        if not self.can_manage_tenant(user, tenant_db):
            raise TenantPermissionError("User does not have management access to this tenant")

        return TenantSchema.TenantReadDetails.model_validate(tenant_db)

    async def create_tenant(
        self,
        session: Session,
        user: User,
        new_tenant: TenantSchema.TenantCreate
    ) -> TenantSchema.TenantRead:
        if not user.is_admin:
            raise TenantPermissionError(f"User {user.username} is not authorized to perform this action")

        tenant_db = TenantDB(
            name=new_tenant.name,
            description=new_tenant.description,
            is_global_retrieval=new_tenant.is_global_retrieval,
            roles=new_tenant.roles,
            created_by=user.username
        )
        self.tenant_repository.create_tenant(session=session, tenant=tenant_db)

        try:
            session.commit()
            session.refresh(tenant_db)
        except IntegrityError as err:
            session.rollback()
            raise TenantNameConflictError(f"Tenant with name {new_tenant.name} already exists") from err

        self.logger.info(f"Tenant {new_tenant.name} creada con éxito | SQL ID: {tenant_db.id}")
        return TenantSchema.TenantRead.model_validate(tenant_db)

    async def update_tenant(
        self,
        session: Session,
        user: User,
        tenant_id: int,
        data: TenantSchema.TenantUpdate
    ) -> TenantSchema.TenantRead:
        if not user.is_admin:
            raise TenantPermissionError(f"User {user.username} is not authorized to perform this action")

        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(tenant_db, field, value)
        tenant_db.updated_by = user.username

        self.tenant_repository.update_tenant(session=session, tenant=tenant_db)
        session.commit()
        session.refresh(tenant_db)

        self.logger.info(f"Tenant {tenant_db.name} modificado con éxito | SQL ID: {tenant_db.id}")
        return TenantSchema.TenantRead.model_validate(tenant_db)

    async def delete_tenant(self, session: Session, user: User, tenant_id: int) -> bool:
        if not user.is_admin:
            raise TenantPermissionError(f"User {user.username} is not authorized to perform this action")

        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        tenant_db.deleted_by = user.username
        self.tenant_repository.delete_tenant(session=session, tenant=tenant_db)

        session.commit()

        self.logger.info(f"Tenant {tenant_db.name} eliminado | SQL ID: {tenant_db.id} ")
        return True

    async def require_management_access(self, session: Session, user: User, tenant_id: int) -> None:
        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        if not self.can_manage_tenant(user, tenant_db):
            raise TenantPermissionError("User does not have management access to this tenant")

    async def require_retrieval_access(self, session: Session, user: User, tenant_id: int) -> None:
        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        if not self.can_retrieve_tenant(user, tenant_db):
            raise TenantPermissionError("User does not have retrieval access to this tenant")

    @staticmethod
    def can_manage_tenant(user: User, tenant: TenantDB) -> bool:
        return user.is_admin or bool(set(user.roles) & set(tenant.roles))

    @staticmethod
    def can_retrieve_tenant(user: User, tenant: TenantDB) -> bool:
        return tenant.is_global_retrieval or bool(set(user.roles) & set(tenant.roles))

    def __get_db_tenant(self, session: Session, tenant_id: int) -> TenantDB:
        tenant_db = self.tenant_repository.get_tenant(session=session, tenant_id=tenant_id)

        if not tenant_db:
            raise TenantNotFoundError(f"Tenant with ID {tenant_id} not found.")

        return tenant_db