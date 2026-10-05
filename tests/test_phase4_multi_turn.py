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


def test_phase4_complete_multi_turn_refinement_journey():
    """
    Task 4.2: Walk through complete multi-turn refinement journey:
    Query -> Candidates (20) -> Turn 1 Refinement -> Narrowed Candidates -> Turn 2 Refinement -> Success Confirm.
    """
    # 1. Initiate search
    s_res = client.post("/api/search", json={"query": "That grand palace courtyard we visited during our Rajasthan trip"}).json()
    session_id = s_res["session_id"]
    assert session_id is not None

    # 2. Understand clues
    u_res = client.post("/api/understand", json={"session_id": session_id}).json()
    assert u_res["session_id"] == session_id
    assert u_res["clues"]["location"] == "Rajasthan"

    # 3. Retrieve initial candidates (Top 20)
    c_res = client.post("/api/candidates", json={"session_id": session_id}).json()
    assert c_res["total"] == 20
    assert len(c_res["candidates"]) == 20
    initial_ids = [c["photo_id"] for c in c_res["candidates"]]
    # Top candidates must be royal palaces, not temples
    assert any(pid.startswith("raj_palace") for pid in initial_ids[:5])

    # 4. Turn 1 Refinement Question
    r1_res = client.post("/api/refine", json={"session_id": session_id}).json()
    assert r1_res["session_id"] == session_id
    assert r1_res["turn"] == 1
    assert "dimension" in r1_res
    assert len(r1_res["options"]) >= 2
    dim1 = r1_res["dimension"]
    ans1 = r1_res["options"][0]

    # 5. Apply Turn 1 Constraint & Narrow Candidates
    c1_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": dim1, "value": ans1}
    }).json()
    assert c1_res["turn"] == 1
    # Candidate pool must either narrow down or preserve viable candidates
    assert 0 < len(c1_res["candidates"]) <= 20

    # 6. Turn 2 Refinement Question
    r2_res = client.post("/api/refine", json={"session_id": session_id}).json()
    assert r2_res["turn"] == 2
    dim2 = r2_res["dimension"]
    ans2 = r2_res["options"][0]

    # 7. Apply Turn 2 Constraint
    c2_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": dim2, "value": ans2}
    }).json()
    assert c2_res["turn"] == 2
    assert c2_res["total"] > 0

    # 8. Confirm Target Photo
    target_photo = c2_res["candidates"][0]
    conf_res = client.post("/api/confirm", json={
        "session_id": session_id,
        "photo_id": target_photo["photo_id"],
        "confirmed": True
    }).json()
    assert conf_res["success"] is True
    assert conf_res["status"] == "completed"
    assert conf_res["metrics"]["total_turns"] >= 2
    assert conf_res["metrics"]["confirmed"] is True

    # 9. Verify Session Audit Trails in SQLite
    db = SessionLocal()
    sess = db.query(SessionRecord).filter_by(session_id=session_id).first()
    assert sess is not None
    assert sess.status == "completed"
    events = db.query(SessionEventRecord).filter_by(session_id=session_id).all()
    assert len(events) >= 6
    db.close()


def test_phase4_rejection_reenters_refinement_loop():
    """
    Acceptance Criteria: Rejection ('No, keep looking') cleanly re-enters the refinement loop.
    """
    s_res = client.post("/api/search", json={"query": "coorg campfire with friends"}).json()
    session_id = s_res["session_id"]
    client.post("/api/understand", json={"session_id": session_id})
    cand_res = client.post("/api/candidates", json={"session_id": session_id}).json()
    first_candidate = cand_res["candidates"][0]["photo_id"]

    # User clicks "No, keep looking" (confirmed=False)
    rej_res = client.post("/api/confirm", json={
        "session_id": session_id,
        "photo_id": first_candidate,
        "confirmed": False
    }).json()
    assert rej_res["status"] == "active"
    assert rej_res["metrics"]["confirmed"] is False

    # Refinement continues cleanly
    refine_next = client.post("/api/refine", json={"session_id": session_id}).json()
    assert "question" in refine_next
    assert len(refine_next["options"]) >= 2


def test_phase4_not_sure_fallback_graceful_handling():
    """
    Task 4.3: 'Not sure' answer does not drop candidates unexpectedly.
    """
    s_res = client.post("/api/search", json={"query": "summer pool party water splash"}).json()
    session_id = s_res["session_id"]
    client.post("/api/candidates", json={"session_id": session_id})

    # User selects "Not sure"
    not_sure_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "time_of_day", "value": "Not sure"}
    }).json()
    # Must retain candidates gracefully without 0 drops
    assert not_sure_res["total"] > 0
    assert len(not_sure_res["candidates"]) > 0


