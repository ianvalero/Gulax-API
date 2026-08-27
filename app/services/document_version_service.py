from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.config.settings import settings
from app.services.document_service import DocumentService
from app.services.ingestion_run_service import IngestionRunService
from app.repositories.document_version import DocumentVersionRepository
from app.infrastructure import StorageGateway, CeleryClient, QdrantGateway
from app.models.document_version import DocumentVersionDB
import app.schemas.document_version as DocumentVersionSchema
from app.schemas.user import User
from app.exceptions import DocumentVersionNotFoundError, DocumentVersionConflictError, CeleryTaskEnqueueError

if TYPE_CHECKING:
    from fastapi import UploadFile


class DocumentVersionService:
    def __init__(
        self,
        celery_client: CeleryClient,
        qdrant_gateway: QdrantGateway,
        storage_gateway: StorageGateway,
        document_service: DocumentService,
        ingestion_run_service: IngestionRunService
    ):
        self.logger = logging.getLogger(f"app.{__name__}")
        self._celery_client = celery_client
        self._qdrant_gateway = qdrant_gateway
        self._storage_gateway = storage_gateway
        self.document_service = document_service
        self.ingestion_run_service = ingestion_run_service
        self.document_version_repository = DocumentVersionRepository()
        self.logger.info("Document Version Service initialized")

    async def get_document_versions(
        self,
        session: Session,
        user: User,
        document_id: int,
        params: DocumentVersionSchema.DocumentVersionQueryParams,
    ) -> tuple[list[DocumentVersionSchema.DocumentVersionRead], int]:
        await self.__check_document_permissions(session=session, user=user, document_id=document_id)
        document_versions_db, total = self.document_version_repository.get_document_versions(
            session=session,
            document_id=document_id,
            params=params
        )

        document_versions_read = [
            DocumentVersionSchema.DocumentVersionRead.model_validate(document_version_db)
            for document_version_db in document_versions_db
        ]
        return document_versions_read, total

    async def get_document_version(
        self,
        session: Session,
        user: User,
        document_id: int,
        document_version_id: int
    ) -> DocumentVersionSchema.DocumentVersionReadDetail:
        await self.__check_document_permissions(session=session, user=user, document_id=document_id)

        document_version_db = self.document_version_repository.get_document_version(
            session=session,
            document_version_id=document_version_id
        )

        if not document_version_db or document_id != document_version_db.document_id:
            raise DocumentVersionNotFoundError(f"Version {document_version_id} not found")

        return DocumentVersionSchema.DocumentVersionReadDetail.model_validate(document_version_db)

    async def add_document_version(
        self,
        session: Session,
        user: User,
        document_id: int,
        file: UploadFile
    ) -> DocumentVersionSchema.DocumentVersionReadDetail:
        await self.__check_document_permissions(session=session, user=user, document_id=document_id)

        document_version_path = await self._storage_gateway.save(file=file)
        for attempt in range(settings.max_version_retries):
            next_version_number = self.document_version_repository.get_next_version_number(
                session=session,
                document_id=document_id,
            )

            document_version_db: DocumentVersionDB = DocumentVersionDB(
                document_id=document_id,
                version_number=next_version_number,
                filename=file.filename,
                file_path=str(document_version_path),
                file_size=file.size,
                mime_type=file.content_type,
                uploaded_by=user.username,
            )

            try:
                with session.begin_nested():
                    document_version_db = self.document_version_repository.add_document_version(
                        session=session,
                        document_version=document_version_db
                    )

                    ingestion_run_db = self.ingestion_run_service.create_ingestion_run(
                        session=session,
                        document_version_id=document_version_db.id
                    )
                    break
            except IntegrityError:
                session.rollback()
                continue
        else:
            raise DocumentVersionConflictError(
                f"Failed to add document version for document {document_id}: "
                f"Max retries reached to get next version number ({settings.max_version_retries} retries)"
            )

        session.commit()
        session.refresh(document_version_db)
        session.refresh(ingestion_run_db)

        try:
            self._celery_client.process_document_version(ingestion_run_id=ingestion_run_db.id)
        except Exception as err:
            self.document_version_repository.update_version_as_failed(
                session=session,
                document_version=document_version_db
            )

            self.ingestion_run_service.mark_ingestion_run_as_failed(
                session=session,
                ingestion_run_id=ingestion_run_db.id,
                error_message="Failed to enqueue Celery task",
            )

            session.commit()

            try:
                self._storage_gateway.delete(file_path=document_version_path)
            except OSError:
                self.logger.warning(f"Could not remove file {document_version_path}")

            raise CeleryTaskEnqueueError(
                f"Failed to enqueue Celery task to process a new document version for document {document_id}"
            ) from err

        return DocumentVersionSchema.DocumentVersionReadDetail.model_validate(document_version_db)

    def activate_version_and_archive_previous(
        self,
        session: Session,
        document_version_id: int,
    ) -> tuple[DocumentVersionDB, list[DocumentVersionDB]]:
        document_version_db = self.document_version_repository.get_document_version(
            session=session,
            document_version_id=document_version_id
        )

        if not document_version_db:
            raise DocumentVersionNotFoundError(f"Version {document_version_id} not found")

        previous_versions = self.document_version_repository.get_document_active_versions(
            session=session,
            document_id=document_version_db.document_id,
        )

        archived_versions = []
        for previous_version in previous_versions:
            if previous_version.id == document_version_id:
                continue

            self.document_version_repository.update_version_as_archived(
                session=session,
                document_version=previous_version,
            )
            archived_versions.append(previous_version)

        self.document_version_repository.update_version_as_active(session=session, document_version=document_version_db)

        return document_version_db, archived_versions

    def mark_document_version_as_failed(
        self,
        session: Session,
        document_version_id: int,
    ) -> DocumentVersionDB:
        document_version_db = self.document_version_repository.get_document_version(
            session=session,
            document_version_id=document_version_id
        )

        if not document_version_db:
            raise DocumentVersionNotFoundError(f"Version {document_version_id} not found")

        self.document_version_repository.update_version_as_failed(session=session, document_version=document_version_db)

        return document_version_db

    async def delete_document_version_chunks(self, document_version_id: int) -> bool:
        try:
            await self._qdrant_gateway.delete_document_version(document_version_id=document_version_id)
        except Exception:
            self.logger.exception(f"Error deleting points from Qdrant for document_version_id={document_version_id}")

        return True

    async def __check_document_permissions(self, session: Session, user: User, document_id: int):
        await self.document_service.get_document(session=session, user=user, document_id=document_id)
        return True