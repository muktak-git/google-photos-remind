import os
import shutil
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models.database import Base


def get_sqlite_url() -> str:
    """Resolve SQLite DB path ensuring parent directory exists with Vercel serverless support."""
    if os.environ.get("VERCEL"):
        tmp_db = Path("/tmp/remind.db")
        if not tmp_db.exists():
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            source_db = project_root / settings.SQLITE_DB_PATH
            if source_db.exists():
                shutil.copyfile(source_db, tmp_db)
        return f"sqlite:///{tmp_db}"

    db_path = Path(settings.SQLITE_DB_PATH)
    if not db_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        db_path = project_root / settings.SQLITE_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


engine = create_engine(
    get_sqlite_url(),
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency helper to yield database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
