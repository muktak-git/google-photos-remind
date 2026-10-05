from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)


class VectorStoreProvider:
    """High-performance vector search provider supporting both lightweight NumPy

    in-memory indexing (for serverless/Vercel) and ChromaDB persistent storage.
    """

    def __init__(self):
        self._use_numpy = False
        self.ids: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.documents: List[str] = []
        self.client = None
        self.collection = None

        # Check for pre-indexed compressed embeddings first (lightweight serverless)
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        npz_path = project_root / "data" / "embeddings.npz"

        if npz_path.exists():
            try:
                data = np.load(npz_path, allow_pickle=True)
                self.ids = [str(x) for x in data["ids"]]
                self.embeddings = np.array(data["embeddings"], dtype=np.float32)
                self.documents = [str(x) for x in data["documents"]] if "documents" in data else []
                self._use_numpy = True
                logger.info(f"Loaded {len(self.ids)} photo embeddings into NumPy vector store.")
                return
            except Exception as e:
                logger.warning(f"Could not load embeddings.npz: {e}. Falling back to ChromaDB.")

        # Fallback to ChromaDB if available
        try:
            import os
            import shutil
            import chromadb

            if os.environ.get("VERCEL"):
                persist_path = Path("/tmp/chroma")
                if not persist_path.exists():
                    source_chroma = project_root / settings.CHROMA_PERSIST_DIR
                    if source_chroma.exists():
                        shutil.copytree(source_chroma, persist_path, dirs_exist_ok=True)
            else:
                persist_path = Path(settings.CHROMA_PERSIST_DIR)
                if not persist_path.is_absolute():
                    persist_path = project_root / settings.CHROMA_PERSIST_DIR
            persist_path.mkdir(parents=True, exist_ok=True)

            self.client = chromadb.PersistentClient(path=str(persist_path))
            self.collection_name = "photo_embeddings"
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as e:
            logger.warning(f"ChromaDB initialization unavailable: {e}")

    def count(self) -> int:
        """Return total number of vectors in collection."""
        if self._use_numpy:
            return len(self.ids)
        if self.collection:
            return self.collection.count()
        return 0

    def upsert_photos(
        self,
        photo_ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        documents: List[str],
    ) -> None:
        """Batch upsert photos into vector store."""
        if self.collection:
            sanitized_metadatas = []
            for meta in metadatas:
                clean_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif isinstance(v, list):
                        clean_meta[k] = ", ".join(str(item) for item in v)
                    elif v is None:
                        clean_meta[k] = ""
                    else:
                        clean_meta[k] = str(v)
                sanitized_metadatas.append(clean_meta)

            self.collection.upsert(
                ids=photo_ids,
                embeddings=embeddings,
                metadatas=sanitized_metadatas,
                documents=documents,
            )

        # Update in-memory NumPy store as well
        new_emb = np.array(embeddings, dtype=np.float32)
        if self.embeddings is not None and len(self.embeddings) > 0:
            self.ids.extend(photo_ids)
            self.embeddings = np.vstack([self.embeddings, new_emb])
            self.documents.extend(documents)
        else:
            self.ids = list(photo_ids)
            self.embeddings = new_emb
            self.documents = list(documents)
            self._use_numpy = True

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 20,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform cosine similarity vector search with optional metadata filter."""
        if self._use_numpy and self.embeddings is not None and len(self.embeddings) > 0:
            query_vec = np.array(query_embedding, dtype=np.float32)
            q_norm = np.linalg.norm(query_vec)
            if q_norm > 1e-9:
                query_vec = query_vec / q_norm

            emb_norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            emb_norms = np.where(emb_norms > 1e-9, emb_norms, 1.0)
            norm_embs = self.embeddings / emb_norms

            sims = np.dot(norm_embs, query_vec)
            distances = np.maximum(0.0, 1.0 - sims)

            top_n = min(n_results, len(self.ids))
            top_indices = np.argsort(distances)[:top_n]

            return {
                "ids": [[self.ids[i] for i in top_indices]],
                "distances": [[float(distances[i]) for i in top_indices]],
                "documents": [[self.documents[i] if i < len(self.documents) else "" for i in top_indices]],
                "metadatas": [[{} for _ in top_indices]],
            }

        if self.collection:
            kwargs: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, max(self.count(), 1)),
            }
            if where_filter:
                kwargs["where"] = where_filter
            return self.collection.query(**kwargs)

        return {"ids": [[]], "distances": [[]], "documents": [[]], "metadatas": [[]]}


# Global singleton instance
vector_store = VectorStoreProvider()
