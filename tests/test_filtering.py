import json
import time
from pathlib import Path

import pandas as pd
import pytest

from app.config import Settings
from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant
from app.services.dataset_loader import DatasetLoader
from app.services.filtering import (
    FilteringService,
    calculate_candidate_score,
)
from app.services.preprocessor import preprocess_dataframe


@pytest.fixture
def sample_pool() -> list[Restaurant]:
    fixtures_path = Path("tests/fixtures/sample_restaurants.json")
    with open(fixtures_path) as f:
        data = json.load(f)
    _, restaurants = preprocess_dataframe(pd.DataFrame(data))
    return restaurants


def test_calculate_candidate_score():
    r1 = Restaurant(
        name="High Rating High Votes",
        location="koramangala",
        cuisines=["Cafe"],
        cost_for_two=500,
        rating=4.5,
        votes=10000,
        budget_tier="low",
    )
    r2 = Restaurant(
        name="High Rating Low Votes",
        location="koramangala",
        cuisines=["Cafe"],
        cost_for_two=500,
        rating=4.5,
        votes=10,
        budget_tier="low",
    )
    r3 = Restaurant(
        name="Low Rating High Votes",
        location="koramangala",
        cuisines=["Cafe"],
        cost_for_two=500,
        rating=3.5,
        votes=10000,
        budget_tier="low",
    )

    s1 = calculate_candidate_score(r1)
    s2 = calculate_candidate_score(r2)
    s3 = calculate_candidate_score(r3)

    # Same rating, higher votes -> higher score
    assert s1 > s2
    # Higher rating prioritized over lower rating
    assert s1 > s3


def test_location_filtering(sample_pool: list[Restaurant]):
    service = FilteringService()
    prefs = UserPreferences(
        location="indiranagar",
        budget="low",
        cuisine="Ice Cream",
        min_rating=0.0,
    )
    result = service.filter(prefs, pool=sample_pool)
    assert len(result.candidates) == 1
    assert result.candidates[0].name == "Corner House Ice Cream"


def test_cuisine_filtering_partial_and_multi(sample_pool: list[Restaurant]):
    service = FilteringService()

    # Partial match: "Burger" matches "Cafe, American, Burger, Fast Food"
    prefs1 = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Burger",
        min_rating=0.0,
    )
    res1 = service.filter(prefs1, pool=sample_pool)
    assert any(c.name == "Truffles" for c in res1.candidates)

    # Multi-cuisine input: "Pizza, French"
    prefs2 = UserPreferences(
        location="old airport road",
        budget="high",
        cuisine="Pizza, French",
        min_rating=0.0,
    )
    res2 = service.filter(prefs2, pool=sample_pool)
    assert any(c.name == "Le Cirque Signature" for c in res2.candidates)


def test_rating_filtering(sample_pool: list[Restaurant]):
    service = FilteringService()

    # min_rating 4.5 should exclude 4.4 and unrated
    prefs = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Cafe",
        min_rating=4.5,
    )
    result = service.filter(prefs, pool=sample_pool)
    for c in result.candidates:
        assert c.rating >= 4.5


def test_budget_tier_filtering(sample_pool: list[Restaurant]):
    service = FilteringService()

    # "high" budget tier should select Le Cirque Signature (cost 6000)
    prefs = UserPreferences(
        location="old airport road",
        budget="high",
        cuisine="Italian",
        min_rating=0.0,
    )
    result = service.filter(prefs, pool=sample_pool)
    assert len(result.candidates) >= 1
    assert all(c.budget_tier == "high" for c in result.candidates)


def test_keyword_fallback_when_too_restrictive(sample_pool: list[Restaurant]):
    service = FilteringService()

    # Additional preference that matches nothing in Truffles attributes
    prefs = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Burger",
        min_rating=4.0,
        additional_preferences="rooftop karaoke pool",
    )
    result = service.filter(prefs, pool=sample_pool)
    # Should gracefully fall back to matching Truffles without dropping everything
    assert any(c.name == "Truffles" for c in result.candidates)


def test_filter_relaxation_triggers(sample_pool: list[Restaurant]):
    service = FilteringService()

    # Ask for low budget in old airport road with Italian cuisine
    # Only high budget Italian exists there. Relaxation should kick in.
    prefs = UserPreferences(
        location="old airport road",
        budget="low",  # Strict budget tier low doesn't exist
        cuisine="Italian",
        min_rating=4.0,
    )
    result = service.filter(prefs, pool=sample_pool)
    assert len(result.candidates) >= 1
    assert "budget" in result.relaxation_applied
    assert "Le Cirque Signature" in [c.name for c in result.candidates]
    assert result.message is not None


def test_zero_matches_unknown_location(sample_pool: list[Restaurant]):
    service = FilteringService()
    prefs = UserPreferences(
        location="NonExistentCityXYZ",
        budget="low",
        cuisine="Italian",
        min_rating=3.0,
    )
    result = service.filter(prefs, pool=sample_pool)
    assert len(result.candidates) == 0
    assert result.total_matching == 0
    assert result.message is not None
    assert "No restaurants found" in result.message


def test_capping_at_max_candidates():
    # Generate 50 mock restaurants in same location
    mock_restaurants = [
        Restaurant(
            name=f"Restaurant {i}",
            location="whitefield",
            cuisines=["North Indian"],
            cost_for_two=400,
            rating=4.0 + (i % 10) * 0.1,
            votes=i * 10,
            budget_tier="low",
        )
        for i in range(50)
    ]

    settings = Settings(max_candidates_for_llm=20)
    service = FilteringService(settings=settings)

    prefs = UserPreferences(
        location="whitefield",
        budget="low",
        cuisine="North Indian",
        min_rating=3.0,
        top_k=5,
    )
    result = service.filter(prefs, pool=mock_restaurants)
    assert len(result.candidates) <= 20
    assert result.total_matching == 50


def test_full_dataset_filtering_benchmark():
    """Verify filtering completes in < 200ms on the full cached dataset."""
    loader = DatasetLoader()
    if not loader.settings.dataset_cache_path or not Path(loader.settings.dataset_cache_path).exists():
        pytest.skip("Local Parquet cache not found; skipping full dataset benchmark.")

    service = FilteringService(loader=loader)

    prefs = UserPreferences(
        location="indiranagar",
        budget="medium",
        cuisine="North Indian",
        min_rating=3.5,
        top_k=5,
    )

    # Warm up loader
    _ = loader.get_restaurants()

    # Time filter execution
    start = time.perf_counter()
    result = service.filter(prefs)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\nFiltering 12k+ restaurants completed in {elapsed_ms:.2f} ms")
    assert elapsed_ms < 200
    assert len(result.candidates) > 0
    assert len(result.candidates) <= 30
