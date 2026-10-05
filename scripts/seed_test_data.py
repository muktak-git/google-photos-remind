import os
import json
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Set deterministic random seed
random.seed(42)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = PROJECT_ROOT / "data" / "photos"
THUMBNAIL_DIR = PHOTO_DIR / "thumbnails"
SEED_META_FILE = PROJECT_ROOT / "data" / "seed_metadata.json"

CLUSTERS = [
    {
        "folder": "rajasthan_trip",
        "count": 160,
        "location": "Rajasthan",
        "event": "Rajasthan Heritage Tour",
        "palace_count": 40,  # Dedicated palace series
        "base_color": (218, 142, 60),  # Warm amber/sandstone
        "people": ["Rahul", "Ananya", "Sneha", "Aditya"],
    },
    {
        "folder": "coorg_friends_trip",
        "count": 120,
        "location": "Coorg",
        "event": "Coorg Friends Getaway",
        "base_color": (46, 125, 50),  # Lush estate green
        "people": ["Rahul", "Sneha", "Aditya", "Priya"],
    },
    {
        "folder": "kids_playing_water",
        "count": 90,
        "location": "Bangalore",
        "event": "Summer Pool Party",
        "base_color": (33, 150, 243),  # Pool aqua blue
        "people": ["Aarav", "Ananya", "Vihaan", "friends"],
    },
    {
        "folder": "bangalore_weekend",
        "count": 100,
        "location": "Bangalore",
        "event": "Weekend Outing",
        "base_color": (121, 85, 72),  # Urban cafe/brewery brown
        "people": ["Karthik", "Rohan", "Meera"],
    },
    {
        "folder": "college_event",
        "count": 80,
        "location": "College Campus",
        "event": "Annual Cultural Fest",
        "base_color": (103, 58, 183),  # Stage purple
        "people": ["Classmates", "Prof. Sharma", "Batch 2024"],
    },
    {
        "folder": "medical_docs",
        "count": 70,
        "location": "City Clinic",
        "event": "Medical Checkup",
        "base_color": (230, 238, 245),  # Hospital light clinical blue
        "people": [],
    },
    {
        "folder": "distractors",
        "count": 120,
        "location": "City Streets",
        "event": "Random Everyday Moments",
        "base_color": (158, 158, 158),  # Neutral gray
        "people": [],
    },
]

TIMES_OF_DAY = ["day", "evening", "night"]
SETTINGS = ["indoor", "outdoor", "mixed"]


