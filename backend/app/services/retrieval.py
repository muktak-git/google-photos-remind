import json
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models.database import PhotoRecord
from app.models.schemas import CandidatePhoto, ClueData
from app.providers.database import SessionLocal
from app.providers.vectorstore import vector_store
from app.providers.embedding import EmbeddingProvider

logger = logging.getLogger(__name__)


class RetrievalService:
    """Handles hybrid vector similarity and metadata candidate retrieval."""

    def __init__(self):
        self.embedding_provider = EmbeddingProvider()

    def get_initial_candidates(
        self,
        clues: Optional[ClueData] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> List[CandidatePhoto]:
        """Retrieve top-K candidate photos based on confident clues or query."""
        search_text = self._synthesize_search_text(clues, query)

        # 1. Generate query embedding
        query_vector = self.embedding_provider.embed_text(search_text)

        # 2. Query ChromaDB for top candidates
        results = vector_store.query(query_embedding=query_vector, n_results=limit)

        retrieved_ids = results["ids"][0] if results and "ids" in results else []
        distances = results.get("distances", [[]])[0] if results else []

        if not retrieved_ids:
            logger.warning(f"No candidates found for search text: '{search_text}'. Attempting relaxed query.")
            # Fallback to broader query if needed
            return []

        # 3. Join with SQLite metadata records
        candidates = self._fetch_candidates_from_db(retrieved_ids, distances)
        return candidates

    def get_candidates_by_ids(self, photo_ids: List[str]) -> List[CandidatePhoto]:
        """Fetch full candidate records for given list of IDs preserving order."""
        if not photo_ids:
            return []
        db: Session = SessionLocal()
        try:
            records = db.query(PhotoRecord).filter(PhotoRecord.photo_id.in_(photo_ids)).all()
            id_to_record = {r.photo_id: r for r in records}

            ordered_candidates = []
            for pid in photo_ids:
                rec = id_to_record.get(pid)
                if rec:
                    ordered_candidates.append(self._record_to_candidate(rec, score=1.0))
            return ordered_candidates
        finally:
            db.close()

    def _synthesize_search_text(self, clues: Optional[ClueData], fallback_query: Optional[str]) -> str:
        """Compose a unified search representation emphasizing confident clues."""
        if not clues:
            return fallback_query or "photo"

        parts = []
        if clues.location and clues.confidence.location >= 0.5:
            parts.append(f"in {clues.location}")
        if clues.scene and clues.confidence.scene >= 0.5:
            parts.append(f"{clues.scene}")
        if clues.event and clues.confidence.event >= 0.5:
            parts.append(f"{clues.event}")
        if clues.people and clues.confidence.people >= 0.5:
            parts.append(f"with {', '.join(clues.people)}")
        if clues.time and clues.confidence.time >= 0.5:
            parts.append(f"at {clues.time}")
        if clues.visual_details:
            parts.append(f"{clues.visual_details}")

        if not parts and fallback_query:
            return fallback_query
        return " ".join(parts) if parts else (fallback_query or "photo")

    def _fetch_candidates_from_db(self, photo_ids: List[str], distances: List[float]) -> List[CandidatePhoto]:
        """Retrieve full database photo records and calculate similarity scores."""
        db: Session = SessionLocal()
        try:
            records = db.query(PhotoRecord).filter(PhotoRecord.photo_id.in_(photo_ids)).all()
            record_map = {r.photo_id: r for r in records}

            candidates: List[CandidatePhoto] = []
            for idx, pid in enumerate(photo_ids):
                rec = record_map.get(pid)
                if rec:
                    # Cosine distance to similarity: similarity = 1 - distance
                    dist = distances[idx] if idx < len(distances) else 0.5
                    score = max(0.0, min(1.0, 1.0 - dist))
                    candidates.append(self._record_to_candidate(rec, score))

            return candidates
        finally:
            db.close()

    def _record_to_candidate(self, rec: PhotoRecord, score: float) -> CandidatePhoto:
        """Convert a PhotoRecord into a CandidatePhoto schema object."""
        return CandidatePhoto(
            photo_id=rec.photo_id,
            file_path=rec.file_path,
            thumbnail_url=f"/photos/thumbnails/{rec.photo_id}.jpg",
            full_url=f"/{rec.file_path.replace('\\', '/')}",
            score=round(score, 3),
            location=rec.location,
            date=rec.date_taken,
            setting=rec.setting,
            time_of_day=rec.time_of_day,
            visual_description=rec.visual_description,
            scene=json.loads(rec.scene) if rec.scene else [],
            objects=json.loads(rec.objects) if rec.objects else [],
            people=json.loads(rec.people) if rec.people else [],
        )


retrieval_service = RetrievalService()
