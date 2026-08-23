from fastapi import APIRouter, Depends, status, Query
from typing import Annotated
from sqlmodel import Session

from app.database import get_session
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth
from app.services import KnowledgeSpaceService
import app.schemas.knowledge_space as KnowledgeSpaceSchema
from app.schemas.pagination import Pagination, PaginatedResponse
from app.schemas.user import User


router = APIRouter(prefix="/api/knowledge-spaces", tags=["Knowledge Spaces"])
create_knowledge_space_router = APIRouter(prefix="/api/tenants", tags=["Knowledge Spaces"])

@router.get(
    "",
    response_model=PaginatedResponse[KnowledgeSpaceSchema.KnowledgeSpaceReadDetail],
    summary="Get all knowledge spaces")
async def get_knowledge_spaces(
    params: Annotated[KnowledgeSpaceSchema.KnowledgeSpaceQueryParams, Query()],
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    items, total = await knowledge_space_service.get_knowledge_spaces(session=session, user=user, params=params)
    pagination = Pagination(
        offset=params.offset,
        limit=params.limit,
        total=total,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )

    return PaginatedResponse[KnowledgeSpaceSchema.KnowledgeSpaceReadDetail](
        items=items,
        pagination=pagination
    )

@router.get(
"/{knowledge_space_id}",
    response_model=KnowledgeSpaceSchema.KnowledgeSpaceReadDetail,
    summary="Get knowledge space by id")
async def get_knowledge_space(
    knowledge_space_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    return await knowledge_space_service.get_knowledge_space(
        session=session,
        user=user,
        knowledge_space_id=knowledge_space_id
    )


@create_knowledge_space_router.post(
"/{tenant_id}/knowledge-spaces",
    response_model=KnowledgeSpaceSchema.KnowledgeSpaceReadDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create knowledge space")
async def create_knowledge_space(
    tenant_id: int,
    body: KnowledgeSpaceSchema.KnowledgeSpaceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    return await knowledge_space_service.create_knowledge_space(
        session=session,
        user=user,
        tenant_id=tenant_id,
        knowledge_space=body
    )


@router.patch(
"/{knowledge_space_id}",
    response_model=KnowledgeSpaceSchema.KnowledgeSpaceReadDetail,
    status_code=status.HTTP_200_OK,
    summary="Update Knowledge Space")
async def update_knowledge_space(
    knowledge_space_id: int,
    body: KnowledgeSpaceSchema.KnowledgeSpaceUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    return await knowledge_space_service.update_knowledge_space(
        session=session,
        user=user,
        knowledge_space_id=knowledge_space_id,
        data=body
    )


@router.delete(
"/{knowledge_space_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Knowledge Space")
async def delete_knowledge_space(
    knowledge_space_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    knowledge_space_service: KnowledgeSpaceService = Depends(dependencies_services.get_knowledge_space_service)
):
    return await knowledge_space_service.delete_knowledge_space(
        session=session,
        user=user,
        knowledge_space_id=knowledge_space_id
    )