def create_gradient_image(width, height, base_rgb, label, subtitle, ocr=""):
    """Create a stylized synthetic photo with gradients, geometric patterns, and visual labels."""
    img = Image.new("RGB", (width, height), base_rgb)
    draw = ImageDraw.Draw(img)

    # Add gradient overlay bands
    for y in range(height):
        factor = y / height
        r = int(base_rgb[0] * (0.7 + 0.6 * factor))
        g = int(base_rgb[1] * (0.7 + 0.5 * factor))
        b = int(base_rgb[2] * (0.7 + 0.4 * factor))
        draw.line([(0, y), (width, y)], fill=(min(255, r), min(255, g), min(255, b)))

    # Decorative shapes (architectural arches, circles, waves)
    draw.rectangle([40, 40, width - 40, height - 40], outline=(255, 255, 255, 120), width=3)
    draw.ellipse([width // 2 - 80, height // 2 - 80, width // 2 + 80, height // 2 + 80], outline=(255, 255, 255, 80), width=4)

    # Draw headline and caption text
    draw.text((60, 60), label, fill=(255, 255, 255))
    draw.text((60, 90), subtitle, fill=(240, 240, 240))

    if ocr:
        draw.rectangle([width - 240, height - 80, width - 50, height - 45], fill=(0, 0, 0, 160))
        draw.text((width - 230, height - 70), f"TXT: {ocr}", fill=(255, 255, 100))

    return img


def generate_dataset():
    print(f"Generating synthetic photos and metadata in {PHOTO_DIR}...")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    all_metadata = []
    total_generated = 0

    for cluster in CLUSTERS:
        folder = cluster["folder"]
        count = cluster["count"]
        location = cluster["location"]
        event = cluster["event"]
        base_color = cluster["base_color"]
        cluster_dir = PHOTO_DIR / folder
        cluster_dir.mkdir(parents=True, exist_ok=True)

        palace_count = cluster.get("palace_count", 0)

        for i in range(1, count + 1):
            total_generated += 1
            is_palace = (folder == "rajasthan_trip" and i <= palace_count)
            time_of_day = random.choice(TIMES_OF_DAY)
            setting = random.choice(SETTINGS)

            if is_palace:
                photo_id = f"raj_palace_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["palace", "courtyard", "heritage", setting]
                objects = ["carved arch", "marble pillar", "courtyard fountain", "royal gate", "stone jali"]
                if time_of_day == "evening":
                    visual_description = (
                        f"Majestic royal palace courtyard in Rajasthan at dusk with illuminated carved sandstone arches, "
                        f"ornate marble pillars, and warm golden lanterns reflecting in the central fountain."
                    )
                elif time_of_day == "night":
                    visual_description = (
                        f"Intricate palace facade at night glowing under floodlights with royal courtyards and star-lit skies."
                    )
                else:
                    visual_description = (
                        f"Grand sunlit courtyard inside Rajasthan palace featuring historic carved pillars, marble balconies, "
                        f"and vibrant decorative arches."
                    )
                ocr_text = "ROYAL PALACE JAIPUR" if i % 2 == 0 else "HERITAGE COURTYARD"
                people = ["Rahul", "Ananya"] if i % 3 == 0 else []

            elif folder == "rajasthan_trip":
                photo_id = f"raj_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["desert", "sand dunes", "fort", "bazaar", setting]
                objects = ["camel", "tent", "sand dune", "handicraft", "turban", "pottery"]
                visual_description = f"Desert landscape and vibrant cultural scene during Rajasthan tour with camels and sand dunes at {time_of_day}."
                ocr_text = "THAR DESERT SAFARI" if i % 4 == 0 else ""
                people = random.sample(cluster["people"], k=random.randint(0, 3))

            elif folder == "coorg_friends_trip":
                photo_id = f"coorg_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["coffee estate", "homestay", "campfire", "waterfall", "misty hills", setting]
                objects = ["campfire", "coffee plants", "guitar", "wooden veranda", "bonfire", "trekking bag"]
                if i == 15 or "campfire" in scene:
                    visual_description = (
                        f"Friends sitting around a cozy evening campfire near the coffee estate homestay veranda in Coorg, "
                        f"enjoying music and misty hills under twilight."
                    )
                    time_of_day = "evening"
                    setting = "outdoor"
                else:
                    visual_description = f"Scenic coffee plantation trail in Coorg surrounded by misty greenery and homestay views at {time_of_day}."
                ocr_text = "COORG ESTATE STAY" if i % 3 == 0 else ""
                people = random.sample(cluster["people"], k=random.randint(1, 4))

            elif folder == "kids_playing_water":
                photo_id = f"water_kids_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["swimming pool", "water park", "garden lawn", "splash pad", setting]
                objects = ["water splash", "pool float", "swim ring", "sprinkler", "beach ball", "goggles"]
                visual_description = (
                    f"Joyful kids playing and splashing in the pool water with friends on a bright sunny day with colorful floats."
                )
                time_of_day = "day"
                setting = "outdoor"
                ocr_text = "SPLASH ZONE" if i % 5 == 0 else ""
                people = random.sample(cluster["people"], k=random.randint(1, 3))

            elif folder == "bangalore_weekend":
                photo_id = f"blr_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["microbrewery", "cafe", "park", "bowling", setting]
                objects = ["craft beer glass", "wooden table", "string lights", "food plate", "board game"]
                visual_description = f"Relaxing weekend hangout at an open-air cafe with string lights in Bangalore at {time_of_day}."
                ocr_text = "TOIT BREWPUB" if i % 4 == 0 else ""
                people = random.sample(cluster["people"], k=random.randint(0, 3))

            elif folder == "college_event":
                photo_id = f"col_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["auditorium", "stage", "canteen", "campus", setting]
                objects = ["stage microphone", "award trophy", "certificate", "banner", "podium"]
                visual_description = f"College cultural fest celebration on stage with students receiving awards and cheering at {time_of_day}."
                ocr_text = "ANNUAL FEST 2024" if i % 3 == 0 else ""
                people = ["Classmates"]

            elif folder == "medical_docs":
                photo_id = f"med_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["clinic", "pharmacy", "desk", setting]
                objects = ["prescription paper", "medicine bottle", "lab report", "stethoscope", "pen"]
                visual_description = f"Medical prescription document with clinic header, doctor's signature, and medication instructions."
                ocr_text = "APOLLO CLINIC RX" if i % 2 == 0 else "DIAGNOSTIC LAB REPORT"
                people = []
                setting = "indoor"

            else:  # distractors
                photo_id = f"dist_{i:03d}"
                filename = f"{photo_id}.jpg"
                scene = ["city street", "abstract", "nature", setting]
                objects = ["bench", "cup", "lamp", "plant", "bicycle"]
                visual_description = f"Everyday scene showing urban details, objects, and ambient light at {time_of_day}."
                ocr_text = ""
                people = []

            # File paths
            file_path = str(cluster_dir / filename)
            rel_file_path = f"data/photos/{folder}/{filename}"
            rel_thumb_path = f"data/photos/thumbnails/{photo_id}.jpg"
            thumb_file_path = str(THUMBNAIL_DIR / f"{photo_id}.jpg")

            # Generate synthetic image (800x600)
            img = create_gradient_image(
                800, 600, base_color,
                label=f"[{folder.upper()}] {photo_id}",
                subtitle=f"{location} | {time_of_day.upper()} | {setting.upper()}",
                ocr=ocr_text,
            )
            img.save(file_path, "JPEG", quality=85)

            # Generate thumbnail (250x250)
            thumb = img.resize((250, 250), Image.Resampling.LANCZOS)
            thumb.save(thumb_file_path, "JPEG", quality=80)

            # Record metadata
            meta = {
                "photo_id": photo_id,
                "file_path": rel_file_path,
                "thumbnail_path": rel_thumb_path,
                "date_taken": f"2025-11-{random.randint(10, 28):02d}",
                "location": location,
                "people": people,
                "event": event,
                "scene": scene,
                "objects": objects,
                "visual_description": visual_description,
                "ocr_text": ocr_text,
                "setting": setting,
                "time_of_day": time_of_day,
            }
            all_metadata.append(meta)

    # Save metadata seed catalog
    with open(SEED_META_FILE, "w", encoding="utf-8") as f:
        json.dump(all_metadata, f, indent=2)

    print(f"Successfully generated {total_generated} photos and thumbnails!")
    print(f"Metadata catalog saved to {SEED_META_FILE}")


if __name__ == "__main__":
    generate_dataset()
