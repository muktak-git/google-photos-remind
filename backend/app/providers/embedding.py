import re
import math
import hashlib
import logging
from typing import List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Provides vector embeddings using Google GenAI (text-embedding-004) or fast local semantic hashing."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.EMBEDDING_MODEL
        self.provider = getattr(settings, "EMBEDDING_PROVIDER", "local").lower()
        self._genai_client = None

        if self.provider == "gemini" and self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Google GenAI embedding client ({self.model_name})")
            except Exception as e:
                logger.warning(f"Could not initialize GenAI client: {e}. Using local fallback.")

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text query or document."""
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a batch of text documents."""
        if self.provider == "gemini" and self._genai_client:
            try:
                result = self._genai_client.models.embed_content(
                    model=self.model_name,
                    contents=texts,
                )
                if hasattr(result, "embeddings"):
                    return [emb.values for emb in result.embeddings]
            except Exception as e:
                logger.warning(f"Google embedding API error: {e}. Falling back to fast local embeddings.")

        # High-performance, deterministic semantic n-gram feature hashing fallback (3072-dim normalized)
        return [self._semantic_hash_vector(t) for t in texts]

    def _semantic_hash_vector(self, text: str, dim: int = 3072) -> List[float]:
        """Compute a deterministic 3072-dimensional normalized vector capturing tokens and character n-grams."""
        tokens = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
        vec = [0.0] * dim

        if not tokens:
            return [1.0 / math.sqrt(dim)] * dim

        for token in tokens:
            # Word-level feature
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % dim
            vec[idx] += 2.0

            # Character 3-gram features for fuzzy morphological matching
            if len(token) >= 3:
                for j in range(len(token) - 2):
                    ngram = token[j : j + 3]
                    n_idx = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:8], 16) % dim
                    vec[n_idx] += 0.5

        # L2-normalization to ensure cosine similarity is valid dot-product
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            return [v / norm for v in vec]
        return [1.0 / math.sqrt(dim)] * dim
