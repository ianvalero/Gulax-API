from fastapi import Request

import app.infrastructure as infrastructure


def get_redis_service(request: Request) -> infrastructure.RedisClient:
    return request.app.state.redis_client

def get_qdrant_service(request: Request) -> infrastructure.QdrantGateway:
    return request.app.state.qdrant_gateway

def get_celery_service(request: Request) -> infrastructure.CeleryClient:
    return request.app.state.celery_client