import json
import logging
from typing import Any, Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


IMAGE_DESCRIPTION_PROMPT = """You are an expert visual memory indexer for Google Photos.
Analyze this photo thoroughly and extract structured visual metadata.
Output MUST be valid JSON adhering strictly to the following schema:
{
  "visual_description": "detailed sentence describing the setting, objects, mood, and composition",
  "scene": ["array of scene tags, e.g. palace, courtyard, coffee estate, pool, indoor, outdoor"],
  "objects": ["array of noticeable objects visible in the image"],
  "people_count": 0,
  "setting": "indoor or outdoor or mixed",
  "time_of_day": "day or evening or night",
  "ocr_text": "any text, signs, logos, or captions visible in the image, or empty string"
}
"""


MEMORY_PARSING_PROMPT = """You are an AI memory reconstruction assistant for Google Photos.
A user is searching for a photo using an incomplete, vague memory.
Analyze the user's input and extract structured retrieval clues with confidence scores between 0.0 and 1.0.
Output MUST be valid JSON adhering strictly to this schema:
{
  "location": "extracted location or null",
  "event": "extracted event name/concept or null",
  "scene": "extracted scene/place or null",
  "people": ["names of people or null"],
  "time": "extracted time of day or null",
  "visual_details": "extracted visual description or null",
  "confidence": {
    "location": 0.0,
    "event": 0.0,
    "scene": 0.0,
    "people": 0.0,
    "time": 0.0,
    "visual_details": 0.0
  }
}
"""


REFINEMENT_QUESTION_PROMPT = """You are an AI memory refinement assistant.
A user is searching through a candidate pool of photos. The candidate photos are most clearly split across the dimension: '{dimension}'.
Distribution of candidates across options: {candidate_summary}.

Formulate a single friendly, conversational clarifying question to ask the user, with 2 to 4 concise options.
Always include "Not sure" as the final option.
Output MUST be valid JSON:
{
  "dimension": "{dimension}",
  "question": "Conversational question to ask the user",
  "options": ["Option 1", "Option 2", "Not sure"]
}
"""


class GeminiProvider:
    """Interacts with the Google Gemini Multimodal Model using Google GenAI SDK."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self._client = None

        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google GenAI client with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}")

    def is_available(self) -> bool:
        """Check if live Gemini API is configured."""
        return self._client is not None

    async def describe_image(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """Send raw image bytes to Gemini Multimodal Model to generate metadata."""
        if not self._client:
            raise RuntimeError("Gemini API client is not configured or missing GEMINI_API_KEY.")

        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                IMAGE_DESCRIPTION_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        return json.loads(response.text)

    async def parse_memory(self, user_memory: str) -> Dict[str, Any]:
        """Parse vague user recollection into structured retrieval clues."""
        if not self._client:
            raise RuntimeError("Gemini API client is not configured or missing GEMINI_API_KEY.")

        from google.genai import types

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[
                f"{MEMORY_PARSING_PROMPT}\n\nUser Vague Memory: \"{user_memory}\"",
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return json.loads(response.text)

    async def generate_refinement_question(self, dimension: str, candidate_summary: Dict[str, int]) -> Dict[str, Any]:
        """Generate conversational refinement question based on candidate distribution."""
        if not self._client:
            raise RuntimeError("Gemini API client is not configured or missing GEMINI_API_KEY.")

        from google.genai import types

        prompt = REFINEMENT_QUESTION_PROMPT.format(
            dimension=dimension,
            candidate_summary=json.dumps(candidate_summary),
        )

        response = self._client.models.generate_content(
            model=self.model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )
        return json.loads(response.text)


# Global singleton instance
gemini_provider = GeminiProvider()
