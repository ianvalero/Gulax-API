from pydantic import BaseModel, Field, ConfigDict, field_validator

from app.enums import CollectionDistance, ChunkIndexState


class HNSWConfig(BaseModel):
    m: int = Field(gt=0, description="Maximum number of connections per node")
    ef_construct: int = Field(gt=0, description="Index quality during construction")


class CollectionCreateQdrant(BaseModel):
    name: str = Field(min_length=1)
    size: int = Field(gt=0, description="Number of dimensions for each vector")
    distance: CollectionDistance = Field(
        default=CollectionDistance.COSINE,
        description="Distance metric used to calculate similarity between vectors"
    )
    shard_number: int | None = Field(default=1, description="Number of shards used to partition the collection")
    replication_factor: int | None = Field(default=1, description="Number of replicas for high availability")
    on_disk_payload: bool | None = Field(default=True,description="Store payload metadata on disk instead of in RAM")
    hnsw_config: HNSWConfig | None = None

    model_config = ConfigDict(extra="forbid")


class ChunkUpsert(BaseModel):
    tenant_id: int = Field(gt=0)
    knowledge_space_id: int = Field(gt=0)
    document_id: int = Field(gt=0)
    document_version_id: int = Field(gt=0)
    chunk_index: int = Field(ge=0)
    text: str
    embedding: list[float] = Field(min_length=1)
    index_state: ChunkIndexState = ChunkIndexState.STAGING
    filename: str | None = None
    page: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("page", mode="before")
    @classmethod
    def page_to_str(cls, value: object) -> str | None:
        if value is None:
            return None

        page = str(value).strip()
        return page or None


