from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
import os
import uuid
import aiofiles
import logging

from sqlmodel import Session

from app.config.settings import settings
from app.services import DocumentService
from app.repositories.document_version import DocumentVersionRepository
from app.infrastructure.celery_client import CeleryClient
from app.models.document_version import DocumentVersionDB
import app.schemas.document_version as DocumentVersionSchema
from app.schemas.user import User
from app.exceptions import DocumentVersionNotFoundError, CeleryTaskEnqueueError

if TYPE_CHECKING:
    from fastapi import UploadFile


class DocumentVersionService:
    def __init__(self, celery_client: CeleryClient, document_service: DocumentService):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.celery = celery_client
        self.document_service = document_service
        self.document_version_repository = DocumentVersionRepository()
        self.logger.info("Document Version Service initialized")

    async def get_document_versions(
        self,
        session: Session,
        user: User,
        document_id: int,
        filters: DocumentVersionSchema.DocumentVersionFilters | None = None,
        offset: int = 0,
        limit: int = 100
    ) -> tuple[list[DocumentVersionSchema.DocumentVersionRead], int]:
        await self.__check_document_permissions(session=session, user=user, document_id=document_id)
        document_versions_db, total = self.document_version_repository.get_document_versions(
            session=session,
            document_id=document_id,
            offset=offset,
            limit=limit,
            filters=filters
        )

        document_versions_read = [
            DocumentVersionSchema.DocumentVersionRead(**document_version_db.model_dump())
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

        if not document_version_db or document_version_db.document_id != document_id:
            raise DocumentVersionNotFoundError(f"Version {document_version_id} not found in document {document_id}")

        return DocumentVersionSchema.DocumentVersionReadDetail(**document_version_db.model_dump())

    async def add_document_version(
        self,
        session: Session,
        user: User,
        document_id: int,
        file: UploadFile
    ) -> DocumentVersionSchema.DocumentVersionReadDetail:
        await self.__check_document_permissions(session=session, user=user, document_id=document_id)

        document_version_path = await self.__save_document_version_file(file=file)
        document_version_db: DocumentVersionDB = DocumentVersionDB(
            document_id=document_id,
            filename=Path(document_version_path).name,
            original_filename=file.filename,
            file_path=document_version_path,
            file_size=file.size,
            mime_type=file.content_type,
            uploaded_by=user.username,
        )

        document_version_db = self.document_version_repository.add_document_version(
            session=session,
            document_version=document_version_db
        )

        try:
            task_id = self.celery.update_document_version(document_version_id=document_version_db.id)
            document_version_db = self.document_version_repository.set_document_version_task_id(
                session=session,
                document_version=document_version_db,
                task_id=task_id
            )

        except Exception as err:
            self.document_version_repository.update_version_as_failed(
                session=session,
                document_version=document_version_db,
                error_message=f"Failed to enqueue Celery task to process a new document"
                              f" version {document_version_db.id} for document {document_id}"
            )
            session.commit()
            raise CeleryTaskEnqueueError(
                f"Failed to enqueue Celery task to process a new document version for document {document_id}"
            ) from err

        session.commit()
        session.refresh(document_version_db)

        return DocumentVersionSchema.DocumentVersionReadDetail(**document_version_db.model_dump())

    async def __save_document_version_file(self, file: UploadFile):
        original_name, extension = os.path.splitext(os.path.basename(file.filename))
        original_name = original_name.replace(" ", "_")

        save_path = os.path.join(
            settings.files_storage_path,
            f"{str(uuid.uuid4())}_{original_name}{extension}"
        )
        async with aiofiles.open(save_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                await buffer.write(chunk)

        self.logger.info(f"Document version file {file.filename} saved to {save_path}")
        return save_path

    async def __check_document_permissions(self, session: Session, user: User, document_id: int):
        await self.document_service.get_document(session=session, user=user, document_id=document_id)
        return True