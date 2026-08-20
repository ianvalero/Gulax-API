from typing import cast
from datetime import datetime
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload, contains_eager

#from app.models.collection import CollectionDB
from app.models.document import DocumentDB
from app.models.document_version import DocumentVersionDB
from app.schemas.document import DocumentQueryParams
from app.repositories.sorting import sort_data
from app.enums import DocumentVersionStatus, DocumentSortField


DOCUMENT_SORT_COLUMNS = {
    DocumentSortField.ID: DocumentDB.id,
    #DocumentSortField.COLLECTION_ID: DocumentDB.collection_id,
    #DocumentSortField.COLLECTION_GULAX_NAME: CollectionDB.gulax_name,
    DocumentSortField.DESCRIPTION: DocumentDB.description,
    #DocumentSortField.COLLECTION_ROLES: CollectionDB.roles,
    DocumentSortField.CREATED_AT: DocumentDB.created_at,
    DocumentSortField.CREATED_BY: DocumentDB.created_by
}

class DocumentRepository:
    def get_documents(
        self,
        session: Session,
        collection_ids: list[int],
        params: DocumentQueryParams,
    ) -> tuple[list[DocumentDB], int]:
        pass
        # where_conditions = [
        #     DocumentDB.collection_id.in_(collection_ids),
        #     *self.__generate_filters(filters=params),
        # ]
        #
        # documents_statement = (
        #     select(DocumentDB)
        #     .join(CollectionDB, DocumentDB.collection_id == CollectionDB.id)
        #     .where(*where_conditions)
        #     .options(
        #         selectinload(DocumentDB.documents_versions.and_(DocumentVersionDB.status == DocumentVersionStatus.ACTIVE)),
        #         contains_eager(DocumentDB.collection)
        #     )
        # )
        # documents_statement = sort_data(
        #     statement=documents_statement,
        #     sort_column=DOCUMENT_SORT_COLUMNS[params.sort_by],
        #     direction=params.sort_order,
        #     tie_breaker=DocumentDB.id,
        # )
        # documents_statement = documents_statement.offset(params.offset).limit(params.limit)
        #
        # total_statement = (
        #     select(func.count())
        #     .select_from(DocumentDB)
        #     .join(CollectionDB, DocumentDB.collection_id == CollectionDB.id)
        #     .where(*where_conditions)
        # )
        #
        # documents = cast(list[DocumentDB], session.exec(documents_statement).all())
        # total = cast(int, session.exec(total_statement).one())
        # return documents, total

    def get_document(self, session: Session, document_id: int) -> DocumentDB | None:
        pass
        # statement = (
        #     select(DocumentDB)
        #     .where(
        #         DocumentDB.id == document_id,
        #         DocumentDB.deleted_at.is_(None)
        #     )
        #     .options(
        #         selectinload(DocumentDB.documents_versions),
        #         selectinload(DocumentDB.collection)
        #     )
        # )
        #
        # return session.exec(statement).first()

    def add_document(self, session: Session, document: DocumentDB) -> DocumentDB:
        session.add(document)
        session.flush()
        return document

    def update_document(self, session: Session, document: DocumentDB) -> DocumentDB:
        document.updated_at = datetime.now()
        session.add(document)
        session.flush()
        return document

    def delete_document(self, session: Session, document: DocumentDB) -> bool:
        document.deleted_at = datetime.now()
        session.flush()
        return True

    def __generate_filters(self, filters: DocumentQueryParams | None = None) -> list:
        where_conditions = []

        if filters:
            if filters.description:
                where_conditions.append(DocumentDB.description.ilike(f"%{filters.description}%"))
            if filters.roles:
                where_conditions.append(CollectionDB.roles.overlap(filters.roles))
            if filters.created_by:
                where_conditions.append(DocumentDB.created_by == filters.created_by)
            if filters.created_at_from:
                where_conditions.append(DocumentDB.created_at >= filters.created_at_from)
            if filters.created_at_to:
                where_conditions.append(DocumentDB.created_at <= filters.created_at_to)
            if not filters.include_deleted:
                where_conditions.append(DocumentDB.deleted_at.is_(None))

        return where_conditions
