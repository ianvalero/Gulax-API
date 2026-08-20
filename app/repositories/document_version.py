from typing import cast
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from app.models.document_version import DocumentVersionDB
from app.schemas.document_version import DocumentVersionFilters
from app.enums import DocumentVersionStatus


class DocumentVersionRepository:
    def get_document_versions(
        self,
        session: Session,
        document_id: int,
        offset: int = 0,
        limit: int = 100,
        filters: DocumentVersionFilters | None = None,
    ) -> tuple[list[DocumentVersionDB], int]:
        where_conditions = [DocumentVersionDB.document_id == document_id]
        where_conditions += self.__generate_filters(filters)

        document_versions = (
            select(DocumentVersionDB)
            .where(*where_conditions)
            .order_by(DocumentVersionDB.id.desc())
            .offset(offset)
            .limit(limit)
        )

        total = (
            select(func.count())
            .select_from(DocumentVersionDB)
            .where(*where_conditions)
        )

        document_versions = cast(list[DocumentVersionDB], session.exec(document_versions).all())
        total = cast(int, session.exec(total).one())
        return document_versions, total

    def get_document_active_versions(self, session: Session, document_id: int) -> list[DocumentVersionDB]:
        statement = (
            select(DocumentVersionDB)
            .where(
                DocumentVersionDB.document_id == document_id,
                DocumentVersionDB.status == DocumentVersionStatus.ACTIVE,
            )
            .order_by(DocumentVersionDB.id.desc())
        )

        return session.exec(statement).all()

    def get_document_version(self, session: Session, document_version_id: int) -> DocumentVersionDB | None:
        statement = (
            select(DocumentVersionDB)
            .options(selectinload(DocumentVersionDB.document))
            .where(DocumentVersionDB.id == document_version_id)
        )

        return session.exec(statement).first()

    def add_document_version(self, session: Session, document_version: DocumentVersionDB) -> DocumentVersionDB:
        session.add(document_version)
        session.flush()
        return document_version

    def set_document_version_task_id(
        self,
        session: Session,
        document_version: DocumentVersionDB,
        task_id: str
    ) -> DocumentVersionDB:
        document_version.task_id = task_id
        session.flush()
        return document_version

    def update_version_as_processing(
        self,
        session: Session,
        document_version: DocumentVersionDB
    ) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.PROCESSING

        session.flush()
        return document_version

    def update_version_as_active(
        self,
        session: Session,
        document_version: DocumentVersionDB,
        qdrant_point_ids: list[str]
    ) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.ACTIVE
        document_version.qdrant_point_ids = qdrant_point_ids
        document_version.error_message = None

        session.flush()
        return document_version

    def update_version_as_failed(
        self,
        session: Session,
        document_version: DocumentVersionDB,
        error_message: str
    ) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.FAILED
        document_version.error_message = error_message
        document_version.attempts += 1

        session.flush()
        return document_version

    def update_version_as_archived(
        self,
        session: Session,
        document_version: DocumentVersionDB
    ) -> DocumentVersionDB:
        document_version.status = DocumentVersionStatus.ARCHIVED

        session.flush()
        return document_version

    def __generate_filters(self, filters: DocumentVersionFilters | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.filename:
                where_conditions.append(DocumentVersionDB.original_filename.ilike(f"%{filters.filename}%"))
            if filters.status:
                where_conditions.append(DocumentVersionDB.status == filters.status)
            if filters.upload_by:
                where_conditions.append(DocumentVersionDB.uploaded_by == filters.upload_by)
            if filters.upload_at_from:
                where_conditions.append(DocumentVersionDB.uploaded_at >= filters.upload_at_from)
            if filters.upload_at_to:
                where_conditions.append(DocumentVersionDB.uploaded_at <= filters.upload_at_to)

        return where_conditions