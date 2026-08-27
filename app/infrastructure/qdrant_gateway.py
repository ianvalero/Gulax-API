import logging
import uuid

from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http.models import (
    VectorParams, Distance, HnswConfigDiff, PointStruct,
    PayloadSchemaType, Filter, FieldCondition, MatchValue, FilterSelector
)

from app.config.settings import settings
from app.schemas.collection import CollectionCreateQdrant
from app.enums import ChunkIndexState


QDRANT_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "gulax.qdrant")
QDRANT_INDEXES_PAYLOAD_FIELDS = (
    "tenant_id",
    "knowledge_space_id",
    "document_id",
    "document_version_id"
)

class QdrantGateway:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self._qdrant_client = QdrantClient(url=settings.qdrant.url)
        self._qdrant_aclient = AsyncQdrantClient(url=settings.qdrant.url)
        self.logger.info("Qdrant Client initialized")

    async def ensure_collection(self, collection: CollectionCreateQdrant):
        if await self._collection_exists(collection.name):
            return True

        try:
            await self._create_collection(collection)
            await self._create_indexes(collection.name)
        except Exception:
            if await self._collection_exists(collection.name):
                return True
            raise

        return True

    async def upsert_chunks(self, nodes: list) -> int:
        points = [
            PointStruct(
                id=self._build_point_id(
                    node.metadata["document_version_id"],
                    node.metadata["chunk_index"],
                ),
                vector=node.embedding,
                payload={**node.metadata, "text": node.get_content()},
            )
            for node in nodes
        ]

        try:
            await self._qdrant_aclient.upsert(
                collection_name=settings.qdrant.collection_name,
                points=points,
                wait=True,
            )
        except Exception as err:
            self.logger.error(f"Error upserting {len(points)} chunks")
            self.logger.exception(err)
            raise

        self.logger.info(f"Upserted {len(points)} chunks into {settings.qdrant.collection_name}")
        return len(points)

    async def activate_chunks(self, document_version_id: int) -> bool:
        self.logger.info(
            f"Activating chunks for document_version_id={document_version_id} in {settings.qdrant.collection_name}"
        )
        try:
            await self._qdrant_aclient.set_payload(
                collection_name=settings.qdrant.collection_name,
                payload={"index_state": ChunkIndexState.ACTIVE.value},
                points=Filter(
                    must=[FieldCondition(key="document_version_id", match=MatchValue(value=document_version_id))]
                ),
                wait=True
            )
            return True
        except Exception as err:
            self.logger.error(f"Error activating chunks for document_version_id={document_version_id} in {settings.qdrant.collection_name}")
            self.logger.exception(err)
            raise

    async def delete_points(self, key: str, value: int) -> bool:
        self.logger.info(f"Deleting points where {key}={value} from {settings.qdrant.collection_name}")
        try:
            await self._qdrant_aclient.delete(
                collection_name=settings.qdrant.collection_name,
                points_selector=FilterSelector(
                    filter=Filter(must=[FieldCondition(key=key, match=MatchValue(value=value))])
                ),
                wait=True
            )
            return True
        except Exception as err:
            self.logger.error(f"Error deleting points where {key}={value} from {settings.qdrant.collection_name}")
            self.logger.exception(err)
            raise

    async def close(self):
        try:
            await self._qdrant_aclient.close()
            self._qdrant_client.close()
        except Exception as e:
            self.logger.error("Error closing Qdrant clients")
            self.logger.exception(e)
            raise

    async def _collection_exists(self, collection_name: str) -> bool:
        return await self._qdrant_aclient.collection_exists(collection_name)

    async def _create_collection(self, collection: CollectionCreateQdrant) -> dict:
        if await self._collection_exists(collection.name):
            raise ValueError(f"Collection {collection.name} already exists")

        vectors_config = VectorParams(
            size=collection.size,
            distance=Distance(collection.distance.value)
        )

        hnsw_config = None
        if collection.hnsw_config:
            hnsw_config = HnswConfigDiff(
                m=collection.hnsw_config.m,
                ef_construct=collection.hnsw_config.ef_construct
            )

        await self._qdrant_aclient.create_collection(
            collection_name=collection.name,
            vectors_config=vectors_config,
            shard_number=collection.shard_number,
            replication_factor=collection.replication_factor,
            on_disk_payload=collection.on_disk_payload,
            hnsw_config=hnsw_config
        )

        return True

    async def _create_indexes(self, collection_name: str) -> None:
        self.logger.info(f"Creating indexes in {collection_name}")
        for field in QDRANT_INDEXES_PAYLOAD_FIELDS:
            await self._qdrant_aclient.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.INTEGER,
            )

    def _build_point_id(self, document_version_id: int, chunk_index: int) -> str:
        return str(uuid.uuid5(QDRANT_NAMESPACE, f"{document_version_id}:{chunk_index}"))