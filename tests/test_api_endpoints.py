import sys
from pathlib import Path

# Add backend directory to sys.path
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path / "backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.providers.database import SessionLocal
from app.models.database import SessionRecord, SessionEventRecord

client = TestClient(app)


def test_complete_api_reconstruction_loop():
    """Verify all 5 API endpoints end-to-end through a full memory reconstruction cycle."""

    # 1. Screen 1: Search
    search_payload = {"query": "That grand palace courtyard we visited during our Rajasthan trip"}
    res = client.post("/api/search", json=search_payload)
    assert res.status_code == 201
    search_data = res.json()
    assert "session_id" in search_data
    session_id = search_data["session_id"]
    assert search_data["query"] == search_payload["query"]

    # 2. Screen 2: Understanding
    understand_payload = {"session_id": session_id}
    res = client.post("/api/understand", json=understand_payload)
    assert res.status_code == 200
    under_data = res.json()
    assert under_data["session_id"] == session_id
    assert "clues" in under_data
    assert "chips" in under_data
    assert len(under_data["chips"]) > 0
    assert under_data["clues"]["location"] == "Rajasthan"

    # 3. Screen 3: Initial Candidates (Top 20)
    cand_payload = {"session_id": session_id}
    res = client.post("/api/candidates", json=cand_payload)
    assert res.status_code == 200
    cand_data = res.json()
    assert cand_data["session_id"] == session_id
    assert cand_data["total"] > 0
    assert len(cand_data["candidates"]) <= 20
    assert cand_data["turn"] == 0

    first_photo = cand_data["candidates"][0]
    assert "photo_id" in first_photo
    assert "thumbnail_url" in first_photo
    assert "score" in first_photo
    assert "visual_description" in first_photo

    # 4. Screen 4: Refinement Question Generation
    refine_payload = {"session_id": session_id}
    res = client.post("/api/refine", json=refine_payload)
    assert res.status_code == 200
    refine_data = res.json()
    assert refine_data["session_id"] == session_id
    assert "dimension" in refine_data
    assert "question" in refine_data
    assert len(refine_data["options"]) >= 2
    assert "Not sure" in refine_data["options"]
    assert refine_data["turn"] == 1

    # 5. Screen 3 (Re-rank with user refinement answer)
    selected_option = refine_data["options"][0]
    constrained_payload = {
        "session_id": session_id,
        "constraint": {
            "dimension": refine_data["dimension"],
            "value": selected_option,
        },
    }
    res = client.post("/api/candidates", json=constrained_payload)
    assert res.status_code == 200
    constrained_data = res.json()
    assert constrained_data["turn"] == 1
    assert "banner_message" in constrained_data
    assert constrained_data["total"] > 0

    # 6. Screen 5: Confirm Recognition
    best_candidate_id = constrained_data["candidates"][0]["photo_id"]
    confirm_payload = {
        "session_id": session_id,
        "photo_id": best_candidate_id,
        "confirmed": True,
    }
    res = client.post("/api/confirm", json=confirm_payload)
    assert res.status_code == 200
    confirm_data = res.json()
    assert confirm_data["success"] is True
    assert confirm_data["status"] == "completed"
    assert "metrics" in confirm_data
    assert confirm_data["metrics"]["total_turns"] >= 1
    assert confirm_data["metrics"]["confirmed"] is True

    # 7. Audit log verification in database
    db = SessionLocal()
    session_row = db.query(SessionRecord).filter_by(session_id=session_id).first()
    assert session_row is not None
    assert session_row.status == "completed"

    events = db.query(SessionEventRecord).filter_by(session_id=session_id).all()
    assert len(events) >= 5  # search, understand, retrieve, refine, confirm
    event_types = [e.event_type for e in events]
    assert "search_created" in event_types
    assert "clues_extracted" in event_types
    assert "confirm_photo" in event_types
    db.close()


def test_static_thumbnail_serving():
    """Verify photo thumbnails are delivered over HTTP with 200 status."""
    res = client.get("/photos/thumbnails/raj_palace_001.jpg")
    assert res.status_code == 200
    assert "image" in res.headers.get("content-type", "")


def test_over_constrained_rollback_edge_case():
    """Verify that an impossible constraint triggers rollback rather than dropping to 0 candidates."""
    # 1. Create session and get candidates
    s_res = client.post("/api/search", json={"query": "palace in rajasthan"}).json()
    session_id = s_res["session_id"]
    client.post("/api/candidates", json={"session_id": session_id})

    # 2. Submit an impossible constraint
    impossible_payload = {
        "session_id": session_id,
        "constraint": {
            "dimension": "location",
            "value": "Antarctica Iceberg Glacier",
        },
    }
    res = client.post("/api/candidates", json=impossible_payload)
    assert res.status_code == 200
    data = res.json()
    # Candidate list must NOT be empty due to graceful rollback
    assert data["total"] > 0
    assert "None of those photos matched" in (data.get("banner_message") or "")


def test_frontend_index_serving():
    """Verify that the single-page application frontend is served at root GET /."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    html_text = res.text
    assert "ReMind" in html_text
    assert "Photos" in html_text


def test_library_endpoint():
    """Verify photo library endpoint returns photos and cluster groups."""
    res = client.get("/api/library?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 740
    assert len(data["photos"]) == 10
    assert len(data["clusters"]) >= 5
    first = data["photos"][0]
    assert "thumbnail_url" in first
    assert "full_url" in first
    assert "location" in first


def test_remove_constraint_restores_candidates():
    """Verify that removing a constraint (wrong direction) restores candidates and updates active constraints."""
    res = client.post("/api/search", json={"query": "palace courtyard in Rajasthan"})
    assert res.status_code == 201
    sess_id = res.json()["session_id"]

    res = client.post("/api/candidates", json={"session_id": sess_id})
    assert res.status_code == 200
    initial_total = res.json()["total"]
    assert "matched_reasons" in res.json()["candidates"][0]

    # Apply a constraint
    res = client.post("/api/candidates", json={
        "session_id": sess_id,
        "constraint": {"dimension": "time_of_day", "value": "evening"}
    })
    assert res.status_code == 200
    assert len(res.json()["active_constraints"]) == 1

    # Remove the constraint (wrong direction recovery)
    res = client.post("/api/candidates", json={
        "session_id": sess_id,
        "remove_constraint": {"dimension": "time_of_day", "value": "evening"}
    })
    assert res.status_code == 200
    restored_data = res.json()
    assert len(restored_data["active_constraints"]) == 0
    assert restored_data["total"] == initial_total
    assert "Removed filter" in restored_data["banner_message"]

