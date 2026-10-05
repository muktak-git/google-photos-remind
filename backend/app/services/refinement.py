import math
import logging
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple
from app.models.schemas import CandidatePhoto, RefineResponse, RefineFacet
from app.providers.llm import gemini_provider

logger = logging.getLogger(__name__)


DISCRIMINATING_DIMENSIONS = [
    "time_of_day",
    "setting",
    "location",
    "scene_type",
    "people_presence",
]


class RefinementEngine:
    """Implements the Shannon entropy uncertainty-driven refinement algorithm."""

    @staticmethod
    async def get_next_question(
        candidates: List[CandidatePhoto],
        answered_dimensions: List[str],
        session_id: str,
        current_turn: int,
        original_query: Optional[str] = None,
        last_constraint_val: Optional[str] = None,
        answered_values: Optional[List[str]] = None,
    ) -> RefineResponse:
        """Find maximal entropy dimension and generate conversational refinement prompt."""
        # 0. Check if user recently answered "not sure", "yes", or "no"
        is_not_sure = False
        val_low = (last_constraint_val or "").lower().strip()
        if last_constraint_val:
            if any(term in val_low for term in ["not sure", "don't know", "dont know", "not remember", "unsure", "no idea"]):
                is_not_sure = True

        # Pure rejection: user explicitly clicked or answered "No"
        is_rejection = val_low in ("no", "n", "nope")

        # Explicit confirmation: user said "Yes" to photo recognition
        is_confirmation = val_low in ("yes", "y", "yeah", "yep", "yes, that's it!", "yes, that's it") and any(
            d in ("recognition", "recognition_ready", "confirmation") for d in answered_dimensions
        )

        if is_confirmation:
            return RefineResponse(
                session_id=session_id,
                dimension="recognition_confirmed",
                question="Is this the photo you remember?",
                options=["Yes, that's it!", "No, keep looking"],
                turn=current_turn,
                candidates_remaining=len(candidates),
                summary_message="Great! Here is the top match from your memory.",
                follow_up_prompt="Tap 'Yes, that's it!' on the photo to confirm, or explore others.",
                facets=[
                    RefineFacet(
                        title="Is this the photo you remember?",
                        dimension="confirmation",
                        options=["Yes, that's it!", "No, keep looking"],
                    )
                ],
            )

        if is_rejection:
            hints = RefinementEngine.generate_embedding_hints(
                query=original_query,
                candidates=candidates,
                rejected_values=answered_values or answered_dimensions,
            )
            hint_facets = [
                RefineFacet(
                    title="Hint keywords",
                    dimension="visual",
                    options=hints,
                )
            ]
            return RefineResponse(
                session_id=session_id,
                dimension="more_clues",
                question="What do you remember more?",
                options=hints,
                turn=current_turn,
                candidates_remaining=len(candidates),
                summary_message="No problem! Let's explore other clues.",
                follow_up_prompt="What do you remember more?",
                facets=hint_facets,
                hint_keywords=hints,
            )

        # Build summary message & multi-facets
        loc_counts = Counter([c.location for c in candidates if c.location])
        main_loc = loc_counts.most_common(1)[0][0] if loc_counts else None
        if not main_loc or main_loc.lower() in ["other", "none", ""]:
            if original_query:
                q_low = original_query.lower()
                for known_loc in ["coorg", "rajasthan", "bangalore", "mysore"]:
                    if known_loc in q_low:
                        main_loc = known_loc.capitalize()
                        break

        if is_not_sure:
            if main_loc:
                summary = f"No problem! Let's explore other clues from your {main_loc} photos."
            else:
                summary = "No problem! Let's explore other clues from your photo library."
            follow_up = "Do any of these settings or details sound familiar?"
        elif current_turn > 1 and len(candidates) <= 3:
            summary = f"I found {len(candidates)} photo{'s' if len(candidates) != 1 else ''} that may match."
            follow_up = "Do you recognize any of these photos?"
        else:
            if main_loc and main_loc.lower() not in ["other", "none", ""]:
                summary = f"I found {len(candidates)} possible photos from your {main_loc} trip."
            else:
                summary = f"I found {len(candidates)} possible photos that match your memory."
            follow_up = "Do you remember anything else?"

        if not candidates:
            return RefineResponse(
                session_id=session_id,
                dimension="general",
                question="Could you recall any other specific detail about the photo?",
                options=["At the palace", "In Coorg", "With friends", "Not sure"],
                turn=current_turn,
                candidates_remaining=0,
                summary_message=summary,
                follow_up_prompt=follow_up,
                facets=[],
            )

        facets = RefinementEngine._build_multi_facets(
            candidates=candidates,
            answered_dimensions=answered_dimensions,
            original_query=original_query,
            is_not_sure=is_not_sure,
            answered_values=answered_values,
        )

        # Recognition trigger:
        # Trigger recognition when narrowed to <= 6 photos, or if candidate facets are completely exhausted
        if not is_rejection and ((len(candidates) <= 6 and current_turn > 1) or not facets):
            recog_facets = [
                RefineFacet(
                    title="Do you recognize any of these photos?",
                    dimension="recognition",
                    options=["Yes", "No"],
                )
            ]
            return RefineResponse(
                session_id=session_id,
                dimension="recognition_ready",
                question="Do you recognize any of these photos?",
                options=["Yes", "No"],
                turn=current_turn,
                candidates_remaining=len(candidates),
                summary_message=summary if (is_not_sure or len(candidates) > 6) else f"I found {len(candidates)} photo{'s' if len(candidates) != 1 else ''} that may match.",
                follow_up_prompt="Do you recognize any of these photos?",
                facets=recog_facets,
            )

        # 1. Compute entropy for each candidate dimension not yet asked
        best_dimension, best_entropy, distribution = RefinementEngine._find_best_dimension(
            candidates, answered_dimensions
        )

        logger.info(
            f"Uncertainty Analysis: Selected '{best_dimension}' (Entropy: {best_entropy:.3f}) "
            f"from distribution: {distribution}"
        )

        # 2. Check if entropy is 0 and no facets are available
        if not facets and (best_entropy <= 0.001 or not distribution):
            recog_facets = [
                RefineFacet(
                    title="Do you recognize any of these photos?",
                    dimension="recognition",
                    options=["Yes", "No"],
                )
            ]
            return RefineResponse(
                session_id=session_id,
                dimension="recognition_ready",
                question="Do you recognize any of these photos?",
                options=["Yes", "No"],
                turn=current_turn,
                candidates_remaining=len(candidates),
                summary_message=f"I found {len(candidates)} photos that may match.",
                follow_up_prompt="Do you recognize any of these photos?",
                facets=recog_facets,
            )

        # 3. Prefer primary facet from smart facets
        if facets:
            question = facets[0].title
            options = facets[0].options
            dim_to_use = facets[0].dimension
        else:
            question, options = await RefinementEngine._generate_question(best_dimension, distribution)
            dim_to_use = best_dimension

        return RefineResponse(
            session_id=session_id,
            dimension=dim_to_use,
            question=question,
            options=options,
            turn=current_turn,
            candidates_remaining=len(candidates),
            summary_message=summary,
            follow_up_prompt=follow_up,
            facets=facets,
        )

    @staticmethod
    def _build_multi_facets(
        candidates: List[CandidatePhoto],
        answered_dimensions: List[str],
        original_query: Optional[str] = None,
        is_not_sure: bool = False,
        answered_values: Optional[List[str]] = None,
    ) -> List[RefineFacet]:
        facets: List[RefineFacet] = []
        ans_set = set(d.lower() for d in answered_dimensions)
        query_str = (original_query or "").lower()

        # Phase 1 / Initial Facets: When? and What did it look like?
        # Only show if not already answered or skipped (and user didn't say "Not sure")
        time_answered = any(k in ans_set for k in ["time_or_date", "time_of_day", "time"])
        visual_answered = any(k in ans_set for k in ["visual", "scene_type"])

        if not is_not_sure:
            if not time_answered:
                has_xmas = any(c.date and ("12-24" in c.date or "12-25" in c.date) for c in candidates)
                has_ny = any(c.date and ("12-31" in c.date or "01-01" in c.date) for c in candidates)
                if has_xmas or has_ny:
                    facets.append(RefineFacet(
                        title="When?",
                        dimension="time_or_date",
                        options=["Around Christmas", "New Year", "Not sure"],
                    ))
                else:
                    times = set((c.time_of_day or "").lower() for c in candidates if c.time_of_day)
                    if len(times) > 1:
                        opts = []
                        if "day" in times:
                            opts.append("During the day")
                        if "evening" in times:
                            opts.append("In the evening / dusk")
                        if "night" in times:
                            opts.append("At night")
                        opts.append("Not sure")
                        facets.append(RefineFacet(
                            title="When?",
                            dimension="time_of_day",
                            options=opts,
                        ))

            if not visual_answered:
                has_blue = any("blue wall" in c.visual_description.lower() for c in candidates)
                has_arches = any("arch" in c.visual_description.lower() for c in candidates)
                has_fountain = any("fountain" in c.visual_description.lower() for c in candidates)
                has_float = any("float" in c.visual_description.lower() for c in candidates)

                if has_blue:
                    facets.append(RefineFacet(
                        title="What did it look like?",
                        dimension="visual",
                        options=["Blue wall", "Outdoor", "Beach nearby", "Not sure"],
                    ))
                elif has_arches or has_fountain:
                    opts = []
                    if has_arches:
                        opts.append("Carved arches")
                    if has_fountain:
                        opts.append("Courtyard fountain")
                    opts.extend(["Illuminated facade", "Not sure"])
                    facets.append(RefineFacet(
                        title="What did it look like?",
                        dimension="visual",
                        options=opts,
                    ))
                elif has_float:
                    facets.append(RefineFacet(
                        title="What did it look like?",
                        dimension="visual",
                        options=["Pool floats", "Water slide", "Splash pad", "Not sure"],
                    ))
                else:
                    scenes = [s for c in candidates for s in c.scene if s.lower() not in ["indoor", "outdoor", "mixed"]]
                    scenes_counted = [k for k, _ in Counter(scenes).most_common(3)]
                    if scenes_counted:
                        facets.append(RefineFacet(
                            title="What was the setting?",
                            dimension="scene_type",
                            options=[s.capitalize() for s in scenes_counted] + ["Not sure"],
                        ))

        # If Phase 1 facets are answered/skipped or user said "Not sure", dynamically advance to Phase 2 smart facets!
        if len(facets) == 0 or is_not_sure:
            facets = []

            # 1. Setting & Vibe
            if not any(k in ans_set for k in ["setting_vibe", "setting", "atmosphere"]):
                if "coorg" in query_str or any("coorg" in (c.location or "").lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Setting & Vibe",
                        dimension="setting_vibe",
                        options=["Homestay veranda", "Coffee estate garden", "Indoor lounge", "Not sure"],
                    ))
                elif "palace" in query_str or any("palace" in " ".join(c.scene).lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Palace Area",
                        dimension="setting_vibe",
                        options=["Grand Durbar Hall", "Palace courtyard", "Garden pavilion", "Not sure"],
                    ))
                elif "water" in query_str or "pool" in query_str or any("pool" in " ".join(c.scene).lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Pool Area",
                        dimension="setting_vibe",
                        options=["Swimming pool deck", "Water park slides", "Shallow splash area", "Not sure"],
                    ))
                else:
                    settings = set(c.setting.lower() for c in candidates if c.setting)
                    if len(settings) > 1:
                        facets.append(RefineFacet(
                            title="Setting & Vibe",
                            dimension="setting_vibe",
                            options=["Outdoors in open air", "Indoors inside", "Not sure"],
                        ))

            # 2. Who was there?
            if not any(k in ans_set for k in ["people_presence", "social"]):
                has_people = any(len(c.people) > 0 for c in candidates)
                has_solo = any(len(c.people) == 0 for c in candidates)
                if has_people and has_solo:
                    facets.append(RefineFacet(
                        title="Who was there?",
                        dimension="people_presence",
                        options=["With friends", "Solo / just the scenery", "Not sure"],
                    ))

            # 3. Highlights & Activities
            if not any(k in ans_set for k in ["highlights", "activity"]):
                if "coorg" in query_str or any("coorg" in (c.location or "").lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Highlights",
                        dimension="highlights",
                        options=["Campfire nearby", "Misty hills view", "Fresh brewed coffee", "Not sure"],
                    ))
                elif "palace" in query_str or any("palace" in " ".join(c.scene).lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Highlights",
                        dimension="highlights",
                        options=["Night illumination", "Carved arches", "Folk performance", "Not sure"],
                    ))
                elif "water" in query_str or "pool" in query_str or any("pool" in " ".join(c.scene).lower() for c in candidates):
                    facets.append(RefineFacet(
                        title="Highlights",
                        dimension="highlights",
                        options=["Inflatable floats", "Water slide splash", "Sun loungers", "Not sure"],
                    ))

        # Phase 3: Dynamic Candidate Facets & Semantic Memory Clues (for Turns 2, 3, 4+)
        # When Phase 1 and Phase 2 are exhausted, dynamically extract features from remaining candidates!
        if len(facets) == 0:
            ans_vals_lower = set((v or "").lower().strip() for v in (answered_values or []))

            # 3.1 Specific Candidate Objects
            cand_objs: List[str] = []
            for c in candidates:
                for obj in c.objects:
                    obj_clean = obj.strip()
                    if len(obj_clean) >= 3 and not any(obj_clean.lower() in v or v in obj_clean.lower() for v in ans_vals_lower):
                        cand_objs.append(obj_clean.title())

            obj_counts = Counter(cand_objs)
            # Find discriminative objects (present in some candidates, not all)
            discriminative_objs = [
                obj for obj, count in obj_counts.most_common(6)
                if 0 < count < len(candidates)
            ]
            if not discriminative_objs and obj_counts:
                discriminative_objs = [obj for obj, _ in obj_counts.most_common(4)]

            if discriminative_objs:
                top_objs = discriminative_objs[:4]
                facets.append(RefineFacet(
                    title="Do you remember any of these details?",
                    dimension="objects",
                    options=top_objs + ["Not sure"],
                ))

            # 3.2 Distinct Scenes or Activities
            cand_scenes = []
            for c in candidates:
                for s in c.scene:
                    s_clean = s.strip()
                    s_low = s_clean.lower()
                    if s_low not in ["indoor", "outdoor", "mixed", "general", "other"] and not any(s_low in v or v in s_low for v in ans_vals_lower):
                        cand_scenes.append(s_clean.capitalize())
            scene_counts = Counter(cand_scenes)
            disc_scenes = [
                s for s, count in scene_counts.most_common(4)
                if count < len(candidates) or len(candidates) <= 2
            ]
            if disc_scenes and len(facets) < 2:
                facets.append(RefineFacet(
                    title="What was the setting or activity?",
                    dimension="activity",
                    options=disc_scenes[:3] + ["Not sure"],
                ))

            # 3.3 Dynamic Embedding Hints
            if len(facets) < 2:
                hints = RefinementEngine.generate_embedding_hints(
                    query=original_query,
                    candidates=candidates,
                    rejected_values=answered_values,
                    top_k=4,
                )
                filtered_hints = [h for h in hints if not any(h.lower() in v or v in h.lower() for v in ans_vals_lower)]
                if filtered_hints:
                    facets.append(RefineFacet(
                        title="Memory clues",
                        dimension="visual",
                        options=filtered_hints[:4] + ["Not sure"],
                    ))

        return facets

    @staticmethod
    def _find_best_dimension(
        candidates: List[CandidatePhoto],
        answered_dimensions: List[str],
    ) -> Tuple[str, float, Dict[str, int]]:
        """Evaluate candidate entropy across all eligible dimensions and select maximal."""
        N = len(candidates)
        best_dim = "time_of_day"
        best_entropy = -1.0
        best_dist: Dict[str, int] = {}

        for dim in DISCRIMINATING_DIMENSIONS:
            if dim in answered_dimensions:
                continue

            values = []
            for c in candidates:
                val = RefinementEngine._extract_dim_value(c, dim)
                if val:
                    values.append(val)

            if not values:
                continue

            counts = Counter(values)
            # Shannon entropy: H = - sum(p * log2(p))
            entropy = 0.0
            for count in counts.values():
                p = count / N
                if p > 0:
                    entropy -= p * math.log2(p)

            # Maximize entropy (prefer even splits)
            if entropy > best_entropy and len(counts) > 1:
                best_entropy = entropy
                best_dim = dim
                best_dist = dict(counts)

        return best_dim, best_entropy, best_dist

    @staticmethod
    def _extract_dim_value(c: CandidatePhoto, dim: str) -> Optional[str]:
        """Extract normalized value for a given dimension from a candidate photo."""
        if dim == "time_of_day":
            return (c.time_of_day or "day").lower()
        elif dim == "setting":
            return (c.setting or "outdoor").lower()
        elif dim == "location":
            return (c.location or "other").capitalize()
        elif dim == "people_presence":
            return "with friends" if len(c.people) > 0 else "alone"
        elif dim == "scene_type":
            if any("palace" in s.lower() for s in c.scene):
                return "palace"
            elif any("campfire" in s.lower() or "estate" in s.lower() for s in c.scene):
                return "coorg estate"
            elif any("pool" in s.lower() or "water" in s.lower() for s in c.scene):
                return "pool & water"
            elif any("cafe" in s.lower() or "brewery" in s.lower() for s in c.scene):
                return "cafe or brewery"
            return "general"
        return None

    @staticmethod
    async def _generate_question(dimension: str, distribution: Dict[str, int]) -> Tuple[str, List[str]]:
        """Generate friendly question and options via Gemini with fallback templates."""
        # 1. Attempt Gemini prompt if available
        if gemini_provider.is_available():
            try:
                res = await gemini_provider.generate_refinement_question(dimension, distribution)
                if isinstance(res, dict) and "question" in res and "options" in res:
                    opts = res["options"]
                    if "Not sure" not in opts:
                        opts.append("Not sure")
                    return res["question"], opts
            except Exception as e:
                logger.warning(f"Gemini refinement question generation failed: {e}. Using template.")

        # 2. Template fallback
        if dimension == "time_of_day":
            question = "Do you remember if it was during the daytime, evening, or at night?"
            options = ["During the day", "In the evening / dusk", "At night", "Not sure"]
        elif dimension == "setting":
            question = "Was the photo taken outdoors or indoors?"
            options = ["Outdoors in open air", "Indoors inside a building", "Not sure"]
        elif dimension == "location":
            locs = [k for k in distribution.keys() if k.lower() != "other"][:3]
            question = f"Do you remember which place this was at?"
            options = locs + ["Somewhere else", "Not sure"]
        elif dimension == "scene_type":
            scenes = [k.capitalize() for k in distribution.keys()][:3]
            question = "What was the main setting or activity in the photo?"
            options = scenes + ["Not sure"]
        elif dimension == "people_presence":
            question = "Were you with a group of friends or was it a solo photo?"
            options = ["With friends", "Solo / just the scenery", "Not sure"]
        else:
            question = "Do you recall any other detail about this moment?"
            options = list(distribution.keys())[:3] + ["Not sure"]

        return question, options

    @staticmethod
    def generate_embedding_hints(
        query: Optional[str],
        candidates: List[CandidatePhoto],
        rejected_values: Optional[List[str]] = None,
        top_k: int = 6,
    ) -> List[str]:
        """Generate smart hint keywords using embeddings of the user's input query and vector store."""
        import re
        from app.providers.embedding import EmbeddingProvider
        from app.providers.vectorstore import vector_store
        from app.services.retrieval import retrieval_service
        from collections import defaultdict

        emb_provider = EmbeddingProvider()
        rejected_lower = [v.lower() for v in (rejected_values or []) if v]
        query_text = (query or "").lower()
        query_words = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", query_text))

        # 1. Embed user query using EmbeddingProvider
        query_vec = emb_provider.embed_text(query or "photo memory")

        # 2. Retrieve top semantic neighbor photos from vector store
        score_map = defaultdict(float)
        try:
            results = vector_store.query(query_embedding=query_vec, n_results=30)
            if results and "ids" in results and results["ids"]:
                pids = results["ids"][0]
                dists = results.get("distances", [[]])[0]
                matched_cands = retrieval_service.get_candidates_by_ids(pids)
                for c, d in zip(matched_cands, dists):
                    # Proximity weight: closer vector distance gets higher weight
                    weight = max(0.1, 1.0 - float(d))
                    for item in set(c.objects + c.scene):
                        score_map[item.lower()] += weight
        except Exception as e:
            logger.warning(f"Vector hint query failed: {e}")

        # 3. Also incorporate current candidates' metadata
        for c in candidates:
            for item in set(c.objects + c.scene):
                score_map[item.lower()] += 0.5

        # 4. Curated evocative candidate pool based on cluster
        ranked_hints = []
        evocative_pool = []
        if "coorg" in query_text or any("coorg" in (c.location or "").lower() for c in candidates):
            evocative_pool = [
                "Homestay veranda", "Campfire", "Misty hills", "Coffee plantation",
                "Wooden bench", "Garden umbrella", "Plantation mugs", "Waterfall nearby"
            ]
        elif "rajasthan" in query_text or any("palace" in " ".join(c.scene).lower() for c in candidates):
            evocative_pool = [
                "Grand Durbar Hall", "Palace courtyard", "Carved arches",
                "Night illumination", "Courtyard fountain", "Royal garden"
            ]
        elif "water" in query_text or "pool" in query_text or any("pool" in " ".join(c.scene).lower() for c in candidates):
            evocative_pool = [
                "Water slide", "Inflatable float", "Swimming pool deck",
                "Splash pad", "Sun loungers", "Poolside table"
            ]
        else:
            evocative_pool = [
                "Outdoor patio", "Garden terrace", "With friends",
                "Evening lights", "Wooden table"
            ]

        # Score evocative pool items using embedding similarity
        for phrase in evocative_pool:
            p_low = phrase.lower()
            if any(p_low == r or r in p_low or p_low in r for r in rejected_lower) or any(w in query_words for w in p_low.split()):
                continue
            p_vec = emb_provider.embed_text(phrase)
            dot_sim = sum(q * p for q, p in zip(query_vec, p_vec))
            match_score = dot_sim + score_map.get(p_low, 0.0) + (1.0 if any(word in score_map for word in p_low.split()) else 0.0)
            ranked_hints.append((phrase, match_score))

        # Also score items from vector store metadata
        for item, v_score in score_map.items():
            item_clean = item.strip().title()
            if item.lower() in [h[0].lower() for h in ranked_hints]:
                continue
            if len(item) < 3 or item.lower() in ("photo", "indoor", "outdoor", "mixed", "other", "general", "none"):
                continue
            if any(item.lower() in r or r in item.lower() for r in rejected_lower) or item.lower() in query_words:
                continue
            item_vec = emb_provider.embed_text(item)
            dot_sim = sum(q * p for q, p in zip(query_vec, item_vec))
            total_score = v_score + (dot_sim * 2.0)
            ranked_hints.append((item_clean, total_score))

        # Sort by total score descending
        ranked_hints.sort(key=lambda x: x[1], reverse=True)

        final_hints = []
        seen = set()
        for phrase, _ in ranked_hints:
            norm = phrase.lower().replace(" ", "")
            if norm not in seen:
                seen.add(norm)
                final_hints.append(phrase)
            if len(final_hints) >= top_k:
                break

        return final_hints or ["Homestay veranda", "Campfire", "Coffee plantation", "Misty hills", "Wooden bench"]


refinement_engine = RefinementEngine()
