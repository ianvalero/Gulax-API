from typing import cast

from sqlmodel import Session, select, func

from app.models.ingestion_run import IngestionRunDB
from app.schemas.ingestion_run import IngestionRunQueryParams
from app.repositories.sorting import sort_data
from app.enums import IngestionRunSortField


INGESTION_RUN_SORT_COLUMNS = {
    IngestionRunSortField.ID: IngestionRunDB.id,
    IngestionRunSortField.STATUS: IngestionRunDB.status,
}

class IngestionRunRepository:
    def get_ingestion_runs(
        self,
        session: Session,
        document_version_id: int,
        params: IngestionRunQueryParams
    ) -> tuple[list[IngestionRunDB], int]:
        where_conditions = [
            IngestionRunDB.document_version_id == document_version_id,
            *self.__generate_filters(filters=params),
        ]

        ingestion_runs_statement = (
            select(IngestionRunDB)
            .where(*where_conditions)
        )

        ingestion_runs_statement = sort_data(
            statement=ingestion_runs_statement,
            sort_column=INGESTION_RUN_SORT_COLUMNS[params.sort_by],
            direction=params.sort_order,
            tie_breaker=IngestionRunDB.id,
        )
        ingestion_runs_statement = ingestion_runs_statement.offset(params.offset).limit(params.limit)

        total_statement = (
            select(func.count())
            .select_from(IngestionRunDB)
            .where(*where_conditions)
        )

        ingestion_runs = cast(list[IngestionRunDB], session.exec(ingestion_runs_statement).all())
        total = cast(int, session.exec(total_statement).one())
        return ingestion_runs, total

    def get_ingestion_run(self, session: Session, ingestion_run_id: int) -> IngestionRunDB | None:
        statement = (
            select(IngestionRunDB)
            .where(IngestionRunDB.id == ingestion_run_id)
        )
        return session.exec(statement).first()

    def get_next_attempt_number(self, session: Session, document_version_id: int) -> int:
        statement = (
            select(func.coalesce(func.max(IngestionRunDB.attempt_number), 0))
            .where(IngestionRunDB.document_version_id == document_version_id)
        )
        current_max = cast(int, session.exec(statement).one())
        return current_max + 1

    def create_ingestion_run(self, session: Session, ingestion_run: IngestionRunDB) -> IngestionRunDB:
        session.add(ingestion_run)
        session.flush()
        return ingestion_run

    def __generate_filters(self, filters: IngestionRunQueryParams | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.status:
                where_conditions.append(IngestionRunDB.status == filters.status)
            if filters.created_at_from:
                where_conditions.append(IngestionRunDB.created_at >= filters.created_at_from)
            if filters.created_at_to:
                where_conditions.append(IngestionRunDB.created_at <= filters.created_at_to)

        return where_conditions