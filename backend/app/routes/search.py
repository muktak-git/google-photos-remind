from fastapi import APIRouter, HTTPException
from app.models.schemas import SearchRequest, SearchResponse
from app.services.session import SessionService

router = APIRouter(prefix="/api", tags=["Search"])


@router.post("/search", response_model=SearchResponse, status_code=201)
async def create_search_session(req: SearchRequest):
    """Screen 1: User initiates memory search by typing a vague recollection."""
    if not req.query or len(req.query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query is too short or empty")

    session = SessionService.create_session(query=req.query.strip())
    return SearchResponse(
        session_id=session.session_id,
        query=session.original_query,
        created_at=session.created_at.isoformat(),
    )
