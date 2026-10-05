from fastapi import APIRouter, HTTPException
from app.models.schemas import ConfirmRequest, ConfirmResponse, SessionMetrics
from app.services.session import SessionService

router = APIRouter(prefix="/api", tags=["Confirmation"])


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_recognition(req: ConfirmRequest):
    """Screen 5: Record final photo recognition ('Yes, that's it') or rejection ('No, keep looking')."""
    session = SessionService.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    metrics_dict = SessionService.complete_session(
        session_id=session.session_id,
        photo_id=req.photo_id,
        confirmed=req.confirmed,
    )

    metrics = SessionMetrics(**metrics_dict)

    if req.confirmed:
        msg = f"Success! Photo {req.photo_id} confirmed in {metrics.total_turns} turns ({metrics.duration_seconds}s)."
        status = "completed"
    else:
        msg = "Refinement continuing. Keep exploring clues."
        status = "active"

    return ConfirmResponse(
        session_id=session.session_id,
        success=req.confirmed,
        status=status,
        metrics=metrics,
        message=msg,
    )
