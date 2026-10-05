import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import SessionRecord, SessionEventRecord
from app.providers.database import SessionLocal


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionService:
    """Manages session lifecycle, constraints, candidate history, and event audit logs."""

    @staticmethod
    def create_session(query: str) -> SessionRecord:
        """Create and persist a new search session."""
        db: Session = SessionLocal()
        try:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"
            record = SessionRecord(
                session_id=session_id,
                original_query=query,
                clues=None,
                constraints=json.dumps([]),
                candidate_ids=json.dumps([]),
                turn_count=0,
                status="active",
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            db.add(record)
            db.commit()

            # Log initial event
            SessionService.log_event(
                session_id=session_id,
                event_type="search_created",
                payload={"query": query},
                db=db,
            )
            return record
        finally:
            db.close()

    @staticmethod
    def get_session(session_id: str) -> Optional[SessionRecord]:
        """Fetch session by ID."""
        db: Session = SessionLocal()
        try:
            return db.query(SessionRecord).filter_by(session_id=session_id).first()
        finally:
            db.close()

    @staticmethod
    def update_clues(session_id: str, clues_data: Dict[str, Any]) -> None:
        """Save extracted clues to session."""
        db: Session = SessionLocal()
        try:
            session = db.query(SessionRecord).filter_by(session_id=session_id).first()
            if session:
                session.clues = json.dumps(clues_data)
                session.updated_at = utcnow()
                db.commit()
                SessionService.log_event(
                    session_id=session_id,
                    event_type="clues_extracted",
                    payload=clues_data,
                    db=db,
                )
        finally:
            db.close()

    @staticmethod
    def update_candidates(session_id: str, candidate_ids: List[str], banner_message: Optional[str] = None) -> None:
        """Update candidate list and increment turn count if constrained."""
        db: Session = SessionLocal()
        try:
            session = db.query(SessionRecord).filter_by(session_id=session_id).first()
            if session:
                session.candidate_ids = json.dumps(candidate_ids)
                session.updated_at = utcnow()
                db.commit()
                SessionService.log_event(
                    session_id=session_id,
                    event_type="candidates_updated",
                    payload={
                        "candidate_count": len(candidate_ids),
                        "candidate_ids": candidate_ids,
                        "banner": banner_message,
                    },
                    db=db,
                )
        finally:
            db.close()

    @staticmethod
    def add_constraint(session_id: str, dimension: str, value: str) -> int:
        """Add a user refinement answer constraint to the session and return new turn count."""
        db: Session = SessionLocal()
        try:
            session = db.query(SessionRecord).filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"Session {session_id} not found")

            existing_constraints = json.loads(session.constraints) if session.constraints else []
            existing_constraints.append({
                "turn": session.turn_count + 1,
                "dimension": dimension,
                "value": value,
                "timestamp": utcnow().isoformat(),
            })
            session.constraints = json.dumps(existing_constraints)
            session.turn_count += 1
            session.updated_at = utcnow()
            db.commit()

            SessionService.log_event(
                session_id=session_id,
                event_type="constraint_applied",
                payload={"dimension": dimension, "value": value, "turn": session.turn_count},
                db=db,
            )
            return session.turn_count
        finally:
            db.close()

    @staticmethod
    def log_event(
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> None:
        """Record an event into the audit log."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        try:
            event = SessionEventRecord(
                session_id=session_id,
                event_type=event_type,
                payload=json.dumps(payload),
                created_at=utcnow(),
            )
            db.add(event)
            db.commit()
        finally:
            if close_db:
                db.close()

    @staticmethod
    def complete_session(session_id: str, photo_id: Optional[str], confirmed: bool) -> Dict[str, Any]:
        """Mark session completed or continue search and calculate duration/turns."""
        db: Session = SessionLocal()
        try:
            session = db.query(SessionRecord).filter_by(session_id=session_id).first()
            if not session:
                raise ValueError(f"Session {session_id} not found")

            now = utcnow()
            # SQLite might return naive or aware datetime depending on driver
            created = session.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            duration = (now - created).total_seconds()
            candidates = json.loads(session.candidate_ids) if session.candidate_ids else []

            if confirmed:
                session.status = "completed"
            else:
                session.status = "active"

            session.updated_at = now
            db.commit()

            SessionService.log_event(
                session_id=session_id,
                event_type="confirm_photo" if confirmed else "rejected_photo",
                payload={
                    "photo_id": photo_id,
                    "confirmed": confirmed,
                    "duration_seconds": duration,
                    "total_turns": session.turn_count,
                },
                db=db,
            )

            return {
                "total_turns": session.turn_count,
                "photos_viewed": len(candidates),
                "duration_seconds": round(duration, 2),
                "confirmed": confirmed,
            }
        finally:
            db.close()
