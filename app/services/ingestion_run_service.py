import logging
from datetime import datetime, timezone

from sqlmodel import Session

from app.services import DocumentService
from app.repositories.ingestion_run import IngestionRunRepository
from app.infrastructure.celery_client import CeleryClient
from app.models.ingestion_run import IngestionRunDB
import app.schemas.ingestion_run as IngestionRunSchema
from app.schemas.user import User
from app.enums import IngestionRunStatus
from app.exceptions import IngestionRunNotFoundError



class IngestionRunService:
    def __init__(self, celery_client: CeleryClient, document_service: DocumentService):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.celery = celery_client
        self.document_service = document_service
        self.ingestion_run_repository = IngestionRunRepository()
        self.logger.info("Ingestion Run Service initialized")

    def create_ingestion_run(self, session: Session, document_version_id: int) -> IngestionRunDB:
        attempt_number = self.ingestion_run_repository.get_next_attempt_number(
            session=session,
            document_version_id=document_version_id
        )

        ingestion_run_db = IngestionRunDB(
            document_version_id=document_version_id,
            attempt_number=attempt_number,
            status=IngestionRunStatus.PENDING,
        )
        self.ingestion_run_repository.create_ingestion_run(session=session,ingestion_run=ingestion_run_db)

        self.logger.info(f"Ingestion Run {ingestion_run_db.id} created for document version {document_version_id}"
                         f" | SQL ID: {ingestion_run_db.id}")

        return ingestion_run_db

    def register_retry_run(self,session: Session, document_version_id: int) -> IngestionRunSchema.IngestionRunRead:
        self.logger.info(f"Registering retry run for document version {document_version_id}")
        ingestion_run_db = self.create_ingestion_run(session=session, document_version_id=document_version_id)

        session.commit()
        session.refresh(ingestion_run_db)

        return IngestionRunSchema.IngestionRunRead.model_validate(ingestion_run_db)

    def assign_celery_task(self, session: Session, ingestion_run: IngestionRunDB, celery_task_id: str) -> IngestionRunDB:
        ingestion_run.celery_task_id = celery_task_id
        session.flush()
        return ingestion_run

    def mark_as_failed(self, session: Session, ingestion_run_id: int, error_message: str) -> IngestionRunDB:
        ingestion_run_db = self.ingestion_run_repository.get_ingestion_run(
            session=session,
            ingestion_run_id=ingestion_run_id,
        )

        if not ingestion_run_db:
            raise IngestionRunNotFoundError(f"Ingestion run {ingestion_run_id} not found")

        ingestion_run_db.status = IngestionRunStatus.FAILED
        ingestion_run_db.error_message = error_message
        ingestion_run_db.finished_at = datetime.now(timezone.utc)

        session.flush()

        return ingestion_run_db
