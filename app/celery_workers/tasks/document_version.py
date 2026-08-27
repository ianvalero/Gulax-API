import asyncio
import logging

from celery.signals import worker_process_init, worker_process_shutdown
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode
from llama_index.embeddings.openai import OpenAIEmbedding
from sqlmodel import Session

from app.config.settings import settings
from app.infrastructure import CeleryClient, QdrantGateway, StorageGateway
from app.models import IngestionRunDB, DocumentVersionDB
from app.services import TenantService, KnowledgeSpaceService, DocumentService, DocumentVersionService, IngestionRunService
from app.celery_workers.celery_app import celery_app
from app.database import engine
from app.enums import IngestionRunStatus, ChunkIndexState


logger = logging.getLogger(f"app.{__name__}")

qdrant_gateway: QdrantGateway | None = None
celery_client: CeleryClient | None = None
storage_gateway: StorageGateway | None = None
embedding_model: OpenAIEmbedding | None = None
worker_loop: asyncio.AbstractEventLoop | None = None

document_service: DocumentService | None = None
document_version_service: DocumentVersionService | None = None
ingestion_run_service: IngestionRunService | None = None


@worker_process_init.connect
def init_worker_connections(**kwargs):
    global qdrant_gateway, celery_client, storage_gateway
    global embedding_model, worker_loop, document_service, document_version_service, ingestion_run_service

    logger.info("Starting worker process. Initializing connections...")

    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)

    qdrant_gateway = QdrantGateway()
    celery_client = CeleryClient()
    storage_gateway = StorageGateway()
    embedding_model = OpenAIEmbedding(
        model_name=settings.embedding.model_name,
        api_base=settings.embedding.base_url,
        api_key="EMPTY",
        embed_batch_size=32,
    )

    tenant_service = TenantService(qdrant_gateway=qdrant_gateway)
    knowledge_space_service = KnowledgeSpaceService(tenant_service=tenant_service, qdrant_gateway=qdrant_gateway)
    document_service = DocumentService(
        qdrant_gateway=qdrant_gateway,
        knowledge_space_service=knowledge_space_service,
    )
    ingestion_run_service = IngestionRunService(
        celery_client=celery_client,
        document_service=document_service,
    )
    document_version_service = DocumentVersionService(
        celery_client=celery_client,
        qdrant_gateway=qdrant_gateway,
        storage_gateway=storage_gateway,
        document_service=document_service,
        ingestion_run_service=ingestion_run_service,
    )


@worker_process_shutdown.connect
def shutdown_worker_connections(**kwargs):
    global worker_loop

    if worker_loop is not None and not worker_loop.is_closed():
        logger.info("Shutting down worker process. Closing event loop...")
        worker_loop.close()


def run_async(coro):
    return worker_loop.run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="tasks.process_document_version",
)
def process_document_version(self, ingestion_run_id: int):
    with Session(engine) as session:
        try:
            ingestion_run_db = ingestion_run_service.get_ingestion_run(
                session=session,
                ingestion_run_id=ingestion_run_id
            )

            ingestion_run_service.mark_ingestion_run_as_processing(
                session=session,
                ingestion_run_id=ingestion_run_id,
                celery_task=self.request.id
            )

            document_version_db = ingestion_run_db.document_version

            session.commit()
            _update_task_state(
                task_instance=self,
                state=IngestionRunStatus.PROCESSING,
                ingestion_run_id=ingestion_run_id,
                document_version_id=document_version_db.id,
                step="reading",
            )
            logger.info(f"Processing document version: {document_version_db.id} - {document_version_db.filename}")
        except Exception:
            session.rollback()
            logger.exception(f"Error loading ingestion run: {ingestion_run_id}")
            raise

        try:
            run_async(_embed_and_upload(document_version_db=document_version_db))
        except Exception as err:
            session.rollback()
            logger.exception(f"Error embedding document version: {document_version_db.id}")
            return _fail_and_retry(
                task_instance=self,
                session=session,
                exception=err,
                error_message=f"Error embedding document version: {document_version_db.id}",
                ingestion_run_db=ingestion_run_db,
                document_version_db=document_version_db
            )

        try:
            document_versions_archived = run_async(
                _activate_and_archive_versions(session=session, document_version_db=document_version_db)
            )
            ingestion_run_service.mark_ingestion_run_as_completed(session=session, ingestion_run_id=ingestion_run_id)
            session.commit()

            run_async(_cleanup_archived_chunks(document_versions_archived=document_versions_archived))
            _update_task_state(
                task_instance=self,
                state=IngestionRunStatus.COMPLETED,
                ingestion_run_id=ingestion_run_id,
                document_version_id=document_version_db.id,
            )
        except Exception as err:
            session.rollback()
            logger.exception(f"Error activating/archiving versions in DB for document version: {document_version_db.id}")
            return _fail_and_retry(
                task_instance=self,
                session=session,
                exception=err,
                error_message=f"Error activating/archiving versions in DB for document version: {document_version_db.id}",
                ingestion_run_db=ingestion_run_db,
                document_version_db=document_version_db
            )

        storage_gateway.delete(file_path=document_version_db.file_path)

        return {
            "status": IngestionRunStatus.COMPLETED,
            "ingestion_run_id": ingestion_run_id,
            "document_version_id": document_version_db.id
        }

