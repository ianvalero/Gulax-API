from typing import cast
from datetime import datetime
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.models.tenant import TenantDB
from app.models.knowledge_space import KnowledgeSpaceDB
from app.schemas.knowledge_space import KnowledgeSpaceQueryParams
from app.repositories.sorting import sort_data
from app.enums import KnowledgeSpaceSortField


KNOWLEDGE_SPACE_SORT_COLUMNS = {
    KnowledgeSpaceSortField.ID: KnowledgeSpaceDB.id,
    KnowledgeSpaceSortField.TENANT_ID: KnowledgeSpaceDB.tenant_id,
    KnowledgeSpaceSortField.TENANT_NAME: TenantDB.name,
    KnowledgeSpaceSortField.TENANT_ROLES: TenantDB.roles,
    KnowledgeSpaceSortField.NAME: KnowledgeSpaceDB.name,
    KnowledgeSpaceSortField.DESCRIPTION: KnowledgeSpaceDB.description,
    KnowledgeSpaceSortField.CREATED_AT: KnowledgeSpaceDB.created_at,
    KnowledgeSpaceSortField.CREATED_BY: KnowledgeSpaceDB.created_by
}

class KnowledgeSpaceRepository:
    def get_knowledge_spaces(
        self,
        session: Session,
        tenant_ids: list[int],
        params: KnowledgeSpaceQueryParams,
    ) -> tuple[list[KnowledgeSpaceDB], int]:
        if not tenant_ids:
            return [], 0

        where_conditions = [
            KnowledgeSpaceDB.tenant_id.in_(tenant_ids),
            *self.__generate_filters(filters=params),
        ]

        knowledge_spaces_statement = (
            select(KnowledgeSpaceDB)
            .join(TenantDB, KnowledgeSpaceDB.tenant_id == TenantDB.id)
            .where(*where_conditions)
            .options(selectinload(KnowledgeSpaceDB.tenant))
        )

        knowledge_spaces_statement = sort_data(
            statement=knowledge_spaces_statement,
            sort_column=KNOWLEDGE_SPACE_SORT_COLUMNS[params.sort_by],
            direction=params.sort_order,
            tie_breaker=KnowledgeSpaceDB.id,
        )
        knowledge_spaces_statement = knowledge_spaces_statement.offset(params.offset).limit(params.limit)

        total_statement = (
            select(func.count())
            .select_from(KnowledgeSpaceDB)
            .join(TenantDB, KnowledgeSpaceDB.tenant_id == TenantDB.id)
            .where(*where_conditions)
        )

        documents = cast(list[KnowledgeSpaceDB], session.exec(knowledge_spaces_statement).all())
        total = cast(int, session.exec(total_statement).one())
        return documents, total

    def get_knowledge_space_ids(self, session: Session, knowledge_space_id: int) -> list[int]:
        pass

    def get_knowledge_space(self, session: Session, knowledge_space_id: int) -> KnowledgeSpaceDB | None:
        statement = (
            select(KnowledgeSpaceDB)
            .where(
                KnowledgeSpaceDB.id == knowledge_space_id,
                KnowledgeSpaceDB.deleted_at.is_(None),
            )
            .options(selectinload(KnowledgeSpaceDB.tenant))
        )
        return session.exec(statement).first()

    def create_knowledge_space(self, session: Session, knowledge_space: KnowledgeSpaceDB) -> KnowledgeSpaceDB:
        session.add(knowledge_space)
        session.flush()
        return knowledge_space

    def update_knowledge_space(self, session: Session, knowledge_space: KnowledgeSpaceDB) -> KnowledgeSpaceDB:
        knowledge_space.updated_at = datetime.now()
        session.add(knowledge_space)
        session.flush()
        return knowledge_space

    def delete_knowledge_space(self, session: Session, knowledge_space: KnowledgeSpaceDB) -> bool:
        knowledge_space.deleted_at = datetime.now()
        session.flush()
        return True

    def __generate_filters(self, filters: KnowledgeSpaceQueryParams | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.tenant_id is not None:
                where_conditions.append(KnowledgeSpaceDB.tenant_id == filters.tenant_id)
            if filters.name:
                where_conditions.append(KnowledgeSpaceDB.name.ilike(f"%{filters.name}%"))
            if filters.description:
                where_conditions.append(KnowledgeSpaceDB.description.ilike(f"%{filters.description}%"))
            if filters.roles:
                where_conditions.append(TenantDB.roles.overlap(filters.roles))
            if filters.created_by:
                where_conditions.append(KnowledgeSpaceDB.created_by == filters.created_by)
            if filters.created_at_from:
                where_conditions.append(KnowledgeSpaceDB.created_at >= filters.created_at_from)
            if filters.created_at_to:
                where_conditions.append(KnowledgeSpaceDB.created_at <= filters.created_at_to)
            if not filters.include_deleted:
                where_conditions.append(KnowledgeSpaceDB.deleted_at.is_(None))

        return where_conditions