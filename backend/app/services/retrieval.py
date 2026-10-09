import re
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


SYNONYM_MAP = {
    'temple': ['temple', 'mandir', 'shrine', 'palace', 'monument', 'heritage', 'dome', 'arch', 'mysore', 'sandstone', 'pillar'],
    'mandir': ['temple', 'mandir', 'shrine', 'palace', 'monument', 'heritage'],
    'shrine': ['shrine', 'temple', 'mandir', 'heritage', 'palace'],
    'sun': ['sun', 'sunny', 'sunlight', 'sunlit', 'sunset', 'day', 'daytime', 'bright'],
    'sunny': ['sunny', 'sun', 'sunlight', 'sunlit', 'day', 'bright'],
    'kid': ['kid', 'kids', 'child', 'children', 'baby', 'toddler', 'boy', 'girl'],
    'kids': ['kid', 'kids', 'child', 'children', 'baby', 'toddler'],
    'child': ['child', 'children', 'kid', 'kids', 'baby', 'toddler'],
    'children': ['child', 'children', 'kid', 'kids', 'baby', 'toddler'],
    'baby': ['baby', 'toddler', 'infant', 'child', 'kid', 'kids'],
    'pool': ['pool', 'swimming pool', 'splash', 'water', 'float'],
    'water': ['water', 'pool', 'lake', 'splash', 'river'],
    'lake': ['lake', 'water', 'pond', 'water body'],
    'palace': ['palace', 'courtyard', 'arch', 'rajasthan', 'jaipur', 'udaipur', 'jodhpur', 'mysore', 'heritage'],
    'courtyard': ['courtyard', 'palace', 'arch', 'heritage', 'rajasthan'],
    'cafe': ['cafe', 'café', 'coffee', 'coorg', 'estate', 'plantation'],
    'coffee': ['coffee', 'cafe', 'coorg', 'estate', 'plantation'],
}

NEGATIVE_MAP = {
    'temple': ['clinic', 'medical', 'prescription', 'doctor'],
    'mandir': ['clinic', 'medical', 'prescription', 'doctor'],
    'shrine': ['clinic', 'medical', 'prescription', 'doctor'],
    'sun': ['clinic', 'medical', 'prescription'],
    'sunny': ['clinic', 'medical', 'prescription'],
    'kid': ['clinic', 'medical', 'prescription'],
    'kids': ['clinic', 'medical', 'prescription'],
    'child': ['clinic', 'medical', 'prescription'],
    'baby': ['clinic', 'medical', 'prescription'],
    'palace': ['clinic', 'medical', 'prescription'],
    'lake': ['clinic', 'medical', 'prescription'],
    'coffee': ['clinic', 'medical', 'prescription'],
    'cafe': ['clinic', 'medical', 'prescription'],
}


