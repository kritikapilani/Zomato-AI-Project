import json
from pathlib import Path

import pandas as pd
import pytest

from app.config import Settings
from app.models.preferences import UserPreferences
from app.services.dataset_loader import DatasetLoader
from app.services.filtering import FilteringService
from app.services.orchestrator import RecommendationOrchestrator
from app.services.preprocessor import preprocess_dataframe
from tests.mocks.mock_groq_client import MockGroqClient


@pytest.fixture
def mock_loader(tmp_path: Path) -> DatasetLoader:
    fixtures_path = Path("tests/fixtures/sample_restaurants.json")
    with open(fixtures_path) as f:
        data = json.load(f)
    raw_df = pd.DataFrame(data)

    cache_file = tmp_path / "cache.parquet"
    settings = Settings(dataset_cache_path=str(cache_file))
    clean_df, _ = preprocess_dataframe(raw_df, settings)
    clean_df.to_parquet(cache_file, index=False)

    loader = DatasetLoader(settings)
    loader.load()
    return loader


def test_orchestrator_happy_path_with_mock_groq(mock_loader: DatasetLoader):
    mock_llm_data = {
        "recommendations": [
            {
                "name": "Truffles",
                "cuisine": "Burger, American",
                "rating": 4.7,
                "estimated_cost": 900,
                "explanation": "Outstanding burgers in a bustling Koramangala atmosphere.",
            }
        ],
        "summary": "Best cafe pick in Koramangala.",
    }
    mock_groq = MockGroqClient(response_data=mock_llm_data)

    orchestrator = RecommendationOrchestrator(
        loader=mock_loader,
        groq_client=mock_groq,
    )

    prefs = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Burger",
        min_rating=4.0,
        top_k=1,
    )

    response = orchestrator.recommend(prefs)

    assert len(response.recommendations) == 1
    assert response.recommendations[0].name == "Truffles"
    assert response.metadata["source"] == "groq"
    assert response.metadata["candidates_considered"] >= 1
    assert "latency_ms" in response.metadata
    assert mock_groq.call_count == 1


def test_orchestrator_zero_candidates_short_circuit(mock_loader: DatasetLoader):
    mock_groq = MockGroqClient()
    orchestrator = RecommendationOrchestrator(
        loader=mock_loader,
        groq_client=mock_groq,
    )

    prefs = UserPreferences(
        location="NonExistentCity123",
        budget="low",
        cuisine="Chinese",
        min_rating=3.0,
    )

    response = orchestrator.recommend(prefs)

    # Short-circuit: recommendations should be empty and Groq must NOT have been invoked
    assert len(response.recommendations) == 0
    assert mock_groq.call_count == 0
    assert response.metadata["source"] == "filtering_short_circuit"
    assert "Try searching for popular Bangalore localities" in response.summary


def test_orchestrator_fallback_when_groq_client_is_none(mock_loader: DatasetLoader):
    orchestrator = RecommendationOrchestrator(
        loader=mock_loader,
        groq_client=None,  # No Groq client (e.g. unconfigured API key)
    )

    prefs = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Burger",
        min_rating=4.0,
        top_k=2,
    )

    response = orchestrator.recommend(prefs)

    assert len(response.recommendations) >= 1
    assert response.metadata["source"] == "fallback"
    assert "GROQ_API_KEY is not configured" in response.metadata["fallback_reason"]
    assert response.recommendations[0].name == "Truffles"


def test_orchestrator_fallback_on_groq_timeout(mock_loader: DatasetLoader):
    mock_groq = MockGroqClient(should_timeout=True)
    orchestrator = RecommendationOrchestrator(
        loader=mock_loader,
        groq_client=mock_groq,
    )

    prefs = UserPreferences(
        location="indiranagar",
        budget="low",
        cuisine="Ice Cream",
        min_rating=4.0,
        top_k=1,
    )

    response = orchestrator.recommend(prefs)

    # Should not crash; gracefully returns fallback recommendations
    assert len(response.recommendations) == 1
    assert response.recommendations[0].name == "Corner House Ice Cream"
    assert response.metadata["source"] == "fallback"
    assert "timed out" in response.metadata["fallback_reason"]
