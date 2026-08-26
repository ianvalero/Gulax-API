from datetime import datetime, timezone
from typing import cast

from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.models.document_version import DocumentVersionDB
from app.schemas.document_version import DocumentVersionQueryParams
from app.repositories.sorting import sort_data
from app.enums import DocumentVersionStatus, DocumentVersionsSortField


DOCUMENT_VERSIONS_SORT_COLUMNS = {
    DocumentVersionsSortField.ID: DocumentVersionDB.id,
    DocumentVersionsSortField.FILENAME: DocumentVersionDB.filename,
    DocumentVersionsSortField.STATUS: DocumentVersionDB.status,
    DocumentVersionsSortField.UPLOADED_AT: DocumentVersionDB.uploaded_at,
    DocumentVersionsSortField.UPLOADED_BY: DocumentVersionDB.uploaded_by,
}

class DocumentVersionRepository:
    def get_document_versions(
        self,
        session: Session,
        document_id: int,
        params: DocumentVersionQueryParams,
    ) -> tuple[list[DocumentVersionDB], int]:
        where_conditions = [
            DocumentVersionDB.document_id == document_id,
            *self.__generate_filters(filters=params)
        ]

        document_versions_statement = (
            select(DocumentVersionDB)
            .where(*where_conditions)
            .options(selectinload(DocumentVersionDB.document))
        )
        document_versions_statement = sort_data(
            statement=document_versions_statement,
            sort_column=DOCUMENT_VERSIONS_SORT_COLUMNS[params.sort_by],
            direction=params.sort_order,
            tie_breaker=DocumentVersionDB.id,
        )
        document_versions_statement = document_versions_statement.offset(params.offset).limit(params.limit)

        total_statement = (
            select(func.count())
            .select_from(DocumentVersionDB)
            .where(*where_conditions)
        )

        document_versions = cast(list[DocumentVersionDB], session.exec(document_versions_statement).all())
        total = cast(int, session.exec(total_statement).one())
        return document_versions, total

    def get_document_active_versions(self, session: Session, document_id: int) -> list[DocumentVersionDB]:
        statement = (
            select(DocumentVersionDB)
            .where(
                DocumentVersionDB.document_id == document_id,
                DocumentVersionDB.status == DocumentVersionStatus.ACTIVE,
            )
            .options(selectinload(DocumentVersionDB.document))
            .order_by(DocumentVersionDB.id.desc())
        )

        return session.exec(statement).all()

    def get_document_version(self, session: Session, document_version_id: int) -> DocumentVersionDB | None:
        statement = (
            select(DocumentVersionDB)
            .where(DocumentVersionDB.id == document_version_id)
            .options(
                selectinload(DocumentVersionDB.document),
                selectinload(DocumentVersionDB.ingestion_runs)
            )
        )

        return session.exec(statement).first()

    def get_next_version_number(self, session: Session, document_id: int) -> int:
        statement = (
            select(func.coalesce(func.max(DocumentVersionDB.version_number), 0))
            .where(DocumentVersionDB.document_id == document_id)
        )
        current_max = cast(int, session.exec(statement).one())
        return current_max + 1

    def add_document_version(self, session: Session, document_version: DocumentVersionDB) -> DocumentVersionDB:
        session.add(document_version)
        session.flush()
        return document_version

    def update_version_as_active(self, session: Session, document_version: DocumentVersionDB) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.ACTIVE
        document_version.activated_at = datetime.now(timezone.utc)

        session.flush()
        return document_version

    def update_version_as_failed(self, session: Session, document_version: DocumentVersionDB) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.FAILED

        session.flush()
        return document_version

    def update_version_as_archived(self, session: Session, document_version: DocumentVersionDB) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.ARCHIVED
        document_version.archived_at = datetime.now(timezone.utc)

        session.flush()
        return document_version

    def __generate_filters(self, filters: DocumentVersionQueryParams | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.filename:
                where_conditions.append(DocumentVersionDB.filename.ilike(f"%{filters.filename}%"))
            if filters.status:
                where_conditions.append(DocumentVersionDB.status == filters.status)
            if filters.upload_by:
                where_conditions.append(DocumentVersionDB.uploaded_by == filters.upload_by)
            if filters.upload_at_from:
                where_conditions.append(DocumentVersionDB.uploaded_at >= filters.upload_at_from)
            if filters.upload_at_to:
                where_conditions.append(DocumentVersionDB.uploaded_at <= filters.upload_at_to)

        return where_conditions