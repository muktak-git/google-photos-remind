import os
import sys
import json
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.config import settings
from app.providers.database import init_db, SessionLocal
from app.models.database import PhotoRecord
from app.providers.vectorstore import vector_store
from app.providers.embedding import EmbeddingProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SEED_META_FILE = PROJECT_ROOT / "data" / "seed_metadata.json"


def run_indexing(batch_size: int = 50):
    """Run offline indexing pipeline: load metadata, insert SQLite, embed, and store in ChromaDB."""
    logger.info("Starting Offline Library Indexing Pipeline...")

    # Ensure DB tables exist
    init_db()

    if not SEED_META_FILE.exists():
        logger.error(f"Seed metadata file not found at {SEED_META_FILE}. Run seed_test_data.py first.")
        sys.exit(1)

    with open(SEED_META_FILE, "r", encoding="utf-8") as f:
        photos_data = json.load(f)

    total_photos = len(photos_data)
    logger.info(f"Loaded {total_photos} photo records to index.")

    embedding_provider = EmbeddingProvider()
    db = SessionLocal()

    try:
        # Recreate collection to ensure embedding dimension matches
        try:
            vector_store.client.delete_collection("photo_embeddings")
        except Exception:
            pass
        vector_store.collection = vector_store.client.get_or_create_collection(
            name="photo_embeddings",
            metadata={"hnsw:space": "cosine"}
        )

        # Step 1: Store/Update metadata in SQLite
        logger.info("Upserting metadata records into SQLite database...")
        for p in photos_data:
            existing = db.query(PhotoRecord).filter_by(photo_id=p["photo_id"]).first()
            if not existing:
                record = PhotoRecord(
                    photo_id=p["photo_id"],
                    file_path=p["file_path"],
                    thumbnail_path=p["thumbnail_path"],
                    date_taken=p.get("date_taken"),
                    location=p.get("location"),
                    people=json.dumps(p.get("people", [])),
                    event=p.get("event"),
                    scene=json.dumps(p.get("scene", [])),
                    objects=json.dumps(p.get("objects", [])),
                    visual_description=p.get("visual_description", ""),
                    ocr_text=p.get("ocr_text", ""),
                    setting=p.get("setting"),
                    time_of_day=p.get("time_of_day"),
                )
                db.add(record)
        db.commit()
        logger.info(f"SQLite metadata upsert complete. Total DB photos: {db.query(PhotoRecord).count()}")

        # Step 2: Generate combined text representations & Embeddings for ChromaDB
        logger.info("Generating combined text representations and vector embeddings...")
        all_ids = []
        all_docs = []
        all_metas = []

        for p in photos_data:
            photo_id = p["photo_id"]
            scene_str = ", ".join(p.get("scene", []))
            objects_str = ", ".join(p.get("objects", []))
            people_str = ", ".join(p.get("people", [])) or "none"
            location = p.get("location", "")
            event = p.get("event", "")
            vis_desc = p.get("visual_description", "")
            ocr = p.get("ocr_text", "")
            setting = p.get("setting", "")
            time_of_day = p.get("time_of_day", "")

            # Unified combined text representation per architecture spec (§9)
            doc_text = (
                f"{vis_desc}. Setting: {setting}, {scene_str}. Objects: {objects_str}. "
                f"People: {people_str}. Location: {location}. Event: {event}. "
                f"Time: {time_of_day}. Text in image: {ocr}."
            )

            all_ids.append(photo_id)
            all_docs.append(doc_text)
            all_metas.append({
                "photo_id": photo_id,
                "location": location,
                "event": event,
                "setting": setting,
                "time_of_day": time_of_day,
                "people_count": len(p.get("people", [])),
            })

        # Process embeddings in batches
        for i in range(0, total_photos, batch_size):
            batch_ids = all_ids[i: i + batch_size]
            batch_docs = all_docs[i: i + batch_size]
            batch_metas = all_metas[i: i + batch_size]

            logger.info(f"Embedding batch {i // batch_size + 1}/{(total_photos + batch_size - 1) // batch_size} ({len(batch_ids)} photos)...")
            batch_embeddings = embedding_provider.embed_batch(batch_docs)

            vector_store.upsert_photos(
                photo_ids=batch_ids,
                embeddings=batch_embeddings,
                metadatas=batch_metas,
                documents=batch_docs,
            )

        logger.info(f"Indexing successfully finished! Total ChromaDB vectors: {vector_store.count()}")

    finally:
        db.close()


if __name__ == "__main__":
    run_indexing()
