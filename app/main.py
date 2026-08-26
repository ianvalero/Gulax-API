import logging

from app.exceptions import AppException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

from app.config.log import setup_logging
from app.config.settings import settings
from app.routers import tenant, document, document_version, user, knowledge_space
from app.schemas.collection import CollectionCreateQdrant, HNSWConfig
import app.services as services
import app.infrastructure as infrastructure

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = logging.getLogger(f"app.{__name__}")
    logger.info("Starting application")

    LlamaIndexInstrumentor().instrument()

    app.state.qdrant_gateway = infrastructure.QdrantGateway()
    app.state.redis_client = infrastructure.RedisClient()
    app.state.celery_client = infrastructure.CeleryClient()
    app.state.storage_gateway = infrastructure.StorageGateway()

    await app.state.qdrant_gateway.ensure_collection(
        CollectionCreateQdrant(
            name=settings.qdrant.collection_name,
            size=settings.qdrant.size,
            distance=settings.qdrant.distance,
            shard_number=settings.qdrant.shard_number,
            replication_factor=settings.qdrant.replication_factor,
            on_disk_payload=settings.qdrant.on_disk_payload,
            hnsw_config=HNSWConfig(
                m=settings.qdrant.node_conexions_number,
                ef_construct=settings.qdrant.ef_construct,
            ),
        )
    )

    app.state.tenant_service = services.TenantService(qdrant_gateway=app.state.qdrant_gateway)
    app.state.knowledge_space_service = services.KnowledgeSpaceService(
        tenant_service=app.state.tenant_service,
        qdrant_gateway=app.state.qdrant_gateway
    )
    app.state.document_service = services.DocumentService(
        knowledge_space_service=app.state.knowledge_space_service,
        qdrant_gateway=app.state.qdrant_gateway,
    )
    app.state.ingestion_run_service = services.IngestionRunService(
        celery_client=app.state.celery_client,
        document_service=app.state.document_service
    )
    app.state.document_version_service = services.DocumentVersionService(
        celery_client=app.state.celery_client,
        qdrant_gateway=app.state.qdrant_gateway,
        storage_gateway=app.state.storage_gateway,
        document_service=app.state.document_service,
        ingestion_run_service=app.state.ingestion_run_service
    )
    app.state.user_service = services.UserService(tenant_service=app.state.tenant_service)

    yield
    await app.state.qdrant_gateway.close()
    app.state.redis_client.close()

    logger.info("Stopping application")

app = FastAPI(
    title="Qdrant Management",
    description="API for Qdrant Management",
    version="0.1.0",
    lifespan=lifespan
)

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

app.include_router(user.router)
app.include_router(tenant.router)
app.include_router(knowledge_space.router)
app.include_router(knowledge_space.create_knowledge_space_router)
app.include_router(document.create_document_router)
app.include_router(document.router)
app.include_router(document_version.router)
