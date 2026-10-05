import sys
from pathlib import Path

# Add backend directory to sys.path for Vercel Serverless Function runtime
root_path = Path(__file__).resolve().parent.parent
backend_path = root_path / "backend"

if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from app.main import app

# Export app for Vercel's ASGI serverless handler
app = app
