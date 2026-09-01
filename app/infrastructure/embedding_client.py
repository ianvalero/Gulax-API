from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding

from app.config.settings import settings


def build_embedding_model() -> BaseEmbedding:
    return OpenAIEmbedding(
        model_name=settings.embedding.model_name,
        api_base=settings.embedding.base_url,
        api_key=settings.embedding.api_key,
        embed_batch_size=settings.embedding.embed_batch_size,
    )