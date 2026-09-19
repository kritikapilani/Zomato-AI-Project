import logging
import time
from typing import Protocol

import groq
from groq import Groq

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class GroqClientInterface(Protocol):
    """Interface protocol for Groq LLM client to support dependency injection and mocking."""

    def complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        ...


class GroqLLMClient:
    """
    Official Groq client wrapper with timeout, JSON formatting, and exponential backoff retries.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        api_key = self.settings.require_groq_api_key()
        self.client = Groq(
            api_key=api_key,
            timeout=float(self.settings.groq_timeout_seconds),
        )
        self.model = self.settings.groq_model
        self.temperature = self.settings.groq_temperature
        self.max_tokens = self.settings.groq_max_tokens

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        max_retries: int = 3,
    ) -> str:
        """
        Send chat completion request to Groq with exponential backoff on transient errors.
        Enforces response_format={"type": "json_object"}.
        """
        tokens = max_tokens or self.max_tokens
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Sending completion request to Groq (model: %s, attempt %d/%d)...",
                    self.model,
                    attempt,
                    max_retries,
                )
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=tokens,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Groq returned empty completion content.")
                return content

            except (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError) as err:
                last_exc = err
                wait_seconds = 2 ** (attempt - 1)
                logger.warning(
                    "Groq transient error (attempt %d/%d: %s). Retrying in %ds...",
                    attempt,
                    max_retries,
                    err,
                    wait_seconds,
                )
                if attempt < max_retries:
                    time.sleep(wait_seconds)

            except Exception as err:
                logger.error("Groq non-retriable error: %s", err)
                raise

        raise RuntimeError(
            f"Groq API call failed after {max_retries} retries: {last_exc}"
        )


def get_groq_client(settings: Settings | None = None) -> GroqClientInterface:
    """Factory function to get configured Groq client."""
    return GroqLLMClient(settings)
