import json
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.providers.database import init_db, SessionLocal
from app.models.database import PhotoRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

META_PATH = PROJECT_ROOT / "data" / "seed_metadata.json"

def enrich_coorg():
    with open(META_PATH, "r", encoding="utf-8") as f:
        photos = json.load(f)

    coorg_cafe_blue_wall = [
        "coorg_001", "coorg_002", "coorg_003", "coorg_004", "coorg_005", "coorg_006"
    ]
    coorg_cafe_outdoor = [
        f"coorg_{i:03d}" for i in range(7, 21)
    ]
    coorg_cafe_homestay = [
        f"coorg_{i:03d}" for i in range(21, 39)
    ]

    updated_count = 0
    for p in photos:
        pid = p["photo_id"]
        if pid in coorg_cafe_blue_wall:
            p["visual_description"] = "Charming rustic coffee estate café in Coorg featuring a distinctive vibrant blue wall, warm brass pendant lights, artisanal Coorg filter coffee, and wooden bistro chairs."
            p["objects"] = ["blue wall", "coffee cup", "bistro table", "chair", "brass lamp"]
            p["scene"] = ["cafe", "coffee estate", "indoor", "blue wall"]
            p["date_taken"] = "2025-12-25"
            p["time_of_day"] = "day"
            p["setting"] = "indoor"
            p["location"] = "Coorg"
            p["event"] = "Coorg Vacation"
            updated_count += 1
        elif pid in coorg_cafe_outdoor:
            p["visual_description"] = "Outdoor coffee estate terrace café in Coorg with garden seating overlooking misty plantation hills, blooming coffee plants, and fresh brews."
            p["objects"] = ["outdoor table", "coffee mug", "garden umbrella", "wooden bench"]
            p["scene"] = ["cafe", "outdoor terrace", "coffee estate", "garden"]
            p["date_taken"] = "2025-12-31"
            p["time_of_day"] = "day"
            p["setting"] = "outdoor"
            p["location"] = "Coorg"
            p["event"] = "Coorg Vacation"
            updated_count += 1
        elif pid in coorg_cafe_homestay:
            p["visual_description"] = "Cozy homestay lounge and coffee dining veranda in Coorg near the plantation with wood decor, evening lamps, and homemade snacks."
            p["objects"] = ["coffee table", "veranda", "plantation mugs", "armchair"]
            p["scene"] = ["cafe", "homestay", "veranda", "coffee lounge"]
            p["date_taken"] = "2025-12-28"
            p["time_of_day"] = "evening"
            p["setting"] = "mixed"
            p["location"] = "Coorg"
            p["event"] = "Coorg Vacation"
            updated_count += 1

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2)

    logger.info(f"Updated {updated_count} Coorg cafe photo descriptions in seed_metadata.json")

    # Update SQLite records
    init_db()
    db = SessionLocal()
    try:
        for p in photos:
            if p["photo_id"] in (coorg_cafe_blue_wall + coorg_cafe_outdoor + coorg_cafe_homestay):
                rec = db.query(PhotoRecord).filter_by(photo_id=p["photo_id"]).first()
                if rec:
                    rec.visual_description = p["visual_description"]
                    rec.objects = json.dumps(p["objects"])
                    rec.scene = json.dumps(p["scene"])
                    rec.date_taken = p["date_taken"]
                    rec.time_of_day = p["time_of_day"]
                    rec.setting = p["setting"]
                    rec.location = p["location"]
                    rec.event = p["event"]
        db.commit()
        logger.info("Updated SQLite database records for Coorg cafe photos.")
    finally:
        db.close()

if __name__ == "__main__":
    enrich_coorg()
