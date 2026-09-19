import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.routes import router

app = FastAPI(
    title="Zomato Restaurant Recommendation API",
    description="AI-powered restaurant recommendations using structured filtering and Groq.",
    version=__version__,
)

# Enable CORS for local and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes first
app.include_router(router)
app.include_router(router, prefix="/api/v1")

# Mount frontend directory for UI delivery
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
