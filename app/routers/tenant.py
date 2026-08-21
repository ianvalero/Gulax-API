from typing import Annotated, cast

from fastapi import APIRouter, Depends, status, Query
from sqlmodel import Session

from app.database import get_session
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth
from app.services import TenantService
import app.schemas.tenant as TenantSchema
from app.schemas.pagination import Pagination, PaginatedResponse
from app.schemas.user import User


router = APIRouter(prefix="/api/tenants", tags=["Tenants"])

@router.get(
    "",
    response_model=PaginatedResponse[TenantSchema.TenantReadDetails] | PaginatedResponse[TenantSchema.TenantRead],
    summary="Get all tenants")
async def get_tenants(
    params: Annotated[TenantSchema.TenantQueryParams, Query()],
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    items, total = await tenant_service.get_tenants(session=session, user=user, params=params,)
    pagination = Pagination(
        offset=params.offset,
        limit=params.limit,
        total=total,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )

    if params.include_knowledge_spaces:
        return PaginatedResponse[TenantSchema.TenantReadDetails](
            items=cast(list[TenantSchema.TenantReadDetails], items),
            pagination=pagination,
        )

    return PaginatedResponse[TenantSchema.TenantRead](
        items=items,
        pagination=pagination,
    )


@router.get(
"/{tenant_id}",
    response_model=TenantSchema.TenantReadDetails,
    summary="Get tenant by id")
async def get_tenant(
    tenant_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    return await tenant_service.get_tenant(session=session, user=user, tenant_id=tenant_id)


@router.post(
"/",
    response_model=TenantSchema.TenantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(dependencies_auth.require_admin)],
    summary="Create tenant")
async def create_tenant(
    body: TenantSchema.TenantCreate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    return await tenant_service.create_tenant(session=session, user=user, new_tenant=body)


@router.patch(
    "/{tenant_id}",
    response_model=TenantSchema.TenantRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(dependencies_auth.require_admin)],
    summary="Update tenant")
async def update_tenant(
    tenant_id: int,
    body: TenantSchema.TenantUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    return await tenant_service.update_tenant(session=session, user=user, tenant_id=tenant_id, data=body)


@router.delete(
"/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(dependencies_auth.require_admin)],
    summary="Delete tenant")
async def delete_tenant(
    tenant_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    tenant_service: TenantService = Depends(dependencies_services.get_tenant_service)
):
    return await tenant_service.delete_tenant(session=session, user=user, tenant_id=tenant_id)