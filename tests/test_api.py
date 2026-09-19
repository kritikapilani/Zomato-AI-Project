from fastapi.testclient import TestClient

from app.api.dependencies import get_groq_client_optional
from app.main import app
from tests.mocks.mock_groq_client import MockGroqClient


def test_post_recommendations_valid():
    client = TestClient(app)
    payload = {
        "location": "indiranagar",
        "budget": "low",
        "cuisine": "Ice Cream",
        "min_rating": 3.5,
        "top_k": 3,
    }
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "recommendations" in data
    assert "summary" in data
    assert "metadata" in data
    assert len(data["recommendations"]) > 0

    rec = data["recommendations"][0]
    assert "name" in rec
    assert "cuisine" in rec
    assert "rating" in rec
    assert "estimated_cost" in rec
    assert "explanation" in rec


def test_post_recommendations_root_route():
    client = TestClient(app)
    payload = {
        "location": "koramangala",
        "budget": "medium",
        "cuisine": "Burger",
        "min_rating": 4.0,
        "top_k": 2,
    }
    response = client.post("/recommendations", json=payload)
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) > 0


def test_post_recommendations_zero_matches():
    client = TestClient(app)
    payload = {
        "location": "AtlantisUnderwaterCity",
        "budget": "low",
        "cuisine": "Seafood",
        "min_rating": 4.0,
    }
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["recommendations"] == []
    assert "AtlantisUnderwaterCity" in data["summary"]
    assert data["metadata"]["source"] == "filtering_short_circuit"


def test_post_recommendations_validation_errors():
    client = TestClient(app)

    # 1. Missing location
    resp1 = client.post("/api/v1/recommendations", json={"budget": "low", "cuisine": "Italian"})
    assert resp1.status_code == 422

    # 2. Whitespace-only location
    resp2 = client.post(
        "/api/v1/recommendations",
        json={"location": "   ", "budget": "low", "cuisine": "Italian"},
    )
    assert resp2.status_code == 422

    # 3. Rating above 5
    resp3 = client.post(
        "/api/v1/recommendations",
        json={"location": "Delhi", "budget": "low", "cuisine": "Italian", "min_rating": 6.0},
    )
    assert resp3.status_code == 422

    # 4. Invalid budget tier
    resp4 = client.post(
        "/api/v1/recommendations",
        json={"location": "Delhi", "budget": "ultra-luxury", "cuisine": "Italian"},
    )
    assert resp4.status_code == 422


def test_post_recommendations_with_mocked_groq():
    mock_data = {
        "recommendations": [
            {
                "name": "Corner House Ice Cream",
                "cuisine": "Ice Cream, Desserts",
                "rating": 4.6,
                "estimated_cost": 450,
                "explanation": "Famous for Death By Chocolate dessert in Indiranagar.",
            }
        ],
        "summary": "Best dessert spot in Indiranagar.",
    }
    mock_groq = MockGroqClient(response_data=mock_data)

    app.dependency_overrides[get_groq_client_optional] = lambda: mock_groq

    try:
        client = TestClient(app)
        payload = {
            "location": "indiranagar",
            "budget": "low",
            "cuisine": "Ice Cream",
            "min_rating": 4.0,
            "top_k": 1,
        }
        response = client.post("/api/v1/recommendations", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert len(data["recommendations"]) == 1
        assert data["recommendations"][0]["name"] == "Corner House Ice Cream"
        assert data["metadata"]["source"] == "groq"
        assert mock_groq.call_count == 1
    finally:
        app.dependency_overrides.clear()
