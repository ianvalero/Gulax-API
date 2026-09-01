from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import Request

import app.infrastructure as infrastructure

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding


def get_redis_service(request: Request) -> infrastructure.RedisClient:
    return request.app.state.redis_client

def get_qdrant_service(request: Request) -> infrastructure.QdrantGateway:
    return request.app.state.qdrant_gateway

def get_celery_service(request: Request) -> infrastructure.CeleryClient:
    return request.app.state.celery_client

def get_storage_service(request: Request) -> infrastructure.StorageGateway:
    return request.app.state.storage_gateway

def get_embedding_model(request: Request) -> BaseEmbedding:
    return request.app.state.embedding_model