async def _embed_and_upload(document_version_db: DocumentVersionDB) -> int:
    documents = SimpleDirectoryReader(input_files=[document_version_db.file_path]).load_data()

    splitter = SentenceSplitter(
        chunk_size=settings.embedding.chunk_size,
        chunk_overlap=settings.embedding.chunk_overlap,
    )
    nodes = splitter.get_nodes_from_documents(documents)

    if not nodes:
        raise ValueError(f"Document version {document_version_db.id} produced no chunks")

    texts = [
        node.get_content(metadata_mode=MetadataMode.EMBED)
        for node in nodes
    ]

    embeddings = await embedding_model.aget_text_embedding_batch(texts)

    for chunk_index, (node, embedding) in enumerate(zip(nodes, embeddings, strict=True)):
        parser_metadata = node.metadata
        page = parser_metadata.get("page_label")
        node.metadata = {
            "tenant_id": document_version_db.document.knowledge_space.tenant.id,
            "knowledge_space_id": document_version_db.document.knowledge_space.id,
            "document_id": document_version_db.document.id,
            "document_version_id": document_version_db.id,
            "filename": document_version_db.filename,
            "chunk_index": chunk_index,
            "index_state": ChunkIndexState.STAGING.value,
        }

        if page is not None:
            node.metadata["page"] = page

        node.embedding = embedding

    await document_version_service.delete_document_version_chunks(document_version_id=document_version_db.id)
    await qdrant_gateway.upsert_chunks(nodes=nodes)

    return len(nodes)

async def _activate_and_archive_versions(
    session: Session,
    document_version_db: DocumentVersionDB
) -> list[DocumentVersionDB]:
    await qdrant_gateway.activate_chunks(document_version_id=document_version_db.id)

    document_version_db, document_versions_archived = document_version_service.activate_version_and_archive_previous(
        session=session,
        document_version_id=document_version_db.id
    )
    logger.info(f"Document version {document_version_db.id} activated and previous versions archived")

    return document_versions_archived

async def _cleanup_archived_chunks(document_versions_archived: list[DocumentVersionDB]):
    for document_version_archived in document_versions_archived:
        await document_version_service.delete_document_version_chunks(document_version_id=document_version_archived.id)


def _update_task_state(
    task_instance,
    state: IngestionRunStatus,
    ingestion_run_id: int,
    document_version_id: int,
    **extra
) -> None:
    task_instance.update_state(
        state=state,
        meta={
            "ingestion_run_id": ingestion_run_id,
            "document_version_id": document_version_id,
            **extra
        }
    )

def _fail_and_retry(
        task_instance,
        session: Session,
        exception: Exception,
        error_message: str,
        ingestion_run_db: IngestionRunDB,
        document_version_db: DocumentVersionDB
):
    ingestion_run_service.mark_ingestion_run_as_failed(
        session=session,
        ingestion_run_id=ingestion_run_db.id,
        error_message=error_message
    )

    session.commit()
    logger.error(
        msg=f"{error_message} | {exception} | run={ingestion_run_db.id} | attempt={ingestion_run_db.attempt_number}",
        exc_info=exception
    )

    _update_task_state(
        task_instance=task_instance,
        state=IngestionRunStatus.FAILED,
        ingestion_run_id=ingestion_run_db.id,
        document_version_id=document_version_db.id,
        error=error_message
    )

    if ingestion_run_db.attempt_number >= settings.celery.max_ingestion_attempts:
        return _permanently_failed(
            session=session,
            document_version_db=document_version_db,
            ingestion_run_db=ingestion_run_db
        )

    return _schedule_retry(session=session, document_version_db=document_version_db, ingestion_run_db=ingestion_run_db)

def _permanently_failed(
    session: Session,
    document_version_db: DocumentVersionDB,
    ingestion_run_db: IngestionRunDB
) -> dict:
    document_version_service.mark_document_version_as_failed(
        session=session,
        document_version_id=document_version_db.id
    )

    session.commit()
    run_async(document_version_service.delete_document_version_chunks(document_version_id=document_version_db.id))
    storage_gateway.delete(file_path=document_version_db.file_path)

    return {
        "status": IngestionRunStatus.FAILED,
        "ingestion_run_id": ingestion_run_db.id,
        "document_version_id": document_version_db.id,
        "error": "Max attempts reached. Document version failed."
    }

def _schedule_retry(session: Session, document_version_db: DocumentVersionDB, ingestion_run_db: IngestionRunDB) -> dict:
    new_ingestion_run = ingestion_run_service.register_retry_run(
        session=session,
        document_version_id=document_version_db.id
    )

    session.commit()
    celery_client.process_document_version(
        ingestion_run_id=new_ingestion_run.id,
        countdown=settings.celery.countdown_retry_delay
    )

    return {
        "status": "retry_scheduled",
        "ingestion_run_id": ingestion_run_db.id,
        "document_version_id": document_version_db.id,
        "new_ingestion_id_scheduled": new_ingestion_run.id,
    }