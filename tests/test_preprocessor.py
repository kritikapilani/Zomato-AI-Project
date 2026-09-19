import json
from pathlib import Path

import pandas as pd
import pytest

from app.config import Settings
from app.models.restaurant import Restaurant
from app.services.preprocessor import (
    clean_text,
    compute_budget_tier,
    normalize_location,
    parse_cost,
    parse_cuisines,
    parse_rating,
    parse_votes,
    preprocess_dataframe,
    preprocess_record,
)


def test_clean_text():
    assert clean_text("  hello  ") == "hello"
    assert clean_text("") is None
    assert clean_text("   ") is None
    assert clean_text(None) is None
    assert clean_text(float("nan")) is None


def test_parse_rating_valid():
    assert parse_rating("4.7/5") == 4.7
    assert parse_rating("4.4 /5") == 4.4
    assert parse_rating("3.8") == 3.8
    assert parse_rating(4.2) == 4.2


def test_parse_rating_special_values():
    assert parse_rating("NEW") == 0.0
    assert parse_rating("-") == 0.0
    assert parse_rating(None) == 0.0
    assert parse_rating("") == 0.0
    assert parse_rating(float("nan")) == 0.0


def test_parse_rating_clamping():
    assert parse_rating("6.5") == 5.0
    assert parse_rating("-2.0") == 0.0


def test_parse_cost_with_commas_and_symbols():
    assert parse_cost("1,200") == 1200
    assert parse_cost("6,000") == 6000
    assert parse_cost("₹800 for two") == 800
    assert parse_cost("300") == 300
    assert parse_cost(500) == 500


def test_parse_cost_invalid():
    assert parse_cost(None) == 0
    assert parse_cost("") == 0
    assert parse_cost("-") == 0
    assert parse_cost(float("nan")) == 0


def test_parse_cuisines():
    assert parse_cuisines("Cafe, American, Burger, Fast Food") == [
        "Cafe",
        "American",
        "Burger",
        "Fast Food",
    ]
    assert parse_cuisines("North Indian | Chinese") == ["North Indian", "Chinese"]
    assert parse_cuisines(" Italian ; Mexican ") == ["Italian", "Mexican"]
    assert parse_cuisines("") == []
    assert parse_cuisines(None) == []
    assert parse_cuisines(["Italian", "French"]) == ["Italian", "French"]


def test_normalize_location():
    assert normalize_location("  Indiranagar  ") == "indiranagar"
    assert normalize_location("Koramangala 5th Block") == "koramangala 5th block"
    assert normalize_location(None) == ""


def test_compute_budget_tier_boundaries():
    assert compute_budget_tier(300, 500, 1500) == "low"
    assert compute_budget_tier(500, 500, 1500) == "low"
    assert compute_budget_tier(501, 500, 1500) == "medium"
    assert compute_budget_tier(1500, 500, 1500) == "medium"
    assert compute_budget_tier(1501, 500, 1500) == "high"
    assert compute_budget_tier(6000, 500, 1500) == "high"


def test_parse_votes():
    assert parse_votes(14720) == 14720
    assert parse_votes("5,200") == 5200
    assert parse_votes(0) == 0
    assert parse_votes(None) is None
    assert parse_votes(float("nan")) is None


def test_preprocess_record_valid():
    raw = {
        "name": "Truffles",
        "location": "Koramangala",
        "rate": "4.7/5",
        "approx_cost(for two people)": "900",
        "cuisines": "Cafe, Burger",
        "votes": 500,
    }
    rec = preprocess_record(raw)
    assert rec is not None
    assert isinstance(rec, Restaurant)
    assert rec.name == "Truffles"
    assert rec.location == "koramangala"
    assert rec.cost_for_two == 900
    assert rec.rating == 4.7
    assert rec.budget_tier == "medium"


def test_preprocess_record_missing_critical_fields():
    assert preprocess_record({"name": "No Loc", "location": ""}) is None
    assert preprocess_record({"name": None, "location": "Delhi"}) is None
    assert preprocess_record({"name": "   ", "location": "Delhi"}) is None


def test_preprocess_dataframe_with_sample_fixtures():
    fixtures_path = Path("tests/fixtures/sample_restaurants.json")
    assert fixtures_path.exists()

    with open(fixtures_path) as f:
        data = json.load(f)

    raw_df = pd.DataFrame(data)
    assert len(raw_df) == 8  # 8 fixture items

    clean_df, restaurants = preprocess_dataframe(raw_df)

    # Missing name (1) and missing location (1) should be dropped
    # Truffles duplicate (1) should be deduplicated
    # Remaining: Truffles (1), Corner House (1), Le Cirque (1), Brew & Bite (1), Highway Diner (1) = 5
    assert len(clean_df) == 5
    assert len(restaurants) == 5

    names = [r.name for r in restaurants]
    assert "Truffles" in names
    assert "Corner House Ice Cream" in names
    assert "Le Cirque Signature" in names
    assert "Brew & Bite" in names
    assert "Highway Diner" in names

    # Check unrated restaurant handling ("NEW" -> 0.0)
    brew_and_bite = next(r for r in restaurants if r.name == "Brew & Bite")
    assert brew_and_bite.rating == 0.0
    assert brew_and_bite.budget_tier == "low"  # 500 is low

    # Check comma cost handling ("6,000" -> 6000, high)
    le_cirque = next(r for r in restaurants if r.name == "Le Cirque Signature")
    assert le_cirque.cost_for_two == 6000
    assert le_cirque.budget_tier == "high"

    # Check all are Restaurant models
    for r in restaurants:
        assert isinstance(r, Restaurant)
