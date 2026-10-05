import os
import sys
import json
import shutil
import logging
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.providers.database import init_db, SessionLocal
from app.models.database import PhotoRecord
from app.providers.vectorstore import vector_store
from app.providers.embedding import EmbeddingProvider

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

EXTRA_PHOTOS_DIR = PROJECT_ROOT / "extraPhotos"
TARGET_PHOTOS_DIR = PROJECT_ROOT / "data" / "photos" / "extra_photos"
THUMBNAILS_DIR = PROJECT_ROOT / "data" / "photos" / "thumbnails"
SEED_META_FILE = PROJECT_ROOT / "data" / "seed_metadata.json"

EXTRA_METADATA = [
    {
        "filename": "Coorg-Cafe.avif",
        "photo_id": "extra_coorg_cafe_01",
        "location": "Coorg",
        "date_taken": "2024-12-25",
        "time_of_day": "day",
        "setting": "mixed",
        "event": "Christmas in Coorg",
        "scene": ["cafe", "coffee estate", "homestay", "veranda", "outdoor terrace"],
        "objects": ["coffee mug", "wooden bench", "bistro table", "brass lamp", "garden umbrella"],
        "people": ["Rohan", "Ananya"],
        "visual_description": "A charming boutique outdoor cafe in Coorg nestled amidst lush coffee plantations with wooden veranda seating and fresh coffee mugs on bistro tables.",
        "ocr_text": "Coorg Coffee Brews",
    },
    {
        "filename": "naste cafe at coorg.avif",
        "photo_id": "extra_coorg_cafe_02",
        "location": "Coorg",
        "date_taken": "2024-12-26",
        "time_of_day": "day",
        "setting": "indoor",
        "event": "Coorg Trip",
        "scene": ["cafe", "homestay", "coffee lounge", "indoor", "veranda"],
        "objects": ["coffee table", "plantation mugs", "armchair", "wooden veranda", "coffee cup"],
        "people": ["Priya", "Vikram", "Sneha"],
        "visual_description": "Cosy rustic cafe and homestay lounge in Coorg surrounded by lush greenery, featuring wooden veranda armchairs and warm coffee mugs.",
        "ocr_text": "Estate Coffee Coorg",
    },
    {
        "filename": "breakfast at cafe.avif",
        "photo_id": "extra_breakfast_cafe_03",
        "location": "Coorg",
        "date_taken": "2024-12-27",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Holiday Breakfast",
        "scene": ["cafe", "breakfast table", "outdoor patio", "garden"],
        "objects": ["breakfast plate", "coffee cup", "croissant", "outdoor table", "garden umbrella"],
        "people": ["Ananya", "Rohan"],
        "visual_description": "Morning breakfast spread at an open-air garden cafe with fresh brewed coffee, breakfast plates, and sunny outdoor seating.",
        "ocr_text": "Fresh Brew Breakfast",
    },
    {
        "filename": "friends having coffee in cafe.webp",
        "photo_id": "extra_friends_coffee_04",
        "location": "Coorg",
        "date_taken": "2024-12-28",
        "time_of_day": "evening",
        "setting": "indoor",
        "event": "Reunion with Friends",
        "scene": ["cafe", "coffee lounge", "homestay", "with friends"],
        "objects": ["coffee mugs", "wooden table", "chairs", "bistro table"],
        "people": ["Rohan", "Vikram", "Sneha", "Ananya"],
        "visual_description": "Group of smiling friends gathering together enjoying warm coffee mugs and conversation at a cozy cafe table.",
        "ocr_text": "Best Memories with Friends",
    },
    {
        "filename": "coffee plant at coorg.jpg",
        "photo_id": "extra_coorg_coffee_plant_05",
        "location": "Coorg",
        "date_taken": "2024-12-29",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Plantation Walk",
        "scene": ["coffee estate", "nature", "plantation walk", "outdoor"],
        "objects": ["coffee berries", "coffee plants", "green leaves", "coffee branch"],
        "people": [],
        "visual_description": "Close-up shot of vibrant red and green coffee berries growing on lush coffee plants during a plantation tour in Coorg.",
        "ocr_text": "",
    },
    {
        "filename": "coffee plantation at coorg.webp",
        "photo_id": "extra_coorg_plantation_06",
        "location": "Coorg",
        "date_taken": "2024-12-30",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Coorg Hills",
        "scene": ["coffee estate", "misty hills", "plantation", "nature", "outdoor"],
        "objects": ["coffee trees", "misty hills", "lush greenery", "pathway"],
        "people": [],
        "visual_description": "Expansive scenic view of a sprawling coffee plantation in Coorg with misty green hills and towering silver oak trees.",
        "ocr_text": "Coorg Coffee Estates",
    },
    {
        "filename": "mysore palace.jpg",
        "photo_id": "extra_mysore_palace_07",
        "location": "Mysore",
        "date_taken": "2024-10-15",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Mysore Tour",
        "scene": ["palace", "royal architecture", "heritage", "durbar hall", "palace courtyard"],
        "objects": ["carved arches", "palace facade", "domes", "courtyard fountain", "grand pillars"],
        "people": ["Rohan", "Priya"],
        "visual_description": "The majestic grand facade of Mysore Palace featuring ornate domes, intricate royal arches, and sprawling palace courtyards.",
        "ocr_text": "Mysore Palace",
    },
    {
        "filename": "jaipur palace with pegion.webp",
        "photo_id": "extra_jaipur_palace_08",
        "location": "Rajasthan",
        "date_taken": "2024-11-12",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Rajasthan Heritage Tour",
        "scene": ["palace", "fort", "courtyard", "heritage", "pigeons"],
        "objects": ["palace courtyard", "carved arches", "pigeons flying", "stone pillars", "jharokha"],
        "people": ["Vikram"],
        "visual_description": "Historic royal palace courtyard in Jaipur Rajasthan with pigeons flocking around intricately carved sandstone arches and jharokhas.",
        "ocr_text": "Jaipur Heritage",
    },
    {
        "filename": "taj mahal palace.jpg",
        "photo_id": "extra_taj_palace_09",
        "location": "Rajasthan",
        "date_taken": "2024-11-14",
        "time_of_day": "evening",
        "setting": "outdoor",
        "event": "Heritage Palace Visit",
        "scene": ["palace", "luxury heritage hotel", "illuminated facade", "courtyard"],
        "objects": ["illuminated facade", "grand entrance", "fountain", "domes", "arches"],
        "people": ["Rohan", "Ananya"],
        "visual_description": "Stunning illuminated facade of a heritage grand palace illuminated under the night sky with grand domes and reflection fountain.",
        "ocr_text": "The Grand Palace",
    },
    {
        "filename": "kids in pool.jpg",
        "photo_id": "extra_kids_in_pool_10",
        "location": "Bangalore",
        "date_taken": "2024-05-20",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Summer Holiday",
        "scene": ["swimming pool", "kids playing", "water splash", "summer pool party"],
        "objects": ["swimming pool", "water splashes", "pool floats", "sun loungers"],
        "people": ["Aarav", "Riya"],
        "visual_description": "Children happily splashing and laughing in the resort swimming pool on a bright sunny summer afternoon.",
        "ocr_text": "",
    },
    {
        "filename": "kids plaing in water.webp",
        "photo_id": "extra_kids_playing_water_11",
        "location": "Bangalore",
        "date_taken": "2024-05-22",
        "time_of_day": "day",
        "setting": "outdoor",
        "event": "Water Park Day",
        "scene": ["swimming pool", "kids playing in water", "water park splash", "inflatable float"],
        "objects": ["inflatable float", "water splash", "colorful pool floats", "water slide"],
        "people": ["Aarav", "Kabir", "Riya"],
        "visual_description": "Kids playing and splashing water with colorful inflatable floats and water games in the swimming pool.",
        "ocr_text": "Splash Fun",
    },
]


