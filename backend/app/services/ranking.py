import logging
from typing import List, Optional, Tuple
from app.models.schemas import CandidatePhoto

logger = logging.getLogger(__name__)


class RankingService:
    """Applies refinement constraints, re-ranks candidates, and handles zero-candidate rollbacks."""

    @staticmethod
    def apply_constraint(
        candidates: List[CandidatePhoto],
        dimension: str,
        value: str,
    ) -> Tuple[List[CandidatePhoto], Optional[str]]:
        """Apply user constraint to candidates and re-rank with graceful rollback protection."""
        val_lower = value.lower()

        # 1. "Not sure" / "Don't remember" does not filter photos
        if any(term in val_lower for term in ["not sure", "don't remember", "dont remember", "not remember", "unsure", "no idea"]):
            banner = "No problem! Let's try another detail you might remember."
            return candidates, banner

        # 2. Recognition response (Yes / No)
        if dimension in ("recognition", "recognition_ready") or val_lower in ("yes", "no"):
            if "yes" in val_lower:
                banner = "Great! Tap the photo you recognize below to confirm."
                return candidates, banner
            else:
                banner = "No problem! What else do you remember?"
                return candidates, banner

        matched_candidates = []
        unmatched_candidates = []

        for c in candidates:
            is_match = RankingService._check_dimension_match(c, dimension, val_lower)
            if is_match:
                # Boost matched score
                c.score = min(1.0, round(c.score * 1.15 + 0.1, 3))
                matched_candidates.append(c)
            else:
                c.score = max(0.05, round(c.score * 0.5, 3))
                unmatched_candidates.append(c)

        # 2. Over-constrained edge case (candidates drop to 0) -> Rollback per edge-case.md §4.1
        if len(matched_candidates) == 0:
            logger.warning(
                f"Constraint '{dimension}={value}' resulted in 0 matches out of {len(candidates)} candidates. "
                f"Rolling back to previous candidate set."
            )
            banner = (
                f"None of those photos matched '{value}'. "
                f"Showing the closest photos from that memory so we can try another clue!"
            )
            # Re-sort existing candidates without dropping
            return sorted(candidates, key=lambda x: x.score, reverse=True), banner

        # 3. Successful filtering: Return matched candidates sorted by boosted score
        matched_candidates.sort(key=lambda x: x.score, reverse=True)
        banner = f"I found {len(matched_candidates)} photos that may match."
        return matched_candidates, banner

    @staticmethod
    def _check_dimension_match(c: CandidatePhoto, dimension: str, val_lower: str) -> bool:
        """Evaluate if candidate photo matches the selected constraint value."""
        # 1. Specific visual feature & object cues (e.g. "blue wall", "carved arches", "beach nearby")
        if any(term in val_lower for term in ["blue wall", "blue"]):
            return "blue wall" in c.visual_description.lower() or any("blue" in o.lower() for o in c.objects)

        if "christmas" in val_lower:
            return (c.date and ("12-24" in c.date or "12-25" in c.date)) or "christmas" in c.visual_description.lower()

        if "new year" in val_lower:
            return (c.date and ("12-31" in c.date or "01-01" in c.date)) or "new year" in c.visual_description.lower()

        if "beach" in val_lower:
            return "beach" in c.visual_description.lower() or any("beach" in s.lower() for s in c.scene)

        if "arch" in val_lower:
            return "arch" in c.visual_description.lower() or any("arch" in o.lower() for o in c.objects)

        if "fountain" in val_lower:
            return "fountain" in c.visual_description.lower() or any("fountain" in o.lower() for o in c.objects)

        if "float" in val_lower:
            return "float" in c.visual_description.lower() or any("float" in o.lower() for o in c.objects)

        if "campfire" in val_lower or "fire" in val_lower:
            return "fire" in c.visual_description.lower() or any("fire" in s.lower() for s in c.scene)

        if "veranda" in val_lower:
            return "veranda" in c.visual_description.lower() or any("veranda" in s.lower() for s in c.scene) or any("veranda" in o.lower() for o in c.objects)

        if "estate" in val_lower or "garden" in val_lower:
            return any("estate" in s.lower() or "garden" in s.lower() for s in c.scene) or "estate" in c.visual_description.lower() or "garden" in c.visual_description.lower()

        if "lounge" in val_lower:
            return any("lounge" in s.lower() for s in c.scene) or "lounge" in c.visual_description.lower()

        if "durbar" in val_lower:
            return "durbar" in c.visual_description.lower() or any("durbar" in s.lower() for s in c.scene)

        if "courtyard" in val_lower:
            return "courtyard" in c.visual_description.lower() or any("courtyard" in s.lower() for s in c.scene) or any("courtyard" in o.lower() for o in c.objects)

        if "pavilion" in val_lower:
            return "pavilion" in c.visual_description.lower() or any("pavilion" in s.lower() for s in c.scene)

        if "slide" in val_lower or "splash" in val_lower:
            return "slide" in c.visual_description.lower() or any("slide" in s.lower() or "pool" in s.lower() or "water" in s.lower() for s in c.scene)

        if "misty" in val_lower or "hills" in val_lower:
            return "mist" in c.visual_description.lower() or any("nature" in s.lower() for s in c.scene) or "hill" in c.visual_description.lower()

        if "coffee" in val_lower:
            return "coffee" in c.visual_description.lower() or any("coffee" in s.lower() for s in c.scene) or any("coffee" in o.lower() for o in c.objects)

        # 2. Time of day or date cues
        if dimension in ("time_of_day", "time_or_date", "time"):
            time_val = (c.time_of_day or "day").lower()
            if "day" in val_lower:
                return "day" in time_val
            elif "evening" in val_lower or "dusk" in val_lower:
                return "evening" in time_val or "dusk" in time_val
            elif "night" in val_lower:
                return "night" in time_val

        # 3. Setting & Vibe cues
        if dimension in ("setting", "setting_vibe", "environment"):
            setting_val = (c.setting or "outdoor").lower()
            if "outdoor" in val_lower or "open air" in val_lower:
                return "outdoor" in setting_val or "outdoor" in c.visual_description.lower()
            elif "indoor" in val_lower or "inside" in val_lower:
                return "indoor" in setting_val or "indoor" in c.visual_description.lower()

        # 4. Location cues
        if dimension == "location":
            loc_val = (c.location or "").lower()
            return any(word in loc_val for word in val_lower.split() if len(word) > 2)

        # 5. People presence & Social context
        if dimension in ("people_presence", "social") or "friends" in val_lower or "solo" in val_lower:
            if "friends" in val_lower or "group" in val_lower:
                return len(c.people) > 0
            elif "solo" in val_lower or "alone" in val_lower or "scenery" in val_lower:
                return len(c.people) <= 1

        # 6. Scene type
        if dimension in ("scene_type", "highlights", "activity"):
            combined_scene = " ".join(c.scene).lower()
            if "palace" in val_lower:
                return "palace" in combined_scene or "palace" in c.visual_description.lower()
            elif "coorg" in val_lower or "estate" in val_lower:
                return "estate" in combined_scene or "coorg" in combined_scene
            elif "pool" in val_lower or "water" in val_lower:
                return "pool" in combined_scene or "water" in combined_scene
            elif "cafe" in val_lower or "brewery" in val_lower:
                return "cafe" in combined_scene or "brewery" in combined_scene

        # 7. Specific objects & items
        if dimension in ("objects", "object", "details", "visual"):
            for obj in c.objects:
                if any(w in obj.lower() for w in val_lower.split() if len(w) >= 3):
                    return True

        # 8. General freeform matching across all photo text
        full_text = f"{c.visual_description.lower()} {' '.join(c.scene).lower()} {' '.join(c.objects).lower()} {(c.setting or '').lower()}"
        words = [w for w in val_lower.split() if len(w) >= 3 and w not in ["with", "that", "from", "around", "near", "this", "some", "were", "there"]]
        if words:
            return any(w in full_text for w in words)

        return True


ranking_service = RankingService()
