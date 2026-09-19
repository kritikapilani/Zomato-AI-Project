import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models.preferences import UserPreferences
from app.models.response import Recommendation, RecommendationResponse
from app.models.restaurant import Restaurant


def test_user_preferences_valid():
    prefs = UserPreferences(
        location="Delhi",
        budget="medium",
        cuisine="Chinese",
        min_rating=4.0,
        additional_preferences="family-friendly",
        top_k=5,
    )
    assert prefs.location == "Delhi"
    assert prefs.budget == "medium"


def test_user_preferences_strips_whitespace():
    prefs = UserPreferences(
        location="  Bangalore  ",
        budget="low",
        cuisine=" Italian ",
    )
    assert prefs.location == "Bangalore"
    assert prefs.cuisine == "Italian"


def test_user_preferences_rejects_empty_location():
    with pytest.raises(ValidationError):
        UserPreferences(location="   ", budget="low", cuisine="Italian")


def test_user_preferences_rejects_invalid_rating():
    with pytest.raises(ValidationError):
        UserPreferences(location="Delhi", budget="low", cuisine="Italian", min_rating=6.0)


def test_restaurant_valid():
    restaurant = Restaurant(
        name="Test Kitchen",
        location="mumbai",
        cuisines=["Italian", "Pizza"],
        cost_for_two=800,
        rating=4.2,
        votes=120,
        budget_tier="medium",
    )
    assert restaurant.cuisines == ["Italian", "Pizza"]


def test_recommendation_response_empty():
    prefs = UserPreferences(location="Delhi", budget="low", cuisine="Chinese")
    response = RecommendationResponse.empty(prefs, "No matches found.")
    assert response.recommendations == []
    assert response.summary == "No matches found."
    assert response.metadata["candidates_considered"] == 0


def test_recommendation_valid():
    rec = Recommendation(
        name="Spice Route",
        cuisine="Chinese",
        rating=4.5,
        estimated_cost=600,
        explanation="Great fit for your budget and cuisine preference.",
    )
    assert rec.name == "Spice Route"


def test_settings_budget_threshold_validation():
    with pytest.raises(ValidationError):
        Settings(budget_low_max=1500, budget_medium_max=500)


def test_settings_require_groq_api_key_missing():
    settings = Settings(groq_api_key="")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
        settings.require_groq_api_key()


def test_settings_require_groq_api_key_present():
    settings = Settings(groq_api_key="gsk_test_key")
    assert settings.require_groq_api_key() == "gsk_test_key"
