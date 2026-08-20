from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator

from app.enums import CollectionDistance


class PostgresSettings(BaseSettings):
    host: str
    port: int = 5432
    user: str
    password: str
    db: str
    postgres_url: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="POSTGRESQL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class RedisSettings(BaseSettings):
    host: str
    port: int = 6379
    db: int = 0
    password: str | None = None
    max_connections: int = 20
    decode_responses: bool = True

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class CelerySettings(BaseSettings):
    broker_url: str | None = None
    result_backend: str | None = None
    task_serializer: str = "json"
    result_serializer: str = "json"
    result_expires: int = 86400
    task_track_started: bool = True
    worker_max_tasks_per_child: int = 200

    model_config = SettingsConfigDict(
        env_prefix="CELERY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class QdrantSettings(BaseSettings):
    url: str
    size: int                                                   # Número de dimensiones de cada vector - ¡Tiene que ser lo que indique el modelo de embbeding!
    distance: CollectionDistance = CollectionDistance.COSINE    # Define como se calcula la similitud entre vectores
    shard_number: int = 1                                       # Divide la colección en particiones
    replication_factor: int = 1                                 # Duplica datos para alta disponibilidad
    on_disk_payload: bool = True                                # Guardar metadata en disco en lugar de RAM
    node_conexions_number: int = 16                             # Número de conexiones por nodo
    ef_construct: int = 200                                     # Calidad del índice al construirlo

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class EmbeddingSettings(BaseSettings):
    model_name: str
    base_url: str
    chunk_size: int
    chunk_overlap: int

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class Settings(BaseSettings):
    log_level: str = "INFO"
    sql_log: bool = False
    automation_api_token: str
    proxy_url: str | None = None
    files_storage_path: str = "/files"

    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)

    @model_validator(mode="after")
    def assemble_celery_urls(self):
        base_redis_url = f"redis://{self.redis.host}:{self.redis.port}"
        if self.redis.password:
            base_redis_url = f"redis://{self.redis.password}@{self.redis.host}:{self.redis.port}"

        if not self.celery.broker_url:
            self.celery.broker_url = f"{base_redis_url}/2"
        if not self.celery.result_backend:
            self.celery.result_backend = f"{base_redis_url}/3"

        return self

    @model_validator(mode="after")
    def assemble_postgres_urls(self):
        self.postgres.postgres_url = (f"postgresql+psycopg2://{self.postgres.user}:{self.postgres.password}@"
                                      f"{self.postgres.host}:{self.postgres.port}/{self.postgres.db}")
        return self

    @model_validator(mode="after")
    def create_files_storage_path(self):
        Path(self.files_storage_path).mkdir(parents=True, exist_ok=True)
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()