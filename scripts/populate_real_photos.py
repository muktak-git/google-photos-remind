import io
import os
import random
import urllib.request
from pathlib import Path
from PIL import Image, ImageEnhance

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHOTO_DIR = PROJECT_ROOT / "data" / "photos"
THUMBNAIL_DIR = PHOTO_DIR / "thumbnails"
CACHE_DIR = PROJECT_ROOT / "data" / "cache_source_photos"

# Curated, verified royalty-free high quality photography from Unsplash
PHOTO_BANK = {
    "rajasthan_palace": [
        "https://images.unsplash.com/photo-1599661046289-e31897846e41", # Jaipur City Palace
        "https://images.unsplash.com/photo-1597848212624-a19eb35e2651", # Amer Fort Arches
        "https://images.unsplash.com/photo-1609137144822-0d127c5950d2", # Hawa Mahal Palace
        "https://images.unsplash.com/photo-1598890777032-bde835ba27c2", # Mehrangarh Fort Courtyard
        "https://images.unsplash.com/photo-1582510003544-4d00b7f74220", # Udaipur Lake Palace
    ],
    "rajasthan_desert": [
        "https://images.unsplash.com/photo-1506461883276-594a12b11cf3", # Thar desert camel
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23", # Sand dunes
        "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9", # Desert sunset
    ],
    "coorg_friends_trip": [
        "https://images.unsplash.com/photo-1510312305653-8ed496efae75", # Bonfire campfire night
        "https://images.unsplash.com/photo-1478131143081-80f7f84ca84d", # Campfire group
        "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4", # Campfire tent
        "https://images.unsplash.com/photo-1526772662000-3f88f10405ff", # Nature trail
        "https://images.unsplash.com/photo-1501785888041-af3ef285b470", # Misty hills
        "https://images.unsplash.com/photo-1533240332313-0db49b459ad6", # Green hills estate
    ],
    "kids_playing_water": [
        "https://images.unsplash.com/photo-1533227268428-f9ed0900fb3b", # Pool splash
        "https://images.unsplash.com/photo-1566737236500-c8ac43014a67", # Pool fun
        "https://images.unsplash.com/photo-1502086223501-7ea6ecd79368", # Kids water fun
        "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7", # Summer pool
        "https://images.unsplash.com/photo-1516627145497-ae6968895b74", # Laughing pool
    ],
    "bangalore_weekend": [
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4", # Cafe restaurant
        "https://images.unsplash.com/photo-1554118811-1e0d58224f24", # Coffee table
        "https://images.unsplash.com/photo-1572116469696-31de0f17cc34", # Beer mugs brewery
        "https://images.unsplash.com/photo-1528605248644-14dd04022da1", # Friends dining
        "https://images.unsplash.com/photo-1559925393-8be0ec4767c8", # Cafe lights
    ],
    "college_event": [
        "https://images.unsplash.com/photo-1511578314322-379afb476865", # Stage lights
        "https://images.unsplash.com/photo-1492684223066-81342ee5ff30", # Fest event
        "https://images.unsplash.com/photo-1523580494863-6f3031224c94", # Students laughing
        "https://images.unsplash.com/photo-1540575467063-178a50c2df87", # Auditorium stage
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655", # Campus fest
    ],
    "medical_docs": [
        "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982", # Rx stethoscope
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef", # Medical report
        "https://images.unsplash.com/photo-1583912267670-6575ad3726f9", # Clinic notes
    ],
    "distractors": [
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05", # Fog nature
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab", # City architecture
        "https://images.unsplash.com/photo-1501854140801-50d01698950b", # Forest green
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86", # Nature trees
        "https://images.unsplash.com/photo-1517841905240-472988babdf9", # People
    ]
}


