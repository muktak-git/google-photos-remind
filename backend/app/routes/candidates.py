import json
from fastapi import APIRouter, HTTPException
from app.config import settings
from app.models.schemas import CandidatesRequest, CandidatesResponse, ClueData
from app.services.session import SessionService
from app.services.retrieval import retrieval_service
from app.services.ranking import ranking_service
from app.services.refinement import refinement_engine

router = APIRouter(prefix="/api", tags=["Candidates"])


@router.post("/candidates", response_model=CandidatesResponse)
async def get_or_refine_candidates(req: CandidatesRequest):
    """Screen 3: Retrieve initial candidate photos or re-rank existing candidates after refinement."""
    session = SessionService.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    banner_msg = None

    # Case A: User supplied a refinement constraint (Refinement Loop Turn)
    if req.constraint:
        # 1. Fetch current candidates from session
        existing_candidate_ids = json.loads(session.candidate_ids) if session.candidate_ids else []
        current_candidates = retrieval_service.get_candidates_by_ids(existing_candidate_ids)

        # 2. Record constraint and increment turn
        turn = SessionService.add_constraint(
            session_id=session.session_id,
            dimension=req.constraint.dimension,
            value=req.constraint.value,
        )

        # Reload session from DB to have updated constraints and turn_count
        session = SessionService.get_session(session.session_id)

        # 3. Apply constraint filter & re-rank
        updated_candidates, banner_msg = ranking_service.apply_constraint(
            candidates=current_candidates,
            dimension=req.constraint.dimension,
            value=req.constraint.value,
        )

        # 4. Save updated candidate IDs to session
        new_ids = [c.photo_id for c in updated_candidates]
        SessionService.update_candidates(session.session_id, new_ids, banner_message=banner_msg)

        # 5. Build next refinement questions
        constraints = json.loads(session.constraints) if session.constraints else []
        answered_dimensions = [c.get("dimension") for c in constraints if "dimension" in c]
        answered_values = [c.get("value") for c in constraints if "value" in c]

        is_not_sure = any(
            phrase in req.constraint.value.lower()
            for phrase in ["not sure", "don't know", "dont know", "not remember", "no idea", "unsure"]
        )
        if is_not_sure:
            for d in ["time_or_date", "time_of_day", "visual", "scene_type"]:
                if d not in answered_dimensions:
                    answered_dimensions.append(d)

        val_lower = req.constraint.value.strip().lower()
        is_rejection = val_lower in ("no", "n", "nope")

        refine_resp = await refinement_engine.get_next_question(
            candidates=updated_candidates,
            answered_dimensions=answered_dimensions,
            session_id=session.session_id,
            current_turn=turn + 1,
            original_query=session.original_query,
            last_constraint_val=req.constraint.value,
            answered_values=answered_values,
        )

        final_banner = refine_resp.summary_message if (is_not_sure or is_rejection) else (banner_msg or refine_resp.summary_message)

        return CandidatesResponse(
            session_id=session.session_id,
            candidates=updated_candidates,
            total=len(updated_candidates),
            turn=turn,
            banner_message=final_banner,
            refinement=refine_resp,
        )

    # Case B: Initial candidate retrieval
    clues_obj = None
    if session.clues:
        clues_dict = json.loads(session.clues)
        clues_obj = ClueData(**clues_dict)

    query_lower = (session.original_query or "").lower()
    # Adapt limit to cluster context (e.g. 38 for coorg cafe)
    limit = 38 if "coorg" in query_lower and ("cafe" in query_lower or "café" in query_lower) else settings.MAX_CANDIDATES

    candidates = retrieval_service.get_initial_candidates(
        clues=clues_obj,
        query=session.original_query,
        limit=limit,
    )

    candidate_ids = [c.photo_id for c in candidates]
    SessionService.update_candidates(session.session_id, candidate_ids)

    # Build initial refinement questions
    refine_resp = await refinement_engine.get_next_question(
        candidates=candidates,
        answered_dimensions=[],
        session_id=session.session_id,
        current_turn=session.turn_count + 1,
        original_query=session.original_query,
    )

    banner = refine_resp.summary_message or f"I found {len(candidates)} possible photos from your library."

    return CandidatesResponse(
        session_id=session.session_id,
        candidates=candidates,
        total=len(candidates),
        turn=session.turn_count,
        banner_message=banner,
        refinement=refine_resp,
    )
