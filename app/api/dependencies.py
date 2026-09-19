from functools import lru_cache
from fastapi import Depends

from app.config import Settings, get_settings
from app.services.dataset_loader import DatasetLoader, get_dataset_loader
from app.services.filtering import FilteringService, get_filtering_service
from app.services.groq_client import GroqClientInterface, GroqLLMClient
from app.services.orchestrator import RecommendationOrchestrator


@lru_cache
def get_cached_settings() -> Settings:
    return get_settings()


def get_loader(settings: Settings = Depends(get_cached_settings)) -> DatasetLoader:
    return get_dataset_loader(settings)


def get_filtering(
    settings: Settings = Depends(get_cached_settings),
    loader: DatasetLoader = Depends(get_loader),
) -> FilteringService:
    return get_filtering_service(loader=loader, settings=settings)


def get_groq_client_optional(
    settings: Settings = Depends(get_cached_settings),
) -> GroqClientInterface | None:
    """Return GroqLLMClient if API key is configured, otherwise None (fallback mode)."""
    if settings.groq_api_key.strip():
        try:
            return GroqLLMClient(settings)
        except Exception:
            return None
    return None


def get_orchestrator(
    settings: Settings = Depends(get_cached_settings),
    loader: DatasetLoader = Depends(get_loader),
    filtering_service: FilteringService = Depends(get_filtering),
    groq_client: GroqClientInterface | None = Depends(get_groq_client_optional),
) -> RecommendationOrchestrator:
    return RecommendationOrchestrator(
        settings=settings,
        loader=loader,
        filtering_service=filtering_service,
        groq_client=groq_client,
    )
