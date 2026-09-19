import pytest

from app.config import Settings
from app.services.groq_client import GroqLLMClient
from tests.mocks.mock_groq_client import MockGroqClient


def test_mock_groq_client_default_completion():
    client = MockGroqClient()
    res = client.complete("System prompt", "User prompt")
    assert "recommendations" in res
    assert "Truffles" in res
    assert client.call_count == 1
    assert client.last_system_prompt == "System prompt"
    assert client.last_user_prompt == "User prompt"


def test_mock_groq_client_custom_data():
    custom_data = {"recommendations": [{"name": "Custom Spot"}], "summary": "Custom"}
    client = MockGroqClient(response_data=custom_data)
    res = client.complete("System", "User")
    assert "Custom Spot" in res


def test_mock_groq_client_timeout():
    client = MockGroqClient(should_timeout=True)
    with pytest.raises(TimeoutError, match="timed out"):
        client.complete("System", "User")


def test_groq_llm_client_requires_api_key():
    settings = Settings(groq_api_key="")
    with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
        GroqLLMClient(settings)


def test_groq_llm_client_initializes_with_key():
    settings = Settings(groq_api_key="gsk_valid_mock_key_for_testing")
    client = GroqLLMClient(settings)
    assert client.model == settings.groq_model
    assert client.temperature == settings.groq_temperature
