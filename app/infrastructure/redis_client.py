import json
import redis
import logging

from app.models.document_version import DocumentVersionDB
from app.config.settings import settings

class RedisClient:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")

        self.logger.info(f"Connecting to Redis: {settings.redis.host}:{settings.redis.port},"
                         f" db={settings.redis.db}, password={settings.redis.password}")
        redis_config = dict(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            max_connections=settings.redis.max_connections,
            decode_responses=settings.redis.decode_responses
        )

        if settings.redis.password:
            self.logger.info("Redis password is set")
            redis_config["password"] = settings.redis.password

        self._redis_pool = redis.ConnectionPool(**redis_config)
        self.redis_client = redis.Redis(connection_pool=self._redis_pool)
        self.logger.info("Redis Service initialized")

    def add_document_version(self, document: DocumentVersionDB):
        self.logger.info(f"Adding document to Redis: {document.id}")
        try:
            document_data = {
                "document_id": document.id,
                "file_path": document.file_path,
                "collection": document.document.collection,
            }

            self.redis_client.setnx(
                name=str(document.id),
                value=json.dumps(document_data)
            )

            self.logger.info(f"Document {document.id} added to Redis successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error adding document to Redis: {document.id}")
            self.logger.exception(e)
            raise

    def delete_document(self, document_id: int):
        self.redis_client.delete(str(document_id))
        return True

    def close(self):
        self._redis_pool.close()
