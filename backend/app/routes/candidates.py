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
    session = SessionService.get_session(req.session_id, default_query=req.query)
    effective_query = req.query or (session.original_query if session and session.original_query else "photo memory")
    if not session:
        session = SessionService.create_session(query=effective_query)

    banner_msg = None

    # Case A: User removed a constraint (Undo / Remove specific clue)
    if req.remove_constraint:
        remaining_constraints = SessionService.remove_constraint(
            session_id=session.session_id,
            dimension=req.remove_constraint.dimension,
            value=req.remove_constraint.value,
        )
        session = SessionService.get_session(session.session_id, default_query=effective_query)

        clues_obj = ClueData(**json.loads(session.clues)) if session.clues else None
        candidates = retrieval_service.get_initial_candidates(
            clues=clues_obj,
            query=effective_query,
            limit=settings.MAX_CANDIDATES,
        )

        for c in remaining_constraints:
            candidates, _ = ranking_service.apply_constraint(
                candidates=candidates,
                dimension=c.get("dimension", "visual"),
                value=c.get("value", ""),
                original_query=effective_query,
            )

        new_ids = [c.photo_id for c in candidates]
        banner_msg = f"Removed filter '{req.remove_constraint.value}'. Restored {len(candidates)} candidates."
        SessionService.update_candidates(session.session_id, new_ids, banner_message=banner_msg)

        answered_dims = [c.get("dimension") for c in remaining_constraints if "dimension" in c]
        answered_vals = [c.get("value") for c in remaining_constraints if "value" in c]

        refine_resp = await refinement_engine.get_next_question(
            candidates=candidates,
            answered_dimensions=answered_dims,
            session_id=session.session_id,
            current_turn=len(remaining_constraints) + 1,
            original_query=session.original_query,
            last_constraint_val="",
            answered_values=answered_vals,
        )

        return CandidatesResponse(
            session_id=session.session_id,
            candidates=candidates,
            total=len(candidates),
            turn=len(remaining_constraints),
            banner_message=banner_msg,
            refinement=refine_resp,
            active_constraints=remaining_constraints,
        )

    # Case B: User supplied a refinement constraint (Refinement Loop Turn)
    if req.constraint:
        # 1. Fetch current candidates from session
        existing_candidate_ids = json.loads(session.candidate_ids) if session.candidate_ids else []
        current_candidates = retrieval_service.get_candidates_by_ids(existing_candidate_ids)
        if not current_candidates:
            current_candidates = retrieval_service.get_initial_candidates(
                clues=None,
                query=effective_query,
                limit=settings.MAX_CANDIDATES,
            )

        # 2. Record constraint and increment turn
        turn = SessionService.add_constraint(
            session_id=session.session_id,
            dimension=req.constraint.dimension,
            value=req.constraint.value,
        )

        # Reload session from DB to have updated constraints and turn_count
        session = SessionService.get_session(session.session_id, default_query=effective_query)

        # 3. Apply constraint filter & re-rank
        updated_candidates, banner_msg = ranking_service.apply_constraint(
            candidates=current_candidates,
            dimension=req.constraint.dimension,
            value=req.constraint.value,
            original_query=effective_query,
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
            active_constraints=constraints,
        )

    # Case C: Initial candidate retrieval
    clues_obj = None
    if session.clues:
        clues_dict = json.loads(session.clues)
        clues_obj = ClueData(**clues_dict)

    query_lower = effective_query.lower()
    # Adapt limit to cluster context (e.g. 38 for coorg cafe)
    limit = 38 if "coorg" in query_lower and ("cafe" in query_lower or "café" in query_lower) else settings.MAX_CANDIDATES

    candidates = retrieval_service.get_initial_candidates(
        clues=clues_obj,
        query=effective_query,
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
        original_query=effective_query,
    )

    banner = refine_resp.summary_message or f"I found {len(candidates)} possible photos from your library."
    constraints = json.loads(session.constraints) if session.constraints else []

    return CandidatesResponse(
        session_id=session.session_id,
        candidates=candidates,
        total=len(candidates),
        turn=session.turn_count,
        banner_message=banner,
        refinement=refine_resp,
        active_constraints=constraints,
    )
