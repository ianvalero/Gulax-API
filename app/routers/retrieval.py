from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
import app.dependencies.services as dependencies_services
import app.dependencies.auth as dependencies_auth
from app.services.retrieval_service import RetrievalService
from app.schemas.retrieval import RetrievalResult, RetrievalQuery
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