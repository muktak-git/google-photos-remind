from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# 1. Search (Screen 1)
# -------------------------------------------------------------
class SearchRequest(BaseModel):
    query: str = Field(..., description="User's vague memory search query", min_length=2)


class SearchResponse(BaseModel):
    session_id: str
    query: str
    created_at: str


# -------------------------------------------------------------
# 2. Understanding / Parsing (Screen 2)
# -------------------------------------------------------------
class ClueConfidence(BaseModel):
    location: float = 0.0
    event: float = 0.0
    scene: float = 0.0
    people: float = 0.0
    time: float = 0.0
    visual_details: float = 0.0


class ClueData(BaseModel):
    location: Optional[str] = None
    event: Optional[str] = None
    scene: Optional[str] = None
    people: Optional[List[str]] = None
    time: Optional[str] = None
    visual_details: Optional[str] = None
    confidence: ClueConfidence = Field(default_factory=ClueConfidence)


class ClueChip(BaseModel):
    facet: str
    value: str
    confidence: float
    display_text: str


class UnderstandRequest(BaseModel):
    session_id: str
    query: Optional[str] = None


class UnderstandResponse(BaseModel):
    session_id: str
    clues: ClueData
    chips: List[ClueChip]


# -------------------------------------------------------------
# 3. Candidates (Screen 3)
# -------------------------------------------------------------
class ConstraintInput(BaseModel):
    dimension: str
    value: str


class CandidatesRequest(BaseModel):
    session_id: str
    constraint: Optional[ConstraintInput] = None


class CandidatePhoto(BaseModel):
    photo_id: str
    file_path: str
    thumbnail_url: str
    full_url: str
    score: float
    location: Optional[str] = None
    date: Optional[str] = None
    setting: Optional[str] = None
    time_of_day: Optional[str] = None
    visual_description: str
    scene: List[str] = Field(default_factory=list)
    objects: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)


class RefineFacet(BaseModel):
    title: str
    dimension: str
    options: List[str]


class RefineResponse(BaseModel):
    session_id: str
    dimension: str
    question: str
    options: List[str]
    turn: int
    candidates_remaining: int
    summary_message: Optional[str] = None
    follow_up_prompt: Optional[str] = "Do you remember anything else?"
    facets: List[RefineFacet] = Field(default_factory=list)
    hint_keywords: List[str] = Field(default_factory=list)


class CandidatesResponse(BaseModel):
    session_id: str
    candidates: List[CandidatePhoto]
    total: int
    turn: int
    banner_message: Optional[str] = None
    refinement: Optional[RefineResponse] = None


# -------------------------------------------------------------
# 4. Refinement (Screen 4)
# -------------------------------------------------------------
class RefineRequest(BaseModel):
    session_id: str


# -------------------------------------------------------------
# 5. Confirmation / Recognition (Screen 5)
# -------------------------------------------------------------
class ConfirmRequest(BaseModel):
    session_id: str
    photo_id: Optional[str] = None
    confirmed: bool = True


class SessionMetrics(BaseModel):
    total_turns: int
    photos_viewed: int
    duration_seconds: float
    confirmed: bool


class ConfirmResponse(BaseModel):
    session_id: str
    success: bool
    status: str
    metrics: SessionMetrics
    message: str
