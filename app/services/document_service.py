import logging
from sqlmodel import Session

# from app.services import CollectionService
from app.repositories.document import DocumentRepository
from app.models.document import DocumentDB
from app.infrastructure.qdrant_gateway import QdrantGateway
import app.schemas.document as DocumentSchema
from app.schemas.user import User
from app.exceptions import DocumentNotFoundError, QdrantOperationError


class DocumentService:
    def __init__(self, qdrant_gateway: QdrantGateway):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.qdrant = qdrant_gateway
        self.document_repository = DocumentRepository()
        self.logger.info("Document Service initialized")

    async def get_documents(
        self,
        session: Session,
        user: User,
        params: DocumentSchema.DocumentQueryParams
    ) -> tuple[list[DocumentSchema.DocumentRead], int]:
        if params.collection_id:
            await self.collection_service.check_access(
                session=session,
                user=user,
                collection_id=params.collection_id
            )
            collection_ids = [params.collection_id]
        else:
            collection_ids = await self.collection_service.get_collection_ids(session=session, user=user)
            if not collection_ids:
                return [], 0

        documents_db, total = self.document_repository.get_documents(
            session=session,
            collection_ids=collection_ids,
            params=params,
        )

        documents_read = [
            DocumentSchema.DocumentRead.model_validate(document_db)
            for document_db in documents_db
        ]
        return documents_read, total

    async def get_document(self, session: Session, user: User, document_id: int) -> DocumentSchema.DocumentRead:
        document_db = await self.__fetch_document(session=session, user=user, document_id=document_id)
        return DocumentSchema.DocumentRead.model_validate(document_db)

    async def add_document(
        self,
        session: Session,
        user: User,
        collection_id: int,
        document: DocumentSchema.DocumentCreate
    ) -> DocumentSchema.DocumentRead:
        await self.collection_service.check_access(
            session=session,
            user=user,
            collection_id=collection_id
        )
        document_db: DocumentDB = DocumentDB(
            **document.model_dump(),
            collection_id=collection_id,
            created_by=user.username
        )
        self.document_repository.add_document(session=session, document=document_db)

        session.commit()
        session.refresh(document_db)

        self.logger.info(f"Document {document_db.id} added to database")
        return DocumentSchema.DocumentRead.model_validate(document_db)

    async def update_document(
        self,
        session: Session,
        user: User,
        document_id: int,
        data: DocumentSchema.DocumentUpdate
    ) -> DocumentSchema.DocumentRead:
        document_db = await self.__fetch_document(session=session, user=user, document_id=document_id)

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(document_db, field, value)
        document_db.updated_by = user.username

        self.document_repository.update_document(session=session, document=document_db)
        session.commit()
        session.refresh(document_db)

        self.logger.info(f"Document {document_db.id} updated")
        return DocumentSchema.DocumentRead.model_validate(document_db)

    async def delete_document(self, session: Session, user: User, document_id: int) -> bool:
        document_db = await self.__fetch_document(session=session, user=user, document_id=document_id)
        document_db.deleted_by = user.username

        self.document_repository.delete_document(session=session, document=document_db)

        active_version = document_db.documents_versions[0] if document_db.documents_versions else None
        try:
            if active_version and active_version.qdrant_point_ids:
                await self.qdrant.delete_points(
                    collection_name=document_db.collection.qdrant_name,
                    point_ids=active_version.qdrant_point_ids
                )

            session.commit()
            self.logger.info(f"Document {document_id} marked as deleted in database")
            return True
        except Exception as err:
            session.rollback()
            self.logger.exception(f"Error deleting document {document_id} from Qdrant")
            raise QdrantOperationError(f"Error deleting document {document_id} from Qdrant") from err

    async def __fetch_document(self, session: Session, user: User, document_id: int) -> DocumentDB:
        document_db = self.document_repository.get_document(
            session=session,
            document_id=document_id
        )

        if not document_db:
            raise DocumentNotFoundError(f"Document {document_id} not found")

        await self.collection_service.check_access(
            session=session,
            user=user,
            collection_id=document_db.collection_id
        )

        return document_db