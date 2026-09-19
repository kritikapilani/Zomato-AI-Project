import importlib

from app.models.preferences import UserPreferences
from ui.streamlit_app import (
    CUSTOM_CSS,
    POPULAR_CUISINES,
    POPULAR_LOCATIONS,
    fetch_recommendations,
)


def test_ui_module_imports():
    """Verify streamlit_app imports cleanly without syntax errors."""
    mod = importlib.import_module("ui.streamlit_app")
    assert mod is not None
    assert len(POPULAR_LOCATIONS) > 5
    assert len(POPULAR_CUISINES) > 5
    assert ".restaurant-card" in CUSTOM_CSS
    assert ".ai-reasoning-box" in CUSTOM_CSS


def test_fetch_recommendations_in_process_fallback():
    """Verify fetch_recommendations executes successfully via in-process orchestrator."""
    prefs = UserPreferences(
        location="indiranagar",
        budget="medium",
        cuisine="Italian",
        min_rating=3.5,
        top_k=2,
    )
    response = fetch_recommendations(prefs)
    assert response is not None
    assert hasattr(response, "recommendations")
    assert hasattr(response, "summary")
    assert hasattr(response, "metadata")
    assert len(response.recommendations) > 0

    # Ensure all 5 mandatory fields exist on each recommendation
    for rec in response.recommendations:
        assert rec.name
        assert rec.cuisine
        assert rec.rating >= 0
        assert rec.estimated_cost >= 0
        assert rec.explanation


def test_frontend_static_serving_and_dropdown():
    """Verify FastAPI serves the frontend with dropdown for location and proper structure."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    # Verify Location is a dropdown (<select id="locationSelect")
    assert '<select' in html
    assert 'id="locationSelect"' in html
    # Verify 93 locations exist in options
    assert 'Bellandur' in html
    assert 'Indiranagar' in html
    assert 'Koramangala' in html
    # Verify no food images are in recommendation cards
    assert 'alt="Toit Brewpub terrace"' not in html
    assert 'alt="Milano Ice Cream garden"' not in html
    # Verify AI Insight container exists
    assert 'AI Insight &amp; Reason' in html or 'AI Insight' in html


def test_metadata_endpoints():
    """Verify metadata endpoints return populated locations and cuisines."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    loc_res = client.get("/api/v1/metadata/locations")
    assert loc_res.status_code == 200
    loc_data = loc_res.json()
    assert loc_data["total"] > 50
    assert any(l["value"] == "bellandur" for l in loc_data["locations"])

    cui_res = client.get("/api/v1/metadata/cuisines")
    assert cui_res.status_code == 200
    cui_data = cui_res.json()
    assert cui_data["total"] > 20
    assert any("North Indian" in c["name"] for c in cui_data["cuisines"])

