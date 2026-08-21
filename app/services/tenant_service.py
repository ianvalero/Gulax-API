import logging

from sqlmodel import Session

from app.models.tenant import TenantDB
from app.repositories.tenant import TenantRepository
from app.schemas.user import User
import app.schemas.tenant as TenantSchema
from app.exceptions import TenantNotFoundError, TenantPermissionError


class TenantService:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.tenant_repository = TenantRepository()
        self.logger.info("Tenant Service initialized")

    async def get_tenants(
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

    async def get_tenant_ids(self, session: Session, user: User) -> list[int]:
        return self.tenant_repository.get_tenant_ids(
            session=session,
            roles=user.roles,
            is_admin=user.is_admin
        )

    async def get_tenant(self, session: Session, user: User, tenant_id: int) -> TenantSchema.TenantReadDetails:
        tenant_db = self.__get_db_tenant(session=session, user=user, tenant_id=tenant_id)
        return TenantSchema.TenantReadDetails.model_validate(tenant_db)

    async def check_access(self, session: Session, user: User, tenant_id: int) -> None:
        self.__get_db_tenant(session=session, user=user, tenant_id=tenant_id)

    async def create_tenant(
        self,
        session: Session,
        user: User,
        new_tenant: TenantSchema.TenantCreate
    ) -> TenantSchema.TenantRead:
        if not user.is_admin:
            raise TenantPermissionError("User does not have permission to create a tenant.")

        tenant_db = TenantDB(
            name=new_tenant.name,
            description=new_tenant.description,
            is_global_retrieval=new_tenant.is_global,
            roles=new_tenant.roles,
            created_by=user.username
        )
        self.tenant_repository.create_tenant(session=session, tenant=tenant_db)

        session.commit()
        session.refresh(tenant_db)

        self.logger.info(f"Tenant {new_tenant.name} creada con éxito | SQL ID: {tenant_db.id}")
        return TenantSchema.TenantRead.model_validate(tenant_db)

    async def update_tenant(
        self,
        session: Session,
        user: User,
        tenant_id: int,
        data: TenantSchema.TenantUpdate
    ) -> TenantSchema.TenantRead:
        tenant_db = self.__get_db_tenant(session=session, user=user, tenant_id=tenant_id)

        update_data = data.model_dump(exclude_unset=True)
        if "roles" in update_data and not user.is_admin and not set(update_data["roles"]).issubset(set(user.roles)):
            raise TenantPermissionError("User does not have permission to assign these roles.")

        for field, value in update_data.items():
            setattr(tenant_db, field, value)
        tenant_db.updated_by = user.username

        self.tenant_repository.update_tenant(session=session, tenant=tenant_db)
        session.commit()
        session.refresh(tenant_db)

        self.logger.info(f"Tenant {tenant_db.name} modificado con éxito | SQL ID: {tenant_db.id}")
        return TenantSchema.TenantRead.model_validate(tenant_db)

    async def delete_tenant(self, session: Session, user: User, tenant_id: int) -> bool:
        tenant_db = self.__get_db_tenant(session=session, user=user, tenant_id=tenant_id)

        tenant_db.deleted_by = user.username
        self.tenant_repository.delete_tenant(session=session, tenant=tenant_db)

        session.commit()

        self.logger.info(f"Tenant {tenant_db.name} eliminado | SQL ID: {tenant_db.id} ")
        return True 

    def __get_db_tenant(self, session: Session, user: User, tenant_id: int) -> TenantDB:
        tenant_db = self.tenant_repository.get_tenant(session=session, tenant_id=tenant_id)

        if not tenant_db:
            raise TenantNotFoundError(f"Tenant with ID {tenant_id} not found.")
        elif not user.is_admin and not (set(tenant_db.roles) & set(user.roles)):
            raise TenantPermissionError("User does not have permission to access this tenant.")

        return tenant_db