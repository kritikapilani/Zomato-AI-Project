import json
import pytest

from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant
from app.services.response_parser import (
    ResponseParser,
    extract_json_from_text,
)


@pytest.fixture
def mock_candidates() -> list[Restaurant]:
    return [
        Restaurant(
            name="Truffles",
            location="koramangala",
            cuisines=["Cafe", "Burger"],
            cost_for_two=900,
            rating=4.7,
            votes=14000,
            budget_tier="medium",
        ),
        Restaurant(
            name="Corner House Ice Cream",
            location="indiranagar",
            cuisines=["Desserts", "Ice Cream"],
            cost_for_two=450,
            rating=4.6,
            votes=5000,
            budget_tier="low",
        ),
        Restaurant(
            name="Le Cirque Signature",
            location="old airport road",
            cuisines=["Italian", "French"],
            cost_for_two=6000,
            rating=4.4,
            votes=480,
            budget_tier="high",
        ),
    ]


def test_extract_json_from_plain_text():
    raw = '{"recommendations": [], "summary": "No spots."}'
    parsed = extract_json_from_text(raw)
    assert parsed["summary"] == "No spots."


def test_extract_json_from_markdown_fences():
    raw = """```json
    {
        "recommendations": [{"name": "Truffles"}],
        "summary": "Great burgers"
    }
    ```"""
    parsed = extract_json_from_text(raw)
    assert parsed["summary"] == "Great burgers"
    assert len(parsed["recommendations"]) == 1


def test_extract_json_with_surrounding_conversational_text():
    raw = """Here is the dining recommendation you requested:
    {
        "recommendations": [{"name": "Corner House Ice Cream"}],
        "summary": "Great desserts"
    }
    Enjoy your dining experience!"""
    parsed = extract_json_from_text(raw)
    assert parsed["recommendations"][0]["name"] == "Corner House Ice Cream"


def test_extract_json_invalid():
    with pytest.raises(ValueError, match="No valid JSON object"):
        extract_json_from_text("Sorry, I could not find any recommendations.")


def test_parse_and_validate_success(mock_candidates: list[Restaurant]):
    prefs = UserPreferences(location="koramangala", budget="medium", cuisine="Burger", top_k=2)
    raw_llm_json = json.dumps(
        {
            "recommendations": [
                {
                    "name": "Truffles",
                    "cuisine": "Burger",
                    "rating": 4.7,
                    "estimated_cost": 900,
                    "explanation": "Best burgers in town with cozy seating.",
                },
                {
                    "name": "Corner House Ice Cream",
                    "cuisine": "Desserts",
                    "rating": 4.6,
                    "estimated_cost": 450,
                    "explanation": "Perfect dessert follow-up.",
                },
            ],
            "summary": "Top choices for burgers and desserts.",
        }
    )

    response = ResponseParser.parse_and_validate(raw_llm_json, mock_candidates, prefs)
    assert len(response.recommendations) == 2
    assert response.recommendations[0].name == "Truffles"
    assert response.recommendations[0].explanation == "Best burgers in town with cozy seating."
    assert response.metadata["source"] == "groq"
    assert response.metadata["hallucinations_dropped"] == 0


def test_anti_hallucination_drops_fake_restaurants(mock_candidates: list[Restaurant]):
    prefs = UserPreferences(location="koramangala", budget="medium", cuisine="Burger", top_k=1)
    raw_llm_json = json.dumps(
        {
            "recommendations": [
                {
                    "name": "NonExistent Ghost Diner",  # Hallucinated!
                    "cuisine": "Fusion",
                    "rating": 5.0,
                    "estimated_cost": 1000,
                    "explanation": "Made up restaurant.",
                },
                {
                    "name": "Truffles",  # Valid candidate!
                    "cuisine": "Burger",
                    "rating": 4.7,
                    "estimated_cost": 900,
                    "explanation": "Real candidate match.",
                },
            ],
            "summary": "Some places.",
        }
    )

    response = ResponseParser.parse_and_validate(raw_llm_json, mock_candidates, prefs)
    # The fake diner must be dropped, and Truffles should be retained
    names = [r.name for r in response.recommendations]
    assert "NonExistent Ghost Diner" not in names
    assert "Truffles" in names
    assert response.metadata["hallucinations_dropped"] == 1


def test_top_up_when_llm_under_returns(mock_candidates: list[Restaurant]):
    # User requested top_k = 3, but LLM only provided 1 valid recommendation
    prefs = UserPreferences(location="koramangala", budget="medium", cuisine="Cafe", top_k=3)
    raw_llm_json = json.dumps(
        {
            "recommendations": [
                {
                    "name": "Truffles",
                    "cuisine": "Cafe",
                    "rating": 4.7,
                    "estimated_cost": 900,
                    "explanation": "Top rated cafe.",
                }
            ],
            "summary": "Only 1 match returned by LLM.",
        }
    )

    response = ResponseParser.parse_and_validate(raw_llm_json, mock_candidates, prefs)
    # Should top up with other candidates from mock_candidates to reach top_k=3
    assert len(response.recommendations) == 3
    names = [r.name for r in response.recommendations]
    assert names[0] == "Truffles"
    assert "Corner House Ice Cream" in names


def test_generate_fallback_response(mock_candidates: list[Restaurant]):
    prefs = UserPreferences(location="koramangala", budget="medium", cuisine="Cafe", top_k=2)
    response = ResponseParser.generate_fallback_response(
        mock_candidates, prefs, reason="Groq API timeout"
    )

    assert len(response.recommendations) == 2
    assert response.metadata["source"] == "fallback"
    assert response.metadata["fallback_reason"] == "Groq API timeout"
    assert "Ranked #1" in response.recommendations[0].explanation
    assert response.recommendations[0].name == "Truffles"
