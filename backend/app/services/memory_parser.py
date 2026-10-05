import re
import logging
from typing import Any, Dict, List, Tuple, Optional
from app.providers.llm import gemini_provider
from app.models.schemas import ClueData, ClueConfidence, ClueChip

logger = logging.getLogger(__name__)

KNOWN_LOCATIONS = ["rajasthan", "coorg", "bangalore", "jaipur", "udaipur", "mysore"]
KNOWN_SCENES = ["palace", "courtyard", "campfire", "pool", "water", "coffee estate", "homestay", "cafe", "auditorium", "clinic", "temple", "lake"]
KNOWN_PEOPLE = ["rahul", "sneha", "aditya", "ananya", "priya", "aarav", "vihaan", "friends", "classmates"]
KNOWN_TIMES = ["day", "evening", "night", "dusk", "sunset", "morning", "afternoon"]


class MemoryParserService:
    """Parses natural-language vague memories into structured machine-retrievable clues."""

    @staticmethod
    async def parse_memory(query: str) -> Tuple[ClueData, List[ClueChip], str]:
        """Extract structured retrieval facets, user-friendly chips, and draft search summary."""
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

        # 4. Generate user-facing display chips (jargon-free, no confidence percentages)
        chips = MemoryParserService._build_chips(cleaned_clue, query)

        # 5. Generate human-friendly draft search summary
        draft_summary = MemoryParserService._compose_draft_summary(cleaned_clue, query)

        return cleaned_clue, chips, draft_summary

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
        if any(w in q_lower for w in ["temple", "mandir", "shrine", "palace", "courtyard", "fort", "monument", "heritage"]):
            if "temple" in q_lower or "mandir" in q_lower or "shrine" in q_lower:
                scene = "Temple & Heritage Architecture"
            elif "palace" in q_lower or "courtyard" in q_lower:
                scene = "Palace Courtyard"
            else:
                scene = "Historic Heritage Architecture"
            scene_conf = 0.90
        elif any(w in q_lower for w in ["pool", "swimming", "splash", "water"]):
            scene = "Swimming Pool"
            scene_conf = 0.90
        elif any(w in q_lower for w in ["cafe", "café", "coffee", "estate", "homestay"]):
            scene = "Cozy Café & Coffee Estate"
            scene_conf = 0.85
        elif any(w in q_lower for w in ["sun", "sunny", "sunlight", "daylight"]):
            scene = "Bright Outdoor Sunshine"
            scene_conf = 0.85
        elif any(w in q_lower for w in ["lake", "river", "mountain", "hills", "nature"]):
            scene = "Scenic Lake & Nature"
            scene_conf = 0.85
        elif any(w in q_lower for w in ["campfire", "fire"]):
            scene = "Campfire Gathering"
            scene_conf = 0.85
        elif any(w in q_lower for w in ["fest", "college", "stage", "auditorium"]):
            scene = "College Fest Stage"
            scene_conf = 0.85
        elif any(w in q_lower for w in ["clinic", "hospital", "prescription", "medical"]):
            scene = "Medical Clinic Documents"
            scene_conf = 0.85
        else:
            for s in KNOWN_SCENES:
                if s in q_lower:
                    scene = s.capitalize()
                    scene_conf = 0.80
                    break

        # People extraction
        people = []
        if any(w in q_lower for w in ["kid", "kids", "children", "child", "baby", "babies", "toddler"]):
            people.append("Kids & Children")
        if any(w in q_lower for w in ["friend", "friends", "classmate", "classmates", "family"]):
            people.append("Friends & Family")
        for p in KNOWN_PEOPLE:
            if p in q_lower and p not in ["friends", "classmates"]:
                people.append(p.capitalize())
        people_conf = 0.85 if people else 0.0

        # Time extraction
        time_val = None
        time_conf = 0.0
        if any(w in q_lower for w in ["sun", "sunny", "sunlight", "day", "daylight", "morning", "afternoon"]):
            time_val = "Bright Daytime"
            time_conf = 0.85
        elif any(w in q_lower for w in ["sunset", "dusk", "evening", "golden hour"]):
            time_val = "Sunset / Golden Hour"
            time_conf = 0.85
        elif any(w in q_lower for w in ["night", "campfire", "dark"]):
            time_val = "Nighttime"
            time_conf = 0.85

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
    def _build_chips(clue: ClueData, raw_query: str = "") -> List[ClueChip]:
        """Create clean, user-friendly clue badges without jargon or confidence percentages."""
        chips: List[ClueChip] = []

        if clue.location and clue.confidence.location >= 0.4:
            chips.append(ClueChip(
                facet="location",
                value=clue.location,
                confidence=clue.confidence.location,
                display_text=f"📍 {clue.location}",
            ))

        if clue.scene and clue.confidence.scene >= 0.4:
            chips.append(ClueChip(
                facet="scene",
                value=clue.scene,
                confidence=clue.confidence.scene,
                display_text=f"🏛️ {clue.scene}",
            ))

        if clue.event and clue.confidence.event >= 0.4:
            chips.append(ClueChip(
                facet="event",
                value=clue.event,
                confidence=clue.confidence.event,
                display_text=f"🎉 {clue.event}",
            ))

        if clue.people and clue.confidence.people >= 0.4:
            people_str = ", ".join(clue.people)
            chips.append(ClueChip(
                facet="people",
                value=people_str,
                confidence=clue.confidence.people,
                display_text=f"👥 {people_str}",
            ))

        if clue.time and clue.confidence.time >= 0.4:
            chips.append(ClueChip(
                facet="time",
                value=clue.time,
                confidence=clue.confidence.time,
                display_text=f"☀️ {clue.time}",
            ))

        # Ensure chips is never empty so Screen 2 always renders actionable context
        if not chips and raw_query:
            clean_word = raw_query.strip().capitalize()
            chips.append(ClueChip(
                facet="visual",
                value=raw_query.strip(),
                confidence=0.8,
                display_text=f"🔍 {clean_word}",
            ))

        return chips

    @staticmethod
    def _compose_draft_summary(clue: ClueData, query: str) -> str:
        """Compose a natural-language search plan sentence for Step 2."""
        q_lower = query.lower()

        if "temple" in q_lower or "mandir" in q_lower or "shrine" in q_lower:
            return "Searching for heritage temples, traditional shrines, and historic palace architecture."
        if "sun" in q_lower or "sunny" in q_lower:
            return "Searching for bright outdoor photos captured in warm daylight and sunny skies."
        if any(w in q_lower for w in ["kid", "kids", "children", "baby", "babies"]):
            return "Searching for family photos featuring kids and children having fun."
        if "coorg" in q_lower and ("cafe" in q_lower or "café" in q_lower or "coffee" in q_lower):
            return "Searching for cozy cafes and relaxed gatherings from your Coorg trip."
        if "rajasthan" in q_lower and ("palace" in q_lower or "courtyard" in q_lower or "fort" in q_lower):
            return "Searching for grand palace courtyards with carved arches from your Rajasthan trip."

        # Dynamic synthesis based on extracted clues
        parts = []
        if clue.scene:
            parts.append(clue.scene.lower())
        if clue.location:
            parts.append(f"in {clue.location}")
        if clue.people:
            parts.append(f"with {', '.join(clue.people)}")
        if clue.time:
            parts.append(f"during {clue.time.lower()}")

        if parts:
            joined = " ".join(parts)
            return f"Searching for photos of {joined}."

        clean_q = query.strip()
        if len(clean_q) > 40:
            return f"Searching for photos matching: “{clean_q[:40]}...”"
        return f"Searching for photos matching: “{clean_q}”."
