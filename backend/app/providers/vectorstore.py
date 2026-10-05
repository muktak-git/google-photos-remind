from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.config import settings


class VectorStoreProvider:
    """Manages the persistent ChromaDB collection for photo vector search."""

    def __init__(self):
        import os
        import shutil

        # Resolve persistence path with Vercel serverless support
        if os.environ.get("VERCEL"):
            persist_path = Path("/tmp/chroma")
            if not persist_path.exists():
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                source_chroma = project_root / settings.CHROMA_PERSIST_DIR
                if source_chroma.exists():
                    shutil.copytree(source_chroma, persist_path, dirs_exist_ok=True)
        else:
            persist_path = Path(settings.CHROMA_PERSIST_DIR)
            if not persist_path.is_absolute():
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                persist_path = project_root / settings.CHROMA_PERSIST_DIR
        persist_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection_name = "photo_embeddings"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Return total number of vectors in collection."""
        return self.collection.count()

    def upsert_photos(
        self,
        photo_ids: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        documents: List[str],
    ) -> None:
        """Batch upsert photos into ChromaDB."""
        # Sanitize metadata: ChromaDB only supports str, int, float, bool
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

    def query(
        self,
        query_embedding: List[float],
        n_results: int = 20,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Perform cosine similarity vector search with optional metadata filter."""
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, max(self.count(), 1)),
        }
        if where_filter:
            kwargs["where"] = where_filter

        results = self.collection.query(**kwargs)
        return results


# Global singleton instance
vector_store = VectorStoreProvider()
