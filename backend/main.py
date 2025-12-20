"""
SinkIn Image Experimentation Web App - Backend API
"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import init_db
from routes.jobs import router as jobs_router
from routes.images import router as images_router
from routes.runs import router as runs_router
from routes.assets import router as assets_router
from routes.analysis import router as analysis_router
from services.sinkin import sinkin_service

from config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: Initialize database and storage directories
    init_db()
    settings = get_settings()
    Path(settings.images_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.assets_dir).mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="SinkIn Image Experimentation API",
    description="Local-first platform for text-to-image experiments using SinkIn AI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(images_router)
app.include_router(assets_router)
app.include_router(analysis_router)


# Mount static files for serving images
settings = get_settings()
images_path = Path(settings.images_dir)
if images_path.exists():
    app.mount("/images", StaticFiles(directory=str(images_path)), name="images")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "SinkIn Image Experimentation API is running"}


@app.get("/api/health")
async def health_check():
    """API health check."""
    return {"status": "healthy"}


@app.get("/api/models")
async def get_models():
    """Get available models from SinkIn API."""
    try:
        result = sinkin_service.get_models()
        if result.get("error_code", 0) != 0:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to fetch models"))
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

