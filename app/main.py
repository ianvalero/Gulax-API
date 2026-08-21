import logging

from app.exceptions import AppException
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from openinference.instrumentation.llama_index import LlamaIndexInstrumentor

from app.config.log import setup_logging
from app.routers import tenant, document, document_version, user, knowledge_space
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

    app.state.tenant_service = services.TenantService()
    app.state.knowledge_space_service = services.KnowledgeSpaceService(
        tenant_service=app.state.tenant_service
    )
    app.state.document_service = services.DocumentService(
        qdrant_gateway=app.state.qdrant_gateway,
        knowledge_space_service=app.state.knowledge_space_service
    )
    app.state.document_version_service = services.DocumentVersionService(
        celery_client=app.state.celery_client,
        document_service=app.state.document_service
    )
    app.state.user_service = services.UserService()

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
