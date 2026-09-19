from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_cached_settings, get_loader, get_orchestrator
from app.config import Settings
from app.models.preferences import UserPreferences
from app.models.response import RecommendationResponse
from app.services.dataset_loader import DatasetLoader
from app.services.orchestrator import RecommendationOrchestrator

router = APIRouter()


@router.get("/health")
def health_check(
    settings: Settings = Depends(get_cached_settings),
    loader: DatasetLoader = Depends(get_loader),
) -> dict:
    return {
        "status": "ok",
        "groq_configured": bool(settings.groq_api_key.strip()),
        "dataset": settings.hf_dataset_name,
        "dataset_loaded": loader.is_loaded,
    }


@router.get("/dataset/status")
def dataset_status(loader: DatasetLoader = Depends(get_loader)) -> dict:
    """Return status of the restaurant dataset and local Parquet cache."""
    return loader.get_status()


@router.post("/dataset/reload")
def reload_dataset(loader: DatasetLoader = Depends(get_loader)) -> dict:
    """Trigger reload of the dataset from Hugging Face / cache."""
    try:
        _, restaurants = loader.load(force_reload=True)
        return {
            "status": "success",
            "message": f"Dataset reloaded successfully with {len(restaurants)} restaurants.",
            "details": loader.get_status(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reload dataset: {exc}")


@router.get("/metadata/locations")
def get_locations(loader: DatasetLoader = Depends(get_loader)) -> dict:
    """Return unique Bangalore locations with restaurant counts."""
    df = loader.get_dataframe()
    if df.empty:
        return {"locations": [], "total": 0}
    counts = df["location"].value_counts()
    items = [{"name": loc.title(), "value": loc, "count": int(count)} for loc, count in counts.items()]
    return {"locations": items, "total": len(items)}


@router.get("/metadata/cuisines")
def get_cuisines(loader: DatasetLoader = Depends(get_loader)) -> dict:
    """Return unique cuisines with popularity counts."""
    df = loader.get_dataframe()
    if df.empty:
        return {"cuisines": [], "total": 0}
    cuisine_counts: dict[str, int] = {}
    for c_list in df["cuisines"].dropna():
        if hasattr(c_list, "__iter__") and not isinstance(c_list, (str, bytes)):
            for c in c_list:
                c_clean = str(c).strip()
                if c_clean:
                    cuisine_counts[c_clean] = cuisine_counts.get(c_clean, 0) + 1
    items = [
        {"name": k, "count": v}
        for k, v in sorted(cuisine_counts.items(), key=lambda x: (-x[1], x[0]))
    ]
    return {"cuisines": items, "total": len(items)}


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    preferences: UserPreferences,
    orchestrator: RecommendationOrchestrator = Depends(get_orchestrator),
) -> RecommendationResponse:
    """Generate personalized, AI-ranked restaurant recommendations based on dining preferences."""
    return orchestrator.recommend(preferences)
