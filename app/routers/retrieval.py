from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.database import get_session
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth
from app.services.retrieval_service import RetrievalService
from app.services import TenantService
from app.services import KnowledgeSpaceService
from app.schemas.retrieval import RetrievalQuery, RetrievalResult
from app.schemas.tenant import TenantRetrievableQueryParams, TenantRetrievableRead
from app.schemas.knowledge_space import KnowledgeSpaceRetrievableQueryParams, KnowledgeSpaceRetrievableRead
from app.schemas.pagination import Pagination, PaginatedResponse
from app.schemas.user import User


router = APIRouter(prefix="/api/retrieval", tags=["Retrieval Data"])

@router.post(
    "/search",
    response_model=list[RetrievalResult],
    summary="Search documents context",
    description="Returns the most relevant chunks the user is authorized to access, "
                "ordered by relevance (best match first).",
    responses={
        403: {"description": "User does not have retrieval access to the requested knowledge spaces"},
    },
)
async def search(
    payload: RetrievalQuery,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    retrieval_service: RetrievalService = Depends(dependencies_services.get_retrieval_service)
):
    return await retrieval_service.search(session=session, user=user, retrieval=payload)


@router.get(
    "/tenants",
    response_model=PaginatedResponse[TenantRetrievableRead],
    summary="Get all retrievable tenants",
    description="Returns the tenants the user is authorized to retrieval data.",
)
async def get_retrievable_tenants(
    params: Annotated[TenantRetrievableQueryParams, Query()],
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    items, total = await tenant_service.get_retrievable_tenants(session=session, user=user, params=params)
    pagination = Pagination(
        offset=params.offset,
        limit=params.limit,
        total=total,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )

    return PaginatedResponse[TenantRetrievableRead](
        items=items,
        pagination=pagination,
    )


@router.get(
    "/knowledge-spaces",
    response_model=PaginatedResponse[KnowledgeSpaceRetrievableRead],
    summary="Get all retrievable knowledge spaces",
    description="Returns the knowledge spaces the user is authorized to retrieval data.",
)
async def get_retrievable_knowledge_spaces(
    params: Annotated[KnowledgeSpaceRetrievableQueryParams, Query()],
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    items, total = await knowledge_space_service.get_retrievable_knowledge_spaces(session=session, user=user, params=params)
    pagination = Pagination(
        offset=params.offset,
        limit=params.limit,
        total=total,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )

    return PaginatedResponse[KnowledgeSpaceRetrievableRead](
        items=items,
        pagination=pagination
    )