def add_extra_photos():
    """Copy extra photos, generate thumbnails, update metadata, and index to DB and ChromaDB."""
    init_db()
    TARGET_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load existing seed metadata
    with open(SEED_META_FILE, "r", encoding="utf-8") as f:
        seed_data = json.load(f)
    existing_ids = {p["photo_id"] for p in seed_data}

    new_records_data = []

    # 2. Process each photo
    for meta in EXTRA_METADATA:
        src_path = EXTRA_PHOTOS_DIR / meta["filename"]
        if not src_path.exists():
            logger.warning(f"File not found: {src_path}")
            continue

        dest_filename = f"{meta['photo_id']}_{meta['filename'].replace(' ', '_')}"
        dest_path = TARGET_PHOTOS_DIR / dest_filename
        shutil.copy2(src_path, dest_path)

        # Generate thumbnail
        thumb_path = THUMBNAILS_DIR / f"{meta['photo_id']}.jpg"
        try:
            with Image.open(src_path) as img:
                img_rgb = img.convert("RGB")
                img_rgb.thumbnail((400, 400), Image.Resampling.LANCZOS)
                img_rgb.save(thumb_path, "JPEG", quality=85)
                logger.info(f"Generated thumbnail: {thumb_path.name}")
        except Exception as e:
            logger.error(f"Failed to generate thumbnail for {src_path}: {e}")

        photo_record = {
            "photo_id": meta["photo_id"],
            "file_path": f"data/photos/extra_photos/{dest_filename}",
            "thumbnail_path": f"data/photos/thumbnails/{meta['photo_id']}.jpg",
            "date_taken": meta["date_taken"],
            "location": meta["location"],
            "people": meta["people"],
            "event": meta["event"],
            "scene": meta["scene"],
            "objects": meta["objects"],
            "visual_description": meta["visual_description"],
            "ocr_text": meta["ocr_text"],
            "setting": meta["setting"],
            "time_of_day": meta["time_of_day"],
        }
        new_records_data.append(photo_record)

        if meta["photo_id"] not in existing_ids:
            seed_data.append(photo_record)
            existing_ids.add(meta["photo_id"])

    # 3. Save updated seed metadata
    with open(SEED_META_FILE, "w", encoding="utf-8") as f:
        json.dump(seed_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated seed metadata file with {len(new_records_data)} extra photos. Total: {len(seed_data)}")

    # 4. Insert/Upsert into SQLite
    db = SessionLocal()
    try:
        for p in new_records_data:
            existing = db.query(PhotoRecord).filter_by(photo_id=p["photo_id"]).first()
            if existing:
                existing.file_path = p["file_path"]
                existing.thumbnail_path = p["thumbnail_path"]
                existing.date_taken = p["date_taken"]
                existing.location = p["location"]
                existing.people = json.dumps(p["people"])
                existing.event = p["event"]
                existing.scene = json.dumps(p["scene"])
                existing.objects = json.dumps(p["objects"])
                existing.visual_description = p["visual_description"]
                existing.ocr_text = p["ocr_text"]
                existing.setting = p["setting"]
                existing.time_of_day = p["time_of_day"]
            else:
                record = PhotoRecord(
                    photo_id=p["photo_id"],
                    file_path=p["file_path"],
                    thumbnail_path=p["thumbnail_path"],
                    date_taken=p["date_taken"],
                    location=p["location"],
                    people=json.dumps(p["people"]),
                    event=p["event"],
                    scene=json.dumps(p["scene"]),
                    objects=json.dumps(p["objects"]),
                    visual_description=p["visual_description"],
                    ocr_text=p["ocr_text"],
                    setting=p["setting"],
                    time_of_day=p["time_of_day"],
                )
                db.add(record)
        db.commit()
        total_db = db.query(PhotoRecord).count()
        logger.info(f"SQLite upsert complete. Total photos in DB: {total_db}")
    finally:
        db.close()

    # 5. Index into ChromaDB
    emb = EmbeddingProvider()
    docs = []
    ids = []
    metas = []

    for p in new_records_data:
        scene_str = ", ".join(p.get("scene", []))
        objects_str = ", ".join(p.get("objects", []))
        people_str = ", ".join(p.get("people", [])) or "none"
        doc_text = (
            f"{p['visual_description']}. Setting: {p['setting']}, {scene_str}. "
            f"Objects: {objects_str}. People: {people_str}. Location: {p['location']}. "
            f"Event: {p['event']}. Time: {p['time_of_day']}. Text in image: {p['ocr_text']}."
        )
        docs.append(doc_text)
        ids.append(p["photo_id"])
        metas.append({
            "photo_id": p["photo_id"],
            "location": p["location"],
            "event": p["event"],
            "setting": p["setting"],
            "time_of_day": p["time_of_day"],
            "people_count": len(p["people"]),
        })

    embeddings = emb.embed_batch(docs)
    vector_store.upsert_photos(
        photo_ids=ids,
        embeddings=embeddings,
        metadatas=metas,
        documents=docs,
    )
    logger.info(f"ChromaDB upsert complete. Total vector count: {vector_store.count()}")


if __name__ == "__main__":
    add_extra_photos()