def test_phase4_kids_playing_in_water_accuracy():
    """
    Verify that kids playing in water query retrieves water pool photos with high confidence.
    """
    s_res = client.post("/api/search", json={"query": "Kids playing and splashing water in the swimming pool"}).json()
    session_id = s_res["session_id"]
    u_res = client.post("/api/understand", json={"session_id": session_id}).json()
    c_res = client.post("/api/candidates", json={"session_id": session_id}).json()
    assert c_res["total"] > 0
    top_candidates = [c["photo_id"] for c in c_res["candidates"][:5]]
    assert any("water_kids" in pid for pid in top_candidates)


def test_phase4_conversational_coorg_cafe_workflow():
    """
    Verify the user's exact workflow experience:
    User: 'That café in coorg.'
    System: 'I found 38 possible photos from your coorg trip. Do you remember anything else?'
    Facets: When? [Around Christmas / New Year / Not sure], What did it look like? [Blue wall / Outdoor / Beach nearby / Not sure]
    User: 'Blue wall.'
    System: 'I found 6 photos that may match.'
    """
    s_res = client.post("/api/search", json={"query": "That café in coorg."}).json()
    session_id = s_res["session_id"]

    # Initial retrieval + refinement
    c_res = client.post("/api/candidates", json={"session_id": session_id}).json()
    assert c_res["total"] == 38
    assert "38 possible photos" in c_res["banner_message"]
    assert "Coorg" in c_res["banner_message"]

    ref = c_res["refinement"]
    assert ref is not None
    assert "Do you remember anything else?" in ref["follow_up_prompt"]

    facet_titles = [f["title"] for f in ref["facets"]]
    assert "When?" in facet_titles
    assert "What did it look like?" in facet_titles

    what_facet = next(f for f in ref["facets"] if f["title"] == "What did it look like?")
    assert "Blue wall" in what_facet["options"]

    # User inputs "Blue wall"
    refine_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "visual", "value": "Blue wall"}
    }).json()

    assert refine_res["total"] == 6
    assert refine_res["banner_message"] == "I found 6 photos that may match."
    # All 6 returned photos should be the blue wall cafe photos
    assert all("coorg_" in c["photo_id"] for c in refine_res["candidates"])
    assert all("blue wall" in c["visual_description"].lower() for c in refine_res["candidates"])
    # Recognition prompt asks for Yes / No input per user requirement
    assert refine_res["refinement"]["dimension"] == "recognition_ready"
    assert refine_res["refinement"]["options"] == ["Yes", "No"]


def test_phase4_conversational_not_sure_smarter_non_repetitive_workflow():
    """
    Verify that when user says 'Not sure', the assistant does NOT repeat
    the previous questions, but advances smartly to new facets based on
    the keyword and remaining photos.
    """
    s_res = client.post("/api/search", json={"query": "That café in coorg."}).json()
    session_id = s_res["session_id"]

    # Initial retrieval + refinement
    c_res = client.post("/api/candidates", json={"session_id": session_id}).json()
    assert c_res["total"] == 38
    initial_facet_titles = [f["title"] for f in c_res["refinement"]["facets"]]
    assert "When?" in initial_facet_titles
    assert "What did it look like?" in initial_facet_titles

    # User says "Not sure"
    not_sure_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "general", "value": "Not sure"}
    }).json()

    # Verify that total candidates are preserved (not dropped to 0)
    assert not_sure_res["total"] == 38
    # Banner acknowledges empathetically without repetition
    assert "No problem!" in not_sure_res["banner_message"]
    assert "Coorg" in not_sure_res["banner_message"]

    # Refinement MUST NOT repeat "When?" or "What did it look like?"
    new_ref = not_sure_res["refinement"]
    new_facet_titles = [f["title"] for f in new_ref["facets"]]
    assert "When?" not in new_facet_titles
    assert "What did it look like?" not in new_facet_titles

    # Instead, smart secondary facets tailored to Coorg café are presented:
    assert "Setting & Vibe" in new_facet_titles
    setting_facet = next(f for f in new_ref["facets"] if f["title"] == "Setting & Vibe")
    assert "Homestay veranda" in setting_facet["options"]
    assert "Coffee estate garden" in setting_facet["options"]

    # User now picks "Homestay veranda"
    veranda_res = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "setting_vibe", "value": "Homestay veranda"}
    }).json()

    assert veranda_res["total"] > 0
    assert veranda_res["total"] < 38
    assert "I found" in veranda_res["banner_message"]


