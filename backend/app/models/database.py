import json
from datetime import datetime
from typing import Any, List, Optional
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class PhotoRecord(Base):
    """SQLAlchemy model representing an indexed photo with its multimodal metadata."""
    __tablename__ = "photos"

    photo_id = Column(String(64), primary_key=True, index=True)
    file_path = Column(String(512), nullable=False)
    thumbnail_path = Column(String(512), nullable=True)
    date_taken = Column(String(32), nullable=True, index=True)
    location = Column(String(128), nullable=True, index=True)
    people = Column(Text, nullable=True)           # JSON array string
    event = Column(String(128), nullable=True, index=True)
    scene = Column(Text, nullable=True)            # JSON array string
    objects = Column(Text, nullable=True)          # JSON array string
    visual_description = Column(Text, nullable=False)
    ocr_text = Column(Text, nullable=True)
    setting = Column(String(64), nullable=True, index=True)      # indoor / outdoor / mixed
    time_of_day = Column(String(64), nullable=True, index=True)  # day / evening / night
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert record to dictionary with parsed JSON fields."""
        return {
            "photo_id": self.photo_id,
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "date_taken": self.date_taken,
            "location": self.location,
            "people": json.loads(self.people) if self.people else [],
            "event": self.event,
            "scene": json.loads(self.scene) if self.scene else [],
            "objects": json.loads(self.objects) if self.objects else [],
            "visual_description": self.visual_description,
            "ocr_text": self.ocr_text or "",
            "setting": self.setting,
            "time_of_day": self.time_of_day,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SessionRecord(Base):
    """SQLAlchemy model representing a user search & memory reconstruction session."""
    __tablename__ = "sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    original_query = Column(Text, nullable=False)
    clues = Column(Text, nullable=True)            # JSON object
    constraints = Column(Text, nullable=True)      # JSON array of applied refinements
    candidate_ids = Column(Text, nullable=True)    # JSON array of current candidate IDs
    turn_count = Column(Integer, default=0)
    status = Column(String(32), default="active", index=True)  # active, completed, abandoned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("SessionEventRecord", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "original_query": self.original_query,
            "clues": json.loads(self.clues) if self.clues else None,
            "constraints": json.loads(self.constraints) if self.constraints else [],
            "candidate_ids": json.loads(self.candidate_ids) if self.candidate_ids else [],
            "turn_count": self.turn_count,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SessionEventRecord(Base):
    """Audit event log tracking user actions and metric points."""
    __tablename__ = "session_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("sessions.session_id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # search, understand, retrieve, refine, confirm, abandon
    payload = Column(Text, nullable=True)                        # JSON data
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("SessionRecord", back_populates="events")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "payload": json.loads(self.payload) if self.payload else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
