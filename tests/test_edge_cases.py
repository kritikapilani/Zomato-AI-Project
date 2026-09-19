import json
import pytest

from app.models.preferences import UserPreferences
from app.models.response import RecommendationResponse
from app.services.dataset_loader import get_dataset_loader
from app.services.orchestrator import RecommendationOrchestrator
from tests.mocks.mock_groq_client import MockGroqClient


@pytest.fixture(scope="module")
def shared_orchestrator() -> RecommendationOrchestrator:
    loader = get_dataset_loader()
    if not loader.is_loaded:
        loader.load()
    return RecommendationOrchestrator(loader=loader)


# --- Test 1: 5-Scenario E2E Evaluation Across Diverse Bangalore Neighborhoods ---
@pytest.mark.parametrize(
    "scenario_name,location,budget,cuisine,min_rating,additional,top_k",
    [
        (
            "Indiranagar Italian",
            "indiranagar",
            "medium",
            "Italian",
            4.0,
            "outdoor seating",
            3,
        ),
        (
            "Koramangala Burgers",
            "koramangala",
            "medium",
            "Burger",
            4.0,
            "casual quick bites",
            3,
        ),
        (
            "Whitefield North Indian",
            "whitefield",
            "low",
            "North Indian",
            3.5,
            "family friendly",
            3,
        ),
        (
            "Jayanagar South Indian",
            "jayanagar",
            "low",
            "South Indian",
            3.8,
            "traditional breakfast",
            3,
        ),
        (
            "MG Road Cafe & Continental",
            "mg road",
            "medium",
            "Cafe",
            3.8,
            "artisan coffee",
            3,
        ),
    ],
)
def test_e2e_scenarios(
    shared_orchestrator: RecommendationOrchestrator,
    scenario_name: str,
    location: str,
    budget: str,
    cuisine: str,
    min_rating: float,
    additional: str,
    top_k: int,
):
    prefs = UserPreferences(
        location=location,
        budget=budget,  # type: ignore
        cuisine=cuisine,
        min_rating=min_rating,
        additional_preferences=additional,
        top_k=top_k,
    )

    response = shared_orchestrator.recommend(prefs)
    assert isinstance(response, RecommendationResponse)
    assert len(response.recommendations) > 0
    assert len(response.recommendations) <= top_k

    # Validate output contract
    for rec in response.recommendations:
        assert rec.name
        assert rec.cuisine
        assert rec.rating >= 0.0
        assert rec.estimated_cost >= 0
        assert len(rec.explanation) > 10


# --- Test 2: Extreme Boundary Conditions ---
def test_boundary_conditions(shared_orchestrator: RecommendationOrchestrator):
    # top_k = 1
    prefs_min_k = UserPreferences(
        location="indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=3.5,
        top_k=1,
    )
    res_min_k = shared_orchestrator.recommend(prefs_min_k)
    assert len(res_min_k.recommendations) == 1

    # top_k = 10
    prefs_max_k = UserPreferences(
        location="indiranagar",
        budget="medium",
        cuisine="North Indian",
        min_rating=3.0,
        top_k=10,
    )
    res_max_k = shared_orchestrator.recommend(prefs_max_k)
    assert len(res_max_k.recommendations) <= 10

    # min_rating = 0.0 (all rated and unrated allowed)
    prefs_zero_rating = UserPreferences(
        location="koramangala",
        budget="low",
        cuisine="Cafe",
        min_rating=0.0,
        top_k=3,
    )
    res_zero_rating = shared_orchestrator.recommend(prefs_zero_rating)
    assert len(res_zero_rating.recommendations) > 0


# --- Test 3: Unicode and Accented Characters ---
def test_unicode_and_special_characters(shared_orchestrator: RecommendationOrchestrator):
    prefs_unicode = UserPreferences(
        location="Indiranagar",
        budget="medium",
        cuisine="Café",  # Accented e
        min_rating=3.5,
        additional_preferences="cozy café vibes ☕",
        top_k=2,
    )
    response = shared_orchestrator.recommend(prefs_unicode)
    assert isinstance(response, RecommendationResponse)
    assert len(response.recommendations) > 0


# --- Test 4: Extremely Long Additional Preferences ---
def test_extremely_long_additional_preferences(shared_orchestrator: RecommendationOrchestrator):
    long_text = "outdoor seating and great coffee " * 50  # ~1600 characters
    prefs_long = UserPreferences(
        location="indiranagar",
        budget="medium",
        cuisine="Cafe",
        min_rating=3.5,
        additional_preferences=long_text,
        top_k=2,
    )
    response = shared_orchestrator.recommend(prefs_long)
    assert len(response.recommendations) > 0


# --- Test 5: Contract Test: Groq LLM Output Schema Verification ---
def test_schema_contract_compliance():
    sample_llm_json = {
        "recommendations": [
            {
                "name": "Truffles",
                "cuisine": "Burger, Cafe",
                "rating": 4.7,
                "estimated_cost": 900,
                "explanation": "Famous burgers with lively ambiance.",
            }
        ],
        "summary": "Great burger recommendation.",
    }

    mock_groq = MockGroqClient(response_data=sample_llm_json)
    loader = get_dataset_loader()
    orchestrator = RecommendationOrchestrator(loader=loader, groq_client=mock_groq)

    prefs = UserPreferences(
        location="koramangala",
        budget="medium",
        cuisine="Burger",
        top_k=1,
    )

    response = orchestrator.recommend(prefs)
    # Ensure serialization matches API schema perfectly
    json_output = response.model_dump_json()
    parsed_back = json.loads(json_output)

    assert "recommendations" in parsed_back
    assert "summary" in parsed_back
    assert "metadata" in parsed_back
    assert parsed_back["recommendations"][0]["name"] == "Truffles"
