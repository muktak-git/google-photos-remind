import json
from typing import Optional, List
from fastapi import APIRouter, Query
from sqlalchemy.orm import Session

from app.providers.database import SessionLocal
from app.models.database import PhotoRecord

router = APIRouter(prefix="/api/library", tags=["Library"])

CLUSTER_INFO = [
    {
        "id": "all",
        "title": "All Photos",
        "subtitle": "Complete timeline",
        "icon": "photo_library",
    },
    {
        "id": "rajasthan_trip",
        "title": "Rajasthan Heritage Tour",
        "subtitle": "Jaipur & Udaipur Palaces",
        "location": "Rajasthan",
        "icon": "fort",
    },
    {
        "id": "coorg_friends_trip",
        "title": "Coorg Friends Getaway",
        "subtitle": "Coffee Estate & Campfire",
        "location": "Coorg",
        "icon": "fireplace",
    },
    {
        "id": "kids_playing_water",
        "title": "Summer Pool Party",
        "subtitle": "Waterpark & Splash Pool",
        "location": "Bangalore",
        "icon": "pool",
    },
    {
        "id": "bangalore_weekend",
        "title": "Bangalore Weekend",
        "subtitle": "Cafes & Microbreweries",
        "location": "Bangalore",
        "icon": "local_cafe",
    },
    {
        "id": "college_event",
        "title": "Annual Cultural Fest",
        "subtitle": "Auditorium & Stage",
        "location": "College Campus",
        "icon": "theater_comedy",
    },
    {
        "id": "medical_docs",
        "title": "Medical Records",
        "subtitle": "Prescriptions & Reports",
        "location": "City Clinic",
        "icon": "prescriptions",
    },
]


@router.get("")
async def get_photo_library(
    cluster: Optional[str] = Query(None, description="Filter by cluster ID (e.g. rajasthan_trip)"),
    limit: int = Query(60, ge=1, le=200, description="Max photos to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """Retrieve photos from the library with thumbnail URLs, metadata, and cluster groupings."""
    db: Session = SessionLocal()
    try:
        query = db.query(PhotoRecord)

        if cluster and cluster != "all":
            # Map cluster to location or photo_id prefix
            prefix_map = {
                "rajasthan_trip": "raj",
                "coorg_friends_trip": "coorg",
                "kids_playing_water": "water_kids",
                "bangalore_weekend": "blr",
                "college_event": "col",
                "medical_docs": "med",
                "distractors": "dist",
            }
            prefix = prefix_map.get(cluster)
            if prefix:
                query = query.filter(PhotoRecord.photo_id.like(f"{prefix}%"))

        total = query.count()
        if not cluster or cluster == "all":
            from sqlalchemy.sql import func
            records = query.order_by(func.random()).offset(offset).limit(limit).all()
        else:
            records = query.order_by(PhotoRecord.date_taken.desc(), PhotoRecord.photo_id.asc()).offset(offset).limit(limit).all()

        photos = []
        for r in records:
            photos.append({
                "photo_id": r.photo_id,
                "thumbnail_url": f"/photos/thumbnails/{r.photo_id}.jpg",
                "full_url": f"/{r.file_path.replace('\\', '/')}",
                "date": r.date_taken,
                "location": r.location,
                "event": r.event,
                "time_of_day": r.time_of_day,
                "setting": r.setting,
                "visual_description": r.visual_description,
                "scene": json.loads(r.scene) if r.scene else [],
                "people": json.loads(r.people) if r.people else [],
            })

        return {
            "total": total,
            "clusters": CLUSTER_INFO,
            "photos": photos,
            "limit": limit,
            "offset": offset,
        }
    finally:
        db.close()