def test_phase4_conversational_no_asks_what_do_you_remember_more_with_smart_hints():
    """
    Verify that when user clicks 'No' to recognition:
    1. System asks 'What do you remember more?'
    2. Provides smart hint keywords generated using embeddings of the input.
    """
    s_res = client.post("/api/search", json={"query": "That café in coorg."}).json()
    session_id = s_res["session_id"]
    client.post("/api/candidates", json={"session_id": session_id})

    # User narrows down with "Blue wall" -> 6 candidates
    c1 = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "visual", "value": "Blue wall"}
    }).json()
    assert c1["total"] == 6
    assert c1["refinement"]["dimension"] == "recognition_ready"
    assert c1["refinement"]["options"] == ["Yes", "No"]

    # User clicks "No"
    c2 = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "recognition", "value": "No"}
    }).json()

    # System must ask "What do you remember more?"
    assert c2["refinement"]["follow_up_prompt"] == "What do you remember more?"
    assert c2["refinement"]["dimension"] == "more_clues"
    assert "No problem!" in c2["banner_message"]

    # Hint keywords generated using embeddings of the input must be present
    hints = c2["refinement"]["hint_keywords"]
    assert len(hints) >= 3
    # Check that hints are smart and relevant to Coorg trip
    expected_pool = [x.lower() for x in ["Homestay", "Veranda", "Coffee estate", "Plantation mugs", "Coffee lounge", "Campfire", "Misty hills", "Coffee plantation", "Wooden bench"]]
    assert any(h.lower() in expected_pool for h in hints)


def test_phase4_multi_turn_beyond_three_attempts_continues_working():
    """
    Verify that refinement options continue to work seamlessly across turns 1, 2, 3, 4, and 5+.
    No empty options, no broken loops, no crash.
    """
    s_res = client.post("/api/search", json={"query": "coorg homestay"}).json()
    session_id = s_res["session_id"]
    client.post("/api/candidates", json={"session_id": session_id})

    # Turn 1
    c1 = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "scene_type", "value": "Homestay"}
    }).json()
    assert c1["total"] > 0
    assert len(c1["refinement"]["options"]) >= 2
    assert c1["refinement"]["facets"] is not None

    # Turn 2
    c2 = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "setting_vibe", "value": "Homestay veranda"}
    }).json()
    assert c2["total"] > 0
    assert len(c2["refinement"]["options"]) >= 2

    # Turn 3
    c3 = client.post("/api/candidates", json={
        "session_id": session_id,
        "constraint": {"dimension": "highlights", "value": "Campfire nearby"}
    }).json()
    assert c3["total"] > 0
    assert len(c3["refinement"]["options"]) >= 2

    # Turn 4: User selects a detail or rejects recognition
    ref3 = c3["refinement"]
    if ref3["dimension"] == "recognition_ready":
        # User says No
        c4 = client.post("/api/candidates", json={
            "session_id": session_id,
            "constraint": {"dimension": "recognition", "value": "No"}
        }).json()
        assert c4["refinement"]["dimension"] == "more_clues"
        assert len(c4["refinement"]["options"]) >= 2
        # User picks a hint keyword
        hint_val = c4["refinement"]["options"][0]
        c5 = client.post("/api/candidates", json={
            "session_id": session_id,
            "constraint": {"dimension": "visual", "value": hint_val}
        }).json()
    else:
        # Refinement option picked
        opt_val = ref3["options"][0]
        c5 = client.post("/api/candidates", json={
            "session_id": session_id,
            "constraint": {"dimension": ref3["dimension"], "value": opt_val}
        }).json()

    # Turn 5: Refinement options must still be robust and non-empty!
    assert c5["total"] > 0
    assert c5["refinement"] is not None
    assert len(c5["refinement"]["options"]) >= 2
    assert c5["refinement"]["question"] is not None
    assert len(c5["refinement"]["question"]) > 0

    # Verify /api/refine also returns non-empty options on Turn 5
    r5 = client.post("/api/refine", json={"session_id": session_id}).json()
    assert len(r5["options"]) >= 2
    assert r5["question"] is not None




