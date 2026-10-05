from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.providers.database import init_db
from app.routes import search, understand, candidates, refine, confirm, library

app = FastAPI(
    title="ReMind API",
    description="Google Photos Memory Reconstruction MVP Backend API powered by Gemini Multimodal Model",
    version="0.1.0",
)


# Ensure database tables are created at startup
init_db()

# CORS configuration for mobile and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount photos directory for static asset delivery
project_root = Path(__file__).resolve().parent.parent.parent
photos_dir = project_root / "data" / "photos"
if photos_dir.exists():
    app.mount("/photos", StaticFiles(directory=str(photos_dir)), name="photos")
    app.mount("/data/photos", StaticFiles(directory=str(photos_dir)), name="data_photos")

# Mount web frontend static assets and root route
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        from fastapi.responses import FileResponse
        return FileResponse(static_dir / "index.html")

# Register API routes
app.include_router(search.router)
app.include_router(understand.router)
app.include_router(candidates.router)
app.include_router(refine.router)
app.include_router(confirm.router)
app.include_router(library.router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend service readiness."""
    return {
        "status": "ok",
        "service": "ReMind API",
        "version": "0.1.0",
        "gemini_model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
