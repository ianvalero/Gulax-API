from pydantic import BaseModel, Field, ConfigDict


class RetrievalQuery(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    knowledge_space_ids: list[int] | None = Field(default=None)
    limit: int = Field(default=10, ge=1, le=100)

    model_config = ConfigDict(str_strip_whitespace=True)


class RetrievalResult(BaseModel):
    content: str
    score: float
    tenant_id: int
    knowledge_space_id: int
    document_id: int
    document_version_id: int
    chunk_index: int
    filename: str | None = None
    page: str | None = None

    model_config = ConfigDict(from_attributes=True)