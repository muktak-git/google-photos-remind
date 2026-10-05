from fastapi import APIRouter, HTTPException
from app.models.schemas import UnderstandRequest, UnderstandResponse
from app.services.session import SessionService
from app.services.memory_parser import MemoryParserService

router = APIRouter(prefix="/api", tags=["Understanding"])


@router.post("/understand", response_model=UnderstandResponse)
async def understand_memory(req: UnderstandRequest):
    """Screen 2: Parse vague memory into machine-readable retrieval facets and display chips."""
    session = SessionService.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query_to_parse = req.query or session.original_query
    clues, chips, draft_summary = await MemoryParserService.parse_memory(query_to_parse)

    # Persist clues into session
    SessionService.update_clues(session_id=session.session_id, clues_data=clues.model_dump())

    return UnderstandResponse(
        session_id=session.session_id,
        clues=clues,
        chips=chips,
        draft_summary=draft_summary,
    )
