import logging

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.tenant import TenantDB
from app.infrastructure import QdrantGateway
from app.repositories.tenant import TenantRepository
from app.schemas.user import User
import app.schemas.tenant as TenantSchema
from app.exceptions import TenantNotFoundError, TenantPermissionError, TenantNameConflictError


EXCLUDED_ROLES = {"ROLE_ADMIN", "ROLE_AUTOMATION"}

class TenantService:
    def __init__(self, qdrant_gateway: QdrantGateway):
        self.logger = logging.getLogger(f"app.{__name__}")
        self._qdrant_gateway = qdrant_gateway
        self.tenant_repository = TenantRepository()
        self.logger.info("Tenant Service initialized")

    async def get_manageable_tenants(
        self,
        session: Session,
        user: User,
        params: TenantSchema.TenantQueryParams
    ) -> tuple[list[TenantSchema.TenantReadDetailsWithKnowledgeSpaces | TenantSchema.TenantReadDetails], int]:
        tenants_db, total = self.tenant_repository.get_tenants(
            session=session,
            roles=user.roles,
            params=params,
            is_admin=user.is_admin
        )

        if params.include_knowledge_spaces:
            tenants = [
                TenantSchema.TenantReadDetailsWithKnowledgeSpaces.model_validate(tenant_db)
                for tenant_db in tenants_db
            ]
        else:
            tenants = [
                TenantSchema.TenantReadDetails.model_validate(tenant_db)
                for tenant_db in tenants_db
            ]

        return tenants, total

    async def get_manageable_tenant_ids(self, session: Session, user: User) -> list[int]:
        return self.tenant_repository.get_manageable_tenant_ids(
            session=session,
            roles=user.roles,
            is_admin=user.is_admin
        )

    async def get_retrievable_tenant_ids(self, session: Session, user: User) -> list[int]:
        return self.tenant_repository.get_retrieval_tenant_ids(
            session=session,
            roles=user.roles,
        )

    async def get_tenant(self, session: Session, user: User, tenant_id: int) -> TenantSchema.TenantReadDetailsWithKnowledgeSpaces:
        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        if not self.can_manage_tenant(user, tenant_db):
            raise TenantPermissionError("User does not have management access to this tenant")

        return TenantSchema.TenantReadDetailsWithKnowledgeSpaces.model_validate(tenant_db)

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
    ) -> TenantSchema.TenantReadDetails:
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
        return TenantSchema.TenantReadDetails.model_validate(tenant_db)

    async def delete_tenant(self, session: Session, user: User, tenant_id: int) -> bool:
        if not user.is_admin:
            raise TenantPermissionError(f"User {user.username} is not authorized to perform this action")

        tenant_db = self.__get_db_tenant(session=session, tenant_id=tenant_id)

        tenant_db.deleted_by = user.username
        self.tenant_repository.delete_tenant(session=session, tenant=tenant_db)

        session.commit()

        try:
            await self._qdrant_gateway.delete_tenant(tenant_id=tenant_id)
        except Exception:
            self.logger.exception(f"Error deleting points from Qdrant for tenant_id={tenant_id}")

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

    def ensure_tenants_for_roles(self, session: Session, roles: list[str]) -> bool:
        roles_to_check: dict[str, str] = {
            role: role.removeprefix("ROLE_").capitalize()
            for role in roles if role not in EXCLUDED_ROLES
        }

        if not roles_to_check:
            return True

        existing_tenants = self.tenant_repository.get_existing_names(
            session=session,
            names=list(roles_to_check.values())
        )

        for role, tenant_name in roles_to_check.items():
            if tenant_name.lower() in existing_tenants:
                continue

            tenant_db = TenantDB(
                name=tenant_name,
                description=f"Tenant for {role}",
                roles=[role],
                created_by="Automation"
            )

            try:
                with session.begin_nested():
                    self.tenant_repository.create_tenant(session=session, tenant=tenant_db)
                    self.logger.info(f"Tenant {tenant_name} created for role {role} | SQL ID: {tenant_db.id}")
            except IntegrityError:
                session.rollback()
                self.logger.warning(f"Tenant {tenant_name} already exists for role {role}")

        return True

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