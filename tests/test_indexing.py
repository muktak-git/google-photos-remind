import sys
from pathlib import Path

# Add backend and root to sys.path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path / "backend"))

from app.providers.database import SessionLocal
from app.models.database import PhotoRecord
from app.providers.vectorstore import vector_store
from app.providers.embedding import EmbeddingProvider


def test_photo_database_records():
    """Verify photo database records exist and have required fields."""
    db = SessionLocal()
    count = db.query(PhotoRecord).count()
    assert count >= 500, f"Expected at least 500 records, got {count}"

    # Verify a Rajasthan palace record
    palace_record = db.query(PhotoRecord).filter(PhotoRecord.photo_id.like("raj_palace_%")).first()
    assert palace_record is not None
    assert "palace" in palace_record.visual_description.lower()
    assert palace_record.location == "Rajasthan"

    # Verify a Coorg record
    coorg_record = db.query(PhotoRecord).filter(PhotoRecord.photo_id.like("coorg_%")).first()
    assert coorg_record is not None
    assert coorg_record.location == "Coorg"

    # Verify a kids playing in water record
    water_record = db.query(PhotoRecord).filter(PhotoRecord.photo_id.like("water_kids_%")).first()
    assert water_record is not None
    assert "pool" in water_record.visual_description.lower() or "water" in water_record.visual_description.lower()

    db.close()


def test_vectorstore_indexed_count():
    """Verify vector store matches or exceeds the 500 photo requirement."""
    assert vector_store.count() >= 500


def test_semantic_search_accuracy():
    """Verify semantic search retrieves relevant photos with top scores."""
    provider = EmbeddingProvider()

    # Query for palace
    vec = provider.embed_text("royal palace courtyard with marble arches in rajasthan")
    results = vector_store.query(query_embedding=vec, n_results=5)
    assert len(results["ids"][0]) == 5
    assert any(id_.startswith("raj_palace") for id_ in results["ids"][0])
