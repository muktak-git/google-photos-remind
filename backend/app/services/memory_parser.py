import re
import logging
from typing import Any, Dict, List, Tuple
from app.providers.llm import gemini_provider
from app.models.schemas import ClueData, ClueConfidence, ClueChip

logger = logging.getLogger(__name__)


KNOWN_LOCATIONS = ["rajasthan", "coorg", "bangalore", "jaipur", "udaipur"]
KNOWN_SCENES = ["palace", "courtyard", "campfire", "pool", "water", "coffee estate", "homestay", "cafe", "auditorium", "clinic"]
KNOWN_PEOPLE = ["rahul", "sneha", "aditya", "ananya", "priya", "aarav", "vihaan", "friends", "classmates"]
KNOWN_TIMES = ["day", "evening", "night", "dusk", "sunset", "morning", "afternoon"]


class MemoryParserService:
    """Parses natural-language vague memories into structured machine-retrievable clues."""

    @staticmethod
    async def parse_memory(query: str) -> Tuple[ClueData, List[ClueChip]]:
        """Extract structured retrieval facets with confidence scores and user-facing chips."""
        parsed_data = None

        # 1. Attempt Gemini Multimodal/Language Parsing if client is available
        if gemini_provider.is_available():
            try:
                raw_response = await gemini_provider.parse_memory(query)
                if isinstance(raw_response, dict) and "confidence" in raw_response:
                    parsed_data = raw_response
            except Exception as e:
                logger.warning(f"Gemini memory parsing failed: {e}. Falling back to rule-based parser.")

        # 2. Fallback to heuristic / semantic parser if LLM is unavailable or errored
        if not parsed_data:
            parsed_data = MemoryParserService._fallback_parse(query)

        # 3. Clean and ground parsed data (prevent hallucinations per edge-case.md)
        cleaned_clue = MemoryParserService._sanitize_and_build(parsed_data, query)

        # 4. Generate user-facing display chips
        chips = MemoryParserService._build_chips(cleaned_clue)

        return cleaned_clue, chips

    @staticmethod
    def _fallback_parse(query: str) -> Dict[str, Any]:
        """Local heuristic parser extracting known entities and calibrating confidence."""
        q_lower = query.lower()

        # Location extraction
        loc = None
        loc_conf = 0.0
        for known_loc in KNOWN_LOCATIONS:
            if known_loc in q_lower:
                loc = known_loc.capitalize()
                loc_conf = 0.95
                break

        # Scene extraction
        scene = None
        scene_conf = 0.0
        for s in KNOWN_SCENES:
            if s in q_lower:
                scene = s
                scene_conf = 0.85
                break

        # People extraction
        people = []
        for p in KNOWN_PEOPLE:
            if p in q_lower:
                people.append(p.capitalize())
        people_conf = 0.75 if people else 0.0

        # Time extraction
        time_val = None
        time_conf = 0.0
        for t in KNOWN_TIMES:
            if t in q_lower:
                time_val = t
                time_conf = 0.80
                break

        # Event
        event = None
        event_conf = 0.0
        if "trip" in q_lower or "vacation" in q_lower or "tour" in q_lower:
            event = f"{loc or 'Vacation'} Trip" if loc else "Trip"
            event_conf = 0.80
        elif "party" in q_lower:
            event = "Party"
            event_conf = 0.80

        # Visual details
        vis_details = query.strip()
        vis_conf = 0.60

        return {
            "location": loc,
            "event": event,
            "scene": scene,
            "people": people if people else None,
            "time": time_val,
            "visual_details": vis_details,
            "confidence": {
                "location": loc_conf,
                "event": event_conf,
                "scene": scene_conf,
                "people": people_conf,
                "time": time_conf,
                "visual_details": vis_conf,
            },
        }

    @staticmethod
    def _sanitize_and_build(data: Dict[str, Any], raw_query: str) -> ClueData:
        """Sanitize fields and construct Pydantic ClueData object."""
        conf_dict = data.get("confidence", {})
        confidence = ClueConfidence(
            location=float(conf_dict.get("location", 0.0)),
            event=float(conf_dict.get("event", 0.0)),
            scene=float(conf_dict.get("scene", 0.0)),
            people=float(conf_dict.get("people", 0.0)),
            time=float(conf_dict.get("time", 0.0)),
            visual_details=float(conf_dict.get("visual_details", 0.5)),
        )

        return ClueData(
            location=data.get("location"),
            event=data.get("event"),
            scene=data.get("scene"),
            people=data.get("people"),
            time=data.get("time"),
            visual_details=data.get("visual_details") or raw_query,
            confidence=confidence,
        )

    @staticmethod
    def _build_chips(clue: ClueData) -> List[ClueChip]:
        """Create user-friendly chips with confidence levels for Screen 2."""
        chips: List[ClueChip] = []

        if clue.location and clue.confidence.location >= 0.4:
            pct = int(clue.confidence.location * 100)
            chips.append(ClueChip(
                facet="location",
                value=clue.location,
                confidence=clue.confidence.location,
                display_text=f"📍 {clue.location} ({pct}%)",
            ))

        if clue.scene and clue.confidence.scene >= 0.4:
            pct = int(clue.confidence.scene * 100)
            chips.append(ClueChip(
                facet="scene",
                value=clue.scene,
                confidence=clue.confidence.scene,
                display_text=f"🏛️ {clue.scene.capitalize()} ({pct}%)",
            ))

        if clue.event and clue.confidence.event >= 0.4:
            pct = int(clue.confidence.event * 100)
            chips.append(ClueChip(
                facet="event",
                value=clue.event,
                confidence=clue.confidence.event,
                display_text=f"🎉 {clue.event} ({pct}%)",
            ))

        if clue.people and clue.confidence.people >= 0.4:
            people_str = ", ".join(clue.people)
            pct = int(clue.confidence.people * 100)
            chips.append(ClueChip(
                facet="people",
                value=people_str,
                confidence=clue.confidence.people,
                display_text=f"👥 {people_str} ({pct}%)",
            ))

        if clue.time and clue.confidence.time >= 0.4:
            pct = int(clue.confidence.time * 100)
            chips.append(ClueChip(
                facet="time",
                value=clue.time,
                confidence=clue.confidence.time,
                display_text=f"🕒 {clue.time.capitalize()} ({pct}%)",
            ))

        return chips