class RetrievalService:
    """Handles hybrid vector similarity and metadata candidate retrieval."""

    def __init__(self):
        self.embedding_provider = EmbeddingProvider()

    def retrieve_candidates(self, query: str, limit: int = 20) -> List[CandidatePhoto]:
        """Convenience method for direct keyword/query retrieval."""
        return self.get_initial_candidates(clues=None, query=query, limit=limit)

    def get_initial_candidates(
        self,
        clues: Optional[ClueData] = None,
        query: Optional[str] = None,
        limit: int = 20,
    ) -> List[CandidatePhoto]:
        """Retrieve top-K candidate photos using hybrid concept, keyword, and vector similarity."""
        search_text = self._synthesize_search_text(clues, query)

        # 1. Vector Search for broad candidate pool
        query_vector = self.embedding_provider.embed_text(search_text)
        results = vector_store.query(query_embedding=query_vector, n_results=min(120, max(limit * 3, 50)))

        retrieved_ids = results["ids"][0] if results and "ids" in results else []
        distances = results.get("distances", [[]])[0] if results else []
        vec_dist_map = {retrieved_ids[i]: distances[i] for i in range(len(retrieved_ids))}

        # 2. Hybrid Keyword & Semantic Re-ranking from SQLite
        db: Session = SessionLocal()
        try:
            records = db.query(PhotoRecord).all()
            q_words = re.findall(r"\b[a-zA-Z0-9]+\b", search_text.lower())

            expanded_terms = set(q_words)
            negative_terms = set()
            for w in q_words:
                if w in SYNONYM_MAP:
                    expanded_terms.update(SYNONYM_MAP[w])
                if w in NEGATIVE_MAP:
                    negative_terms.update(NEGATIVE_MAP[w])

            scored_records = []
            for rec in records:
                full_text = f"{rec.location} {rec.event} {rec.visual_description} {rec.setting} {rec.time_of_day}".lower()
                if rec.scene:
                    full_text += " " + " ".join(json.loads(rec.scene)).lower()
                if rec.objects:
                    full_text += " " + " ".join(json.loads(rec.objects)).lower()
                if rec.people:
                    full_text += " " + " ".join(json.loads(rec.people)).lower()

                # Base vector similarity
                dist = vec_dist_map.get(rec.photo_id, 0.95)
                sim_base = max(0.0, min(1.0, 1.0 - dist))

                # Penalty for negative terms (e.g. clinic for temple/sun/kid queries)
                if any(neg in full_text for neg in negative_terms):
                    sim_base -= 3.0

                # Keyword exact word match boost
                for w in q_words:
                    if len(w) >= 3:
                        if re.search(r"\b" + re.escape(w) + r"\b", full_text):
                            sim_base += 1.8
                        elif w in full_text:
                            sim_base += 0.9

                # Synonym / concept match boost
                for syn in expanded_terms:
                    if len(syn) >= 3 and syn not in q_words:
                        if re.search(r"\b" + re.escape(syn) + r"\b", full_text):
                            sim_base += 0.8
                        elif syn in full_text:
                            sim_base += 0.4

                scored_records.append((rec, sim_base))

            # Sort descending by hybrid score
            scored_records.sort(key=lambda x: x[1], reverse=True)

            top_candidates = []
            for rec, score in scored_records[:limit]:
                # Normalize display score between 0.50 and 0.98 for top candidates
                display_score = max(0.40, min(0.98, round(score if score <= 1.0 else (0.82 + min(0.16, (score - 1.0) * 0.04)), 3)))
                top_candidates.append(self._record_to_candidate(rec, display_score, query=search_text))

            return top_candidates
        finally:
            db.close()

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

    def _record_to_candidate(self, rec: PhotoRecord, score: float, query: Optional[str] = None) -> CandidatePhoto:
        """Convert a PhotoRecord into a CandidatePhoto schema object with explainable matched reasons."""
        scene_list = json.loads(rec.scene) if rec.scene else []
        objects_list = json.loads(rec.objects) if rec.objects else []
        people_list = json.loads(rec.people) if rec.people else []

        reasons = []
        if rec.location and rec.location not in ("Unknown", "Various"):
            reasons.append(rec.location)
        for s in scene_list:
            clean_s = s.strip().title()
            if clean_s and clean_s not in reasons:
                reasons.append(clean_s)
        for o in objects_list:
            clean_o = o.strip().title()
            if clean_o and clean_o not in reasons:
                reasons.append(clean_o)
        if rec.setting and rec.setting.title() not in reasons:
            reasons.append(rec.setting.title())
        if rec.time_of_day and rec.time_of_day.title() not in reasons:
            reasons.append(rec.time_of_day.title())
        for p in people_list:
            clean_p = p.strip().title()
            if clean_p and clean_p not in reasons:
                reasons.append(clean_p)

        # If query is provided, sort matching terms first
        if query:
            q_tokens = [w.lower() for w in re.findall(r"\b[a-zA-Z0-9]+\b", query) if len(w) >= 3]
            matched_terms = [r for r in reasons if any(qt in r.lower() for qt in q_tokens)]
            other_terms = [r for r in reasons if r not in matched_terms]
            reasons = matched_terms + other_terms

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
            scene=scene_list,
            objects=objects_list,
            people=people_list,
            matched_reasons=reasons[:3],
        )


retrieval_service = RetrievalService()
