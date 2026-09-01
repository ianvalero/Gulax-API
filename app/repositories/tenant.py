from typing import cast
from datetime import datetime, timezone

from sqlmodel import Session, select, func, or_
from sqlalchemy.orm import selectinload, with_loader_criteria

from app.models.tenant import TenantDB
from app.models.knowledge_space import KnowledgeSpaceDB
from app.schemas.tenant import TenantQueryParams
from app.repositories.sorting import sort_data
from app.enums import TenantSortField


TENANT_SORT_COLUMNS = {
    TenantSortField.ID: TenantDB.id,
    TenantSortField.NAME: TenantDB.name,
    TenantSortField.DESCRIPTION: TenantDB.description,
    TenantSortField.ROLES: TenantDB.roles,
    TenantSortField.CREATED_AT: TenantDB.created_at,
    TenantSortField.CREATED_BY: TenantDB.created_by
}

class TenantRepository:
    def get_tenants(
        self,
        session: Session,
        roles: list[str],
        params: TenantQueryParams,
        is_admin: bool = False,
    ) -> tuple[list[TenantDB], int]:
        where_conditions = [
            *self.__base_conditions(roles=roles, is_admin=is_admin),
            *self.__generate_filters(filters=params)
        ]

        tenants_statement = select(TenantDB).where(*where_conditions)

        if params.include_knowledge_spaces:
            tenants_statement = tenants_statement.options(
                selectinload(TenantDB.knowledge_spaces),
                with_loader_criteria(
                    KnowledgeSpaceDB,
                    KnowledgeSpaceDB.deleted_at.is_(None),
                )
            )

        tenants_statement = sort_data(
            statement=tenants_statement,
            sort_column=TENANT_SORT_COLUMNS[params.sort_by],
            direction=params.sort_order,
            tie_breaker=TenantDB.id,
        )
        tenants_statement = tenants_statement.offset(params.offset).limit(params.limit)

        total_statement = (
            select(func.count())
            .select_from(TenantDB)
            .where(*where_conditions)
        )

        tenants = cast(list[TenantDB], session.exec(tenants_statement).all())
        total = cast(int, session.exec(total_statement).one())
        return tenants, total

    def get_manageable_tenant_ids(self, session: Session, roles: list[str], is_admin: bool = False) -> list[int]:
        where_conditions = [
            TenantDB.deleted_at.is_(None),
            *self.__base_conditions(roles=roles, is_admin=is_admin)
        ]

        statement = select(TenantDB.id).where(*where_conditions)
        return list(session.exec(statement).all())

    def get_retrieval_tenant_ids(self, session: Session, roles: list[str]) -> list[int]:
        where_conditions = [
            TenantDB.deleted_at.is_(None),
            or_(TenantDB.roles.overlap(roles), TenantDB.is_global_retrieval.is_(True))
        ]

        statement = select(TenantDB.id).distinct().where(*where_conditions)
        return list(session.exec(statement).all())

    def get_tenant(self, session: Session, tenant_id: int) -> TenantDB | None:
        statement = (
            select(TenantDB)
            .where(
                TenantDB.id == tenant_id,
                TenantDB.deleted_at.is_(None),
            )
            .options(
                selectinload(TenantDB.knowledge_spaces),
                with_loader_criteria(
                    KnowledgeSpaceDB,
                    KnowledgeSpaceDB.deleted_at.is_(None),
                )
            )
        )
        return session.exec(statement).first()

    def get_existing_names(self, session: Session, names: list[str]) -> set[str]:
        statement = (
            select(func.lower(TenantDB.name))
            .where(
                TenantDB.deleted_at.is_(None),
                func.lower(TenantDB.name).in_([name.lower() for name in names])
            )
        )
        return set(session.exec(statement).all())

    def create_tenant(self, session: Session, tenant: TenantDB) -> TenantDB:
        session.add(tenant)
        session.flush()
        return tenant

    def update_tenant(self, session: Session, tenant: TenantDB) -> TenantDB:
        tenant.updated_at = datetime.now(timezone.utc)
        session.add(tenant)
        session.flush()
        return tenant

    def delete_tenant(self, session: Session, tenant: TenantDB) -> bool:
        tenant.deleted_at = datetime.now(timezone.utc)
        session.flush()
        return True

    def __base_conditions(self, roles: list[str], is_admin: bool) -> list:
        if is_admin:
            return []

        return [TenantDB.roles.overlap(roles)]

    def __generate_filters(self, filters: TenantQueryParams | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.name:
                where_conditions.append(TenantDB.name.ilike(f"%{filters.name}%"))
            if filters.description:
                where_conditions.append(TenantDB.description.ilike(f"%{filters.description}%"))
            if filters.roles:
                where_conditions.append(TenantDB.roles.overlap(filters.roles))
            if filters.created_by:
                where_conditions.append(TenantDB.created_by == filters.created_by)
            if filters.created_at_from:
                where_conditions.append(TenantDB.created_at >= filters.created_at_from)
            if filters.created_at_to:
                where_conditions.append(TenantDB.created_at <= filters.created_at_to)
            if not filters.include_deleted:
                where_conditions.append(TenantDB.deleted_at.is_(None))

        return where_conditions