from typing import Any
from datetime import datetime

from sqlmodel import SQLModel
from pydantic import ConfigDict, Field

from app.schemas.pagination import PaginationParams
from app.enums import IngestionRunStatus, IngestionRunSortField, SortDirection


class IngestionRunQueryParams(PaginationParams):
    status: IngestionRunStatus | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None

    sort_by: IngestionRunSortField = IngestionRunSortField.ID
    sort_order: SortDirection = SortDirection.ASC


class CeleryTaskRead(SQLModel):
    task_id: str
    status: str
    result: Any | None = None


class IngestionRunRead(SQLModel):
    id: int
    document_version_id: int
    attempt_number: int
    status: IngestionRunStatus
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)