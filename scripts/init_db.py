import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.providers.database import init_db, engine
from app.config import settings

def main():
    print(f"Initializing SQLite database at: {settings.SQLITE_DB_PATH}")
    init_db()
    print("Database tables ('photos', 'sessions', 'session_events') initialized successfully.")

if __name__ == "__main__":
    main()
