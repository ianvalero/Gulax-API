from fastapi import APIRouter, Depends, status, Query
from typing import Annotated
from sqlmodel import Session

from app.database import get_session
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth
from app.services import DocumentService
import app.schemas.document as DocumentSchema
from app.schemas.pagination import Pagination, PaginatedResponse
from app.schemas.user import User


router = APIRouter(prefix="/api/documents", tags=["Documents"])
create_document_router = APIRouter(prefix="/api/collections", tags=["Documents"])

@router.get(
    "",
    response_model=PaginatedResponse[DocumentSchema.DocumentRead],
    summary="Get all documents")
async def get_documents(
    params: Annotated[DocumentSchema.DocumentQueryParams, Query()],
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    document_service: DocumentService = Depends(dependencies_services.get_document_service)
):
    items, total = await document_service.get_documents(session=session, user=user, params=params,)
    pagination = Pagination(
        offset=params.offset,
        limit=params.limit,
        total=total,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )

    return PaginatedResponse[DocumentSchema.DocumentRead](
        items=items,
        pagination=pagination
    )

@router.get(
"/{document_id}",
    response_model=DocumentSchema.DocumentRead,
    summary="Get document by id")
async def get_document(
    document_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    document_service: DocumentService = Depends(dependencies_services.get_document_service)
):
    return await document_service.get_document(session=session, user=user, document_id=document_id)

@create_document_router.post(
"/{collection_id}/documents",
    response_model=DocumentSchema.DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create new document")
async def upload_document(
    collection_id: int,
    payload: DocumentSchema.DocumentCreate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    document_service: DocumentService = Depends(dependencies_services.get_document_service)
):
    return await document_service.add_document(
        session=session,
        user=user,
        collection_id=collection_id,
        document=payload
    )

@router.patch(
"/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Update document")
async def update_document(
    document_id: int,
    payload: DocumentSchema.DocumentUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    document_service: DocumentService = Depends(dependencies_services.get_document_service)
):
    return await document_service.update_document(session=session, user=user, document_id=document_id, data=payload)


@router.delete(
"/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document")
async def delete_document(
    document_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(dependencies_auth.get_current_user),
    document_service: DocumentService = Depends(dependencies_services.get_document_service)
):
    return await document_service.delete_document(session=session, user=user, document_id=document_id)