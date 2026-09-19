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

# Enable CORS for local and web clients (supporting Vercel, Railway, localhost, and custom domains)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()] if allowed_origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.railway\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
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
