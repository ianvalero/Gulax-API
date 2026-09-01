from __future__ import annotations
from typing import TYPE_CHECKING
import logging

from sqlmodel import Session

from app.schemas.user import User
from app.infrastructure.qdrant_gateway import QdrantGateway
from app.services.tenant_service import TenantService
from app.services.knowledge_space_service import KnowledgeSpaceService
from app.schemas.retrieval import RetrievalResult, RetrievalQuery
from app.exceptions import KnowledgeSpacePermissionError, QdrantOperationError, EmbeddingServiceError

if TYPE_CHECKING:
    from llama_index.core.base.embeddings.base import BaseEmbedding

class RetrievalService:
    def __init__(
        self,
        tenant_service: TenantService,
        knowledge_space_service: KnowledgeSpaceService,
        qdrant_gateway: QdrantGateway,
        embedding_model: BaseEmbedding
    ):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.tenant_service = tenant_service
        self.knowledge_space_service = knowledge_space_service
        self._qdrant_gateway = qdrant_gateway
        self._embedding_model = embedding_model
        self.logger.info("Retrieval Service initialized")

    async def search(self, session: Session, user: User, retrieval: RetrievalQuery) -> list[RetrievalResult]:
        tenant_ids = await self.tenant_service.get_retrievable_tenant_ids(session=session, user=user)
        if not tenant_ids:
            return []

        if retrieval.knowledge_space_ids:
            allowed_knowledge_space_ids = await self.knowledge_space_service.get_retrievable_knowledge_space_ids(
                session=session,
                user=user
            )

            if not set(retrieval.knowledge_space_ids).issubset(set(allowed_knowledge_space_ids)):
                raise KnowledgeSpacePermissionError("User does not have permission to access these knowledge spaces")
        try:
            embedding = await self._embedding_model.aget_query_embedding(retrieval.query)
        except Exception as err:
            self.logger.exception("Error generating query embedding")
            raise EmbeddingServiceError("Embedding service unavailable") from err

        try:
            context_chunks =  await self._qdrant_gateway.search_chunks(
                query_embedding=embedding,
                tenant_ids=tenant_ids,
                knowledge_space_ids=retrieval.knowledge_space_ids,
                limit=retrieval.limit
            )
        except Exception as err:
            self.logger.error(f"Error searching chunks in Qdrant")
            self.logger.exception(err)
            raise QdrantOperationError("Error searching chunks in Qdrant")

        return [self.__prepare_result(chunk) for chunk in context_chunks]

    def __prepare_result(self, chunk: dict) -> RetrievalResult:
        payload = chunk.get("payload", {})
        return RetrievalResult(
            content=payload.get("text", ""),
            score=chunk["score"],
            tenant_id=payload["tenant_id"],
            knowledge_space_id=payload["knowledge_space_id"],
            document_id=payload["document_id"],
            document_version_id=payload["document_version_id"],
            filename=payload.get("filename"),
            page=payload.get("page"),
            chunk_index=payload["chunk_index"],
        )