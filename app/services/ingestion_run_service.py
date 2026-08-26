import logging

from sqlmodel import Session

from app.services import DocumentService
from app.repositories.ingestion_run import IngestionRunRepository
from app.infrastructure.celery_client import CeleryClient
from app.models.ingestion_run import IngestionRunDB
from app.exceptions import IngestionRunNotFoundError



class IngestionRunService:
    def __init__(self, celery_client: CeleryClient, document_service: DocumentService):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.celery = celery_client
        self.document_service = document_service
        self.ingestion_run_repository = IngestionRunRepository()
        self.logger.info("Ingestion Run Service initialized")

    def get_ingestion_run(self, session: Session, ingestion_run_id: int) -> IngestionRunDB:
        ingestion_run_db = self.ingestion_run_repository.get_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
        )

        if not ingestion_run_db:
            raise IngestionRunNotFoundError(f"Ingestion run {ingestion_run_id} not found")

        return ingestion_run_db

    def create_ingestion_run(self, session: Session, document_version_id: int) -> IngestionRunDB:
        attempt_number = self.ingestion_run_repository.get_next_attempt_number(
            session=session,
            document_version_id=document_version_id
        )

        ingestion_run_db = IngestionRunDB(document_version_id=document_version_id, attempt_number=attempt_number)
        self.ingestion_run_repository.create_ingestion_run(session=session, ingestion_run=ingestion_run_db)

        self.logger.info(f"Ingestion Run {ingestion_run_db.id} created for document version {document_version_id}"
                         f" | SQL ID: {ingestion_run_db.id}")

        return ingestion_run_db

    def register_retry_run(self,session: Session, document_version_id: int) -> IngestionRunDB:
        self.logger.info(f"Registering retry run for document version {document_version_id}")
        ingestion_run_db = self.create_ingestion_run(session=session, document_version_id=document_version_id)
        return ingestion_run_db

    def mark_ingestion_run_as_processing(
        self,
        session: Session,
        ingestion_run_id: int,
        celery_task: str
    ) -> IngestionRunDB:
        ingestion_run_db = self.ingestion_run_repository.get_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
        )

        if not ingestion_run_db:
            raise IngestionRunNotFoundError(f"Ingestion run {ingestion_run_id} not found")

        self.ingestion_run_repository.update_ingestion_run_as_processing(
            session=session,
            ingestion_run=ingestion_run_db,
            celery_task=celery_task
        )

        return ingestion_run_db

    def mark_ingestion_run_as_completed(self, session: Session, ingestion_run_id: int) -> IngestionRunDB:
        ingestion_run_db = self.ingestion_run_repository.get_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
        )

        if not ingestion_run_db:
            raise IngestionRunNotFoundError(f"Ingestion run {ingestion_run_id} not found")

        self.ingestion_run_repository.update_ingestion_run_as_completed(session=session, ingestion_run=ingestion_run_db)

        return ingestion_run_db

    def mark_ingestion_run_as_failed(
        self,
        session: Session,
        ingestion_run_id: int,
        error_message: str
    ) -> IngestionRunDB:
        ingestion_run_db = self.ingestion_run_repository.get_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
        )

        if not ingestion_run_db:
            raise IngestionRunNotFoundError(f"Ingestion run {ingestion_run_id} not found")

        self.ingestion_run_repository.update_ingestion_run_as_failed(
            session=session,
            ingestion_run=ingestion_run_db,
            error_message=error_message
        )

        return ingestion_run_db
