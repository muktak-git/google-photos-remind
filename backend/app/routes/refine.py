import json
from fastapi import APIRouter, HTTPException
from app.models.schemas import RefineRequest, RefineResponse
from app.services.session import SessionService
from app.services.retrieval import retrieval_service
from app.services.refinement import refinement_engine

router = APIRouter(prefix="/api", tags=["Refinement"])


@router.post("/refine", response_model=RefineResponse)
async def get_refinement_question(req: RefineRequest):
    """Screen 4: Generate next entropy-driven question based on current candidate pool."""
    session = SessionService.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Fetch current candidate photos
    candidate_ids = json.loads(session.candidate_ids) if session.candidate_ids else []
    candidates = retrieval_service.get_candidates_by_ids(candidate_ids)

    # 2. Extract answered dimensions and values
    constraints = json.loads(session.constraints) if session.constraints else []
    answered_dimensions = [c.get("dimension") for c in constraints if "dimension" in c]
    answered_values = [c.get("value") for c in constraints if "value" in c]
    last_val = constraints[-1].get("value", "") if constraints else ""
    is_not_sure = any(
        term in last_val.lower()
        for term in ["not sure", "don't know", "dont know", "not remember", "no idea", "unsure"]
    )
    if is_not_sure:
        for d in ["time_or_date", "time_of_day", "visual", "scene_type"]:
            if d not in answered_dimensions:
                answered_dimensions.append(d)

    # 3. Compute highest entropy question
    refine_resp = await refinement_engine.get_next_question(
        candidates=candidates,
        answered_dimensions=answered_dimensions,
        session_id=session.session_id,
        current_turn=session.turn_count + 1,
        original_query=session.original_query,
        last_constraint_val=last_val,
        answered_values=answered_values,
    )

    # 4. Log event
    SessionService.log_event(
        session_id=session.session_id,
        event_type="refinement_question_presented",
        payload={
            "dimension": refine_resp.dimension,
            "question": refine_resp.question,
            "options": refine_resp.options,
            "turn": refine_resp.turn,
        },
    )

    return refine_resp
