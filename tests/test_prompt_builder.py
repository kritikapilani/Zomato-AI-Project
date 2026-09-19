import json

from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant
from app.services.prompt_builder import PromptBuilder


def test_build_system_prompt():
    system_prompt = PromptBuilder.build_system_prompt()
    assert "Zomato" in system_prompt
    assert "ONLY recommend restaurants from the provided" in system_prompt
    assert "NEVER invent" in system_prompt
    assert "JSON" in system_prompt
    assert '"recommendations"' in system_prompt


def test_build_user_prompt():
    prefs = UserPreferences(
        location="Indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=4.0,
        additional_preferences="outdoor seating",
        top_k=3,
    )

    candidates = [
        Restaurant(
            name="Milano Pizzeria",
            location="indiranagar",
            cuisines=["Italian", "Pizza"],
            cost_for_two=1200,
            rating=4.5,
            votes=850,
            address="100ft Road, Indiranagar",
            rest_type="Casual Dining",
            budget_tier="medium",
        ),
        Restaurant(
            name="Pasta Bella",
            location="indiranagar",
            cuisines=["Italian", "Pasta"],
            cost_for_two=900,
            rating=4.2,
            votes=400,
            budget_tier="medium",
        ),
    ]

    user_prompt = PromptBuilder.build_user_prompt(prefs, candidates)

    assert "Indiranagar" in user_prompt
    assert "Italian" in user_prompt
    assert "outdoor seating" in user_prompt
    assert "top_k): 3" in user_prompt
    assert "Milano Pizzeria" in user_prompt
    assert "Pasta Bella" in user_prompt


def test_build_prompts_convenience_method():
    prefs = UserPreferences(location="Delhi", budget="low", cuisine="Chinese")
    candidates = [
        Restaurant(
            name="Wok Express",
            location="delhi",
            cuisines=["Chinese"],
            cost_for_two=400,
            rating=4.1,
            budget_tier="low",
        )
    ]

    system, user = PromptBuilder.build_prompts(prefs, candidates)
    assert isinstance(system, str) and len(system) > 50
    assert isinstance(user, str) and "Wok Express" in user
