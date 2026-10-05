import sys
from pathlib import Path

# Add backend directory to sys.path so app can be imported
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)


def test_health_endpoint():
    """Verify the /health check endpoint returns 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ReMind API"
    assert data["version"] == "0.1.0"
    assert "gemini_model" in data
    assert "embedding_model" in data


def test_settings_load():
    """Verify settings load correctly from .env and defaults."""
    assert settings.PORT == 8000
    assert settings.MAX_CANDIDATES == 20
    assert settings.MAX_REFINEMENT_TURNS == 5
    assert settings.CHROMA_PERSIST_DIR == "./data/chroma"
    assert settings.SQLITE_DB_PATH == "./data/db/remind.db"
