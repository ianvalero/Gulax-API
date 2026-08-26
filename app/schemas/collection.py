from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from app.enums import CollectionDistance


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


