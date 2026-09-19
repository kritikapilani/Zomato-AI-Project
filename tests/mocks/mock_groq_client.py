import json
from typing import Any

from app.services.groq_client import GroqClientInterface


class MockGroqClient:
    """Configurable mock Groq client for unit testing."""

    def __init__(
        self,
        response_data: dict[str, Any] | None = None,
        raw_text: str | None = None,
        should_timeout: bool = False,
        rate_limit_attempts: int = 0,
    ):
        self.response_data = response_data
        self.raw_text = raw_text
        self.should_timeout = should_timeout
        self.rate_limit_attempts = rate_limit_attempts
        self.call_count = 0
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
    ) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        if self.should_timeout:
            raise TimeoutError("Groq request timed out after 30 seconds.")

        if self.rate_limit_attempts > 0:
            self.rate_limit_attempts -= 1
            import httpx
            import groq

            fake_request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
            fake_response = httpx.Response(status_code=429, request=fake_request)
            raise groq.RateLimitError("Rate limit exceeded", response=fake_response, body=None)

        if self.raw_text is not None:
            return self.raw_text

        if self.response_data is not None:
            return json.dumps(self.response_data)

        # Default mock response
        default_resp = {
            "recommendations": [
                {
                    "name": "Truffles",
                    "cuisine": "Burger, American",
                    "rating": 4.7,
                    "estimated_cost": 900,
                    "explanation": "Famous for its juicy burgers and lively cafe ambiance in Koramangala.",
                }
            ],
            "summary": "Top recommended cafe in Koramangala.",
        }
        return json.dumps(default_resp)