def download_source_images():
    """Download and cache base photographs."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached_images = {}

    for category, urls in PHOTO_BANK.items():
        cached_images[category] = []
        for idx, base_url in enumerate(urls):
            cache_file = CACHE_DIR / f"{category}_{idx}.jpg"
            if not cache_file.exists():
                full_url = f"{base_url}?w=1200&auto=format&fit=crop&q=85"
                try:
                    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        content = resp.read()
                        with open(cache_file, "wb") as f:
                            f.write(content)
                    print(f"Cached {category}_{idx}.jpg ({len(content)} bytes)")
                except Exception as e:
                    print(f"Failed to fetch {full_url}: {e}")
                    continue

            if cache_file.exists():
                try:
                    img = Image.open(cache_file).convert("RGB")
                    cached_images[category].append(img)
                except Exception as e:
                    print(f"Corrupt cache {cache_file}: {e}")

    return cached_images


def transform_variant(base_img: Image.Image, seed_num: int, time_of_day: str = "day") -> Image.Image:
    """Create a realistic variation with slight cropping and tone adjustment."""
    w, h = base_img.size
    
    # Slight crop variation (zoom up to 8%)
    crop_margin_x = int(w * 0.04)
    crop_margin_y = int(h * 0.04)
    offset_x = (seed_num * 17) % max(1, crop_margin_x)
    offset_y = (seed_num * 13) % max(1, crop_margin_y)

    cropped = base_img.crop((
        offset_x,
        offset_y,
        w - (crop_margin_x - offset_x),
        h - (crop_margin_y - offset_y)
    ))

    # Resize to standard full resolution 800x600
    resized = cropped.resize((800, 600), Image.Resampling.LANCZOS)

    # Lighting / mood adjustment according to time of day
    if time_of_day == "evening":
        # Warm golden dusk tone
        enhancer = ImageEnhance.Color(resized)
        resized = enhancer.enhance(1.15)
        brightener = ImageEnhance.Brightness(resized)
        resized = brightener.enhance(0.92)
    elif time_of_day == "night":
        # Cooler/darker night tone
        brightener = ImageEnhance.Brightness(resized)
        resized = brightener.enhance(0.75)
        contraster = ImageEnhance.Contrast(resized)
        resized = contraster.enhance(1.2)
    else:
        # Daytime vibrant
        brightener = ImageEnhance.Brightness(resized)
        resized = brightener.enhance(1.02)

    return resized


def populate_library():
    """Populate full photo library and thumbnails with authentic photos."""
    print("Fetching and caching authentic base photos from Unsplash...")
    cached_images = download_source_images()

    import json
    metadata_file = PROJECT_ROOT / "data" / "seed_metadata.json"
    with open(metadata_file, "r", encoding="utf-8") as f:
        metadata_list = json.load(f)

    print(f"Applying authentic photos across {len(metadata_list)} photo library entries...")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

    for idx, item in enumerate(metadata_list):
        photo_id = item["photo_id"]
        rel_file_path = item["file_path"]
        time_of_day = item.get("time_of_day", "day")
        full_dest = PROJECT_ROOT / rel_file_path
        thumb_dest = THUMBNAIL_DIR / f"{photo_id}.jpg"
        full_dest.parent.mkdir(parents=True, exist_ok=True)

        # Select matching category
        if photo_id.startswith("raj_palace"):
            pool = cached_images.get("rajasthan_palace", [])
        elif photo_id.startswith("raj_"):
            pool = cached_images.get("rajasthan_desert", []) or cached_images.get("rajasthan_palace", [])
        elif photo_id.startswith("coorg_"):
            pool = cached_images.get("coorg_friends_trip", [])
        elif photo_id.startswith("water_kids_"):
            pool = cached_images.get("kids_playing_water", [])
        elif photo_id.startswith("blr_"):
            pool = cached_images.get("bangalore_weekend", [])
        elif photo_id.startswith("col_"):
            pool = cached_images.get("college_event", [])
        elif photo_id.startswith("med_"):
            pool = cached_images.get("medical_docs", [])
        else:
            pool = cached_images.get("distractors", [])

        if not pool:
            # Fallback to any available pool
            pool = next(iter(cached_images.values()), [])

        base_img = pool[idx % len(pool)]
        real_full = transform_variant(base_img, idx, time_of_day)

        # Save 800x600 photo
        real_full.save(full_dest, "JPEG", quality=88, optimize=True)

        # Save 250x250 square thumbnail
        thumb = real_full.resize((250, 250), Image.Resampling.LANCZOS)
        thumb.save(thumb_dest, "JPEG", quality=84, optimize=True)

        if (idx + 1) % 100 == 0 or idx == len(metadata_list) - 1:
            print(f"Processed {idx + 1}/{len(metadata_list)} photos...")

    print("Successfully populated authentic photo library and thumbnails!")


if __name__ == "__main__":
    populate_library()
