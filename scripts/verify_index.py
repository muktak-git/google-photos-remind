import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.providers.database import SessionLocal
from app.models.database import PhotoRecord
from app.providers.vectorstore import vector_store
from app.providers.embedding import EmbeddingProvider


def verify_library():
    print("==================================================")
    print("       ReMind Index Verification & Sanity Check   ")
    print("==================================================")

    # 1. Database count
    db = SessionLocal()
    db_count = db.query(PhotoRecord).count()
    print(f"1. SQLite 'photos' table total records: {db_count}")
    assert db_count >= 500, f"Expected at least 500 records in SQLite, found {db_count}"

    # 2. ChromaDB count
    chroma_count = vector_store.count()
    print(f"2. ChromaDB 'photo_embeddings' total vectors: {chroma_count}")
    assert chroma_count == db_count, f"Mismatch: SQLite has {db_count} but ChromaDB has {chroma_count}"

    # 3. Test Queries
    embedding_provider = EmbeddingProvider()

    test_queries = [
        {
            "query": "grand palace courtyard in rajasthan with carved arches and pillars",
            "expected_prefix": "raj_palace",
            "desc": "Rajasthan Palace Courtyard Test",
        },
        {
            "query": "friends campfire near coffee estate homestay in coorg with guitar",
            "expected_prefix": "coorg",
            "desc": "Coorg Friends Campfire Test",
        },
        {
            "query": "kids playing and splashing in the pool water with friends",
            "expected_prefix": "water_kids",
            "desc": "Kids Playing in Water Test",
        },
    ]

    print("\n3. Running Semantic Retrieval Tests:")
    for test in test_queries:
        start_time = time.time()
        query_vec = embedding_provider.embed_text(test["query"])
        results = vector_store.query(query_embedding=query_vec, n_results=5)
        elapsed_ms = (time.time() - start_time) * 1000

        retrieved_ids = results["ids"][0] if results and "ids" in results else []
        print(f"\n   Query: '{test['query']}'")
        print(f"   Elapsed Time: {elapsed_ms:.1f} ms (< 500 ms target)")
        print(f"   Top 5 IDs: {retrieved_ids}")

        # Check prefix match in top 5
        matched = any(id_.startswith(test["expected_prefix"]) for id_ in retrieved_ids)
        assert matched, f"Expected ID starting with '{test['expected_prefix']}' in top results!"
        print(f"   Result: PASS (Found '{test['expected_prefix']}' match in top candidates)")

    db.close()
    print("\n==================================================")
    print("   ALL PHASE 1 ACCEPTANCE CRITERIA VERIFIED!     ")
    print("==================================================")


if __name__ == "__main__":
    verify_library()
