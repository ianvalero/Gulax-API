import asyncio
import logging
import os

from celery.exceptions import MaxRetriesExceededError
from celery.signals import worker_process_init, worker_process_shutdown
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode
from llama_index.embeddings.openai import OpenAIEmbedding
from sqlmodel import Session

from app.celery_workers.celery_app import celery_app
from app.config.settings import settings
from app.database import engine
from app.models.document_version import DocumentVersionDB
from app.infrastructure.qdrant_gateway import QdrantGateway
from app.repositories.document_version import DocumentVersionRepository
from app.exceptions import DocumentNotFoundError

logger = logging.getLogger(f"app.{__name__}")

qdrant_gateway: QdrantGateway | None = None
document_version_repository: DocumentVersionRepository | None = None
embedding_model: OpenAIEmbedding | None = None
worker_loop: asyncio.AbstractEventLoop | None = None


@worker_process_init.connect
def init_worker_connections(**kwargs):
    global qdrant_gateway, document_version_repository, embedding_model, worker_loop

    logger.info("Starting worker process. Initializing connections...")

    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)

    qdrant_gateway = QdrantGateway()
    document_version_repository = DocumentVersionRepository()
    embedding_model = OpenAIEmbedding(
        model_name=settings.embedding.model_name,
        api_base=settings.embedding.base_url,
        api_key="EMPTY",
        embed_batch_size=32,
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
    max_retries=3,
    default_retry_delay=60,
    name="tasks.process_document_version",
)
def process_document_version(self, ingestion_run_id: int):
    pass
    # with Session(engine) as session:
    #     document_version_db = document_version_repository.get_document_version(session, document_version_id)
    #     if not document_version_db:
    #         logger.error(f"Document version {document_version_id} not found")
    #         raise self.retry(exc=DocumentNotFoundError(f"Document version {document_version_id} not found"))
    #
    #     collection_name = document_version_db.document.collection.qdrant_name
    #
    #     if not run_async(qdrant_gateway.collection_exists(collection_name)):
    #         document_version_repository.update_version_as_failed(
    #             session=session,
    #             document_version=document_version_db,
    #             error_message=f"Collection {collection_name} not found"
    #         )
    #         session.commit()
    #         raise CollectionNotFoundError(f"Collection {collection_name} not found")
    #
    #     document_version_repository.update_version_as_processing(
    #         session=session,
    #         document_version=document_version_db
    #     )
    #     session.commit()
    #
    #     self.update_state(state="PROGRESS", meta={"step": "reading", "document_id": document_version_db.document_id})
    #     logger.info(f"Processing document version: {document_version_db.id} - {document_version_db.filename}")
    #
    #     try:
    #         point_ids = run_async(
    #             _embed_and_upload(
    #                 file_path=document_version_db.file_path,
    #                 collection_name=collection_name,
    #                 document_version_id=document_version_db.id,
    #             )
    #         )
    #     except Exception as err:
    #         logger.exception(f"Error embedding and uploading points for document version: {document_version_db.id}")
    #         document_version_repository.update_version_as_failed(
    #             session=session,
    #             document_version=document_version_db,
    #             error_message=f"Error embedding and uploading points for document version: {document_version_db.id}"
    #         )
    #         session.commit()
    #         return _trigger_retry_or_fail(self, err, document_version_db.file_path)
    #
    #     try:
    #         _activate_and_archive_versions(session=session, document_version=document_version_db, point_ids=point_ids)
    #         logger.info(f"Version {document_version_db.id} processed: {len(point_ids)} points")
    #     except Exception as err:
    #         document_version_repository.update_version_as_failed(
    #             session=session,
    #             document_version=document_version_db,
    #             error_message=f"Error activating/archiving versions in DB"
    #         )
    #         session.commit()
    #         return _trigger_retry_or_fail(self, err, document_version_db.file_path)
    #
    #     _delete_local_file(file_path=document_version_db.file_path)
    #     return {"document_version_id": document_version_db.id, "points_count": len(point_ids)}

async def _embed_and_upload(file_path: str, collection_name: str, document_version_id: int) -> list[str]:
    pass
    # documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
    #
    # splitter = SentenceSplitter(
    #     chunk_size=settings.embedding.chunk_size,
    #     chunk_overlap=settings.embedding.chunk_overlap,
    # )
    # nodes = splitter.get_nodes_from_documents(documents)
    #
    # if not nodes:
    #     return []
    #
    # for node in nodes:
    #     node.metadata["document_version_id"] = document_version_id
    #
    # texts = [node.get_content(metadata_mode=MetadataMode.EMBED) for node in nodes]
    # embeddings = await embedding_model.aget_text_embedding_batch(texts)
    #
    # for node, embedding in zip(nodes, embeddings):
    #     node.embedding = embedding
    #
    # vector_store = await qdrant_gateway.get_vector_store(collection_name)
    # point_ids = await vector_store.async_add(nodes)
    #
    # return [str(pid) for pid in point_ids]

def _archive_previous_versions(document_id: int, current_version_id: int, collection_name: str, session: Session) -> None:
    pass
    # active_versions_db = document_version_repository.get_document_active_versions(session, document_id)
    #
    # previous_versions = [
    #     version for version in active_versions_db
    #     if version.id != current_version_id
    # ]
    #
    # for version in previous_versions:
    #     if version.qdrant_point_ids:
    #         try:
    #             run_async(
    #                 qdrant_gateway.delete_points(
    #                     collection_name=collection_name,
    #                     point_ids=version.qdrant_point_ids,
    #                 )
    #             )
    #         except Exception:
    #             logger.exception(f"Failed to delete Qdrant points for version {version.id}")
    #             continue
    #
    #     document_version_repository.update_version_as_archived(
    #         session=session,
    #         document_version=version
    #     )
    #
    # if previous_versions:
    #     logger.info(f"Archived {len(previous_versions)} previous version(s) of document {document_id}")

def _activate_and_archive_versions(session: Session, document_version: DocumentVersionDB, point_ids: list[str]):
    pass
    # try:
    #     document_version_repository.update_version_as_active(
    #         session=session,
    #         document_version=document_version,
    #         qdrant_point_ids=point_ids,
    #     )
    #     logger.info(f"Document version {document_version.id} processed: {len(point_ids)} points")
    #
    #     _archive_previous_versions(
    #         document_id=document_version.document_id,
    #         current_version_id=document_version.id,
    #         collection_name=document_version.document.collection.qdrant_name,
    #         session=session,
    #     )
    #
    #     session.commit()
    # except Exception as err:
    #     session.rollback()
    #     logger.exception(f"Error activating/archiving versions in DB")
    #
    #     if point_ids:
    #         try:
    #             run_async(qdrant_gateway.delete_points(
    #                 collection_name=document_version.document.collection.qdrant_name,
    #                 point_ids=point_ids)
    #             )
    #         except Exception as qdrant_err:
    #             logger.exception(f"Error deleting points from Qdrant: {str(qdrant_err)}")
    #
    #     raise err

def _delete_local_file(file_path: str) -> bool:
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Local file deleted: {file_path}")
        return True

    except Exception:
        logger.exception(f"Error deleting local file {file_path}")
        return False

def _trigger_retry_or_fail(task_instance, exception: Exception, file_path: str):
    try:
        raise task_instance.retry(exc=exception)
    except MaxRetriesExceededError:
        _delete_local_file(file_path)
        raise