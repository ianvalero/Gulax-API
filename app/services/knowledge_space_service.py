import logging

from app.services import TenantService
from sqlmodel import Session

from app.models.knowledge_space import KnowledgeSpaceDB
from app.repositories.knowledge_space import KnowledgeSpaceRepository
from app.schemas.user import User
import app.schemas.knowledge_space as KnowledgeSpaceSchema
from app.exceptions import KnowledgeSpaceNotFoundError

class KnowledgeSpaceService:
    def __init__(self, tenant_service: TenantService):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.tenant_service = tenant_service
        self.knowledge_repository = KnowledgeSpaceRepository()
        self.logger.info("Knowledge Space Service initialized")

    async def get_knowledge_spaces(
        self,
        session: Session,
        user: User,
        params: KnowledgeSpaceSchema.KnowledgeSpaceQueryParams
    ) -> tuple[list[KnowledgeSpaceSchema.KnowledgeSpaceReadDetail], int]:
        if params.tenant_id:
            await self.tenant_service.check_access(session=session, user=user, tenant_id=params.tenant_id)
            tenant_ids = [params.tenant_id]
        else:
            tenant_ids = await self.tenant_service.get_tenant_ids(session=session, user=user)
            if not tenant_ids:
                return [], 0

        knowledge_spaces_db, total = self.knowledge_repository.get_knowledge_spaces(
            session=session,
            tenant_ids=tenant_ids,
            params=params,
        )

        knowledge_spaces = [
            KnowledgeSpaceSchema.KnowledgeSpaceReadDetail.model_validate(knowledge_space_db)
            for knowledge_space_db in knowledge_spaces_db
        ]

        return knowledge_spaces, total

    async def get_knowledge_space(
        self,
        session: Session,
        user: User,
        knowledge_space_id: int
    ) -> KnowledgeSpaceSchema.KnowledgeSpaceReadDetail:
        knowledge_space_db = await self.__get_db_knowledge_space(
            session=session,
            user=user,
            knowledge_space_id=knowledge_space_id
        )

        if not knowledge_space_db:
            raise KnowledgeSpaceNotFoundError(f"Knowledge Space with id {knowledge_space_id} not found")

        return KnowledgeSpaceSchema.KnowledgeSpaceReadDetail.model_validate(knowledge_space_db)

    async def create_knowledge_space(
        self,
        session: Session,
        user: User,
        tenant_id: int,
        knowledge_space: KnowledgeSpaceSchema.KnowledgeSpaceCreate
    ) -> KnowledgeSpaceSchema.KnowledgeSpaceReadDetail:
        await self.tenant_service.check_access(session=session, user=user, tenant_id=tenant_id)

        knowledge_space_db: KnowledgeSpaceDB = KnowledgeSpaceDB(
            **knowledge_space.model_dump(),
            tenant_id=tenant_id,
            created_by=user.username
        )
        self.knowledge_repository.create_knowledge_space(session=session, knowledge_space=knowledge_space)

        session.commit()
        session.refresh(knowledge_space_db)

        self.logger.info(f"Knowledge Space {knowledge_space_db.name} creado con éxito | SQL ID: {knowledge_space_db.id}")
        return KnowledgeSpaceSchema.KnowledgeSpaceReadDetail.model_validate(knowledge_space_db)

    async def update_knowledge_space(
        self,
        session: Session,
        user: User,
        knowledge_space_id: int,
        data: KnowledgeSpaceSchema.KnowledgeSpaceUpdate
    ) -> KnowledgeSpaceSchema.KnowledgeSpaceReadDetail:
        knowledge_space_db = await self.__get_db_knowledge_space(
            session=session,
            user=user,
            knowledge_space_id=knowledge_space_id
        )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(knowledge_space_db, field, value)
        knowledge_space_db.updated_by = user.username

        self.knowledge_repository.update_knowledge_space(session=session, knowledge_space=knowledge_space_db)
        session.commit()
        session.refresh(knowledge_space_db)

        self.logger.info(f"Knowledge Space {knowledge_space_db.name} actualizado | SQL ID: {knowledge_space_db.id}")
        return KnowledgeSpaceSchema.KnowledgeSpaceReadDetail.model_validate(knowledge_space_db)

    async def delete_knowledge_space(
        self,
        session: Session,
        user: User,
        knowledge_space_id: int
    ):
        knowledge_space_db = await self.__get_db_knowledge_space(
            session=session,
            user=user,
            knowledge_space_id=knowledge_space_id
        )

        knowledge_space_db.deleted_by = user.username
        self.knowledge_repository.delete_knowledge_space(session=session, knowledge_space=knowledge_space_db)

        session.commit()

        self.logger.info(f"Knowledge Space {knowledge_space_db.name} eliminado | SQL ID: {knowledge_space_db.id}")
        return True

    async def __get_db_knowledge_space(self, session: Session, user: User, knowledge_space_id: int) -> KnowledgeSpaceDB:
        knowledge_space_db = self.knowledge_repository.get_knowledge_space(
            session=session,
            knowledge_space_id=knowledge_space_id
        )

        if not knowledge_space_db:
            raise KnowledgeSpaceNotFoundError(f"Knowledge Space with ID {knowledge_space_id} not found.")

        await self.tenant_service.check_access(session=session, user=user, tenant_id=knowledge_space_db.tenant_id)
        return knowledge_space_db