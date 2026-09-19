from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Groq LLM
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    groq_max_tokens: int = Field(default=2048, ge=1)
    groq_timeout_seconds: int = Field(default=30, ge=1)

    # Dataset
    hf_dataset_name: str = "ManikaSaini/zomato-restaurant-recommendation"
    dataset_cache_path: str = "./data/restaurants.parquet"

    # Filtering
    max_candidates_for_llm: int = Field(default=30, ge=1)
    budget_low_max: int = Field(default=500, ge=0)
    budget_medium_max: int = Field(default=1500, ge=0)

    # App
    top_k_default: int = Field(default=5, ge=1, le=10)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @model_validator(mode="after")
    def validate_budget_thresholds(self) -> "Settings":
        if self.budget_low_max >= self.budget_medium_max:
            raise ValueError(
                "budget_low_max must be less than budget_medium_max "
                f"(got {self.budget_low_max} and {self.budget_medium_max})"
            )
        return self

    def require_groq_api_key(self) -> str:
        """Return the Groq API key or raise if missing (call before LLM usage)."""
        if not self.groq_api_key.strip():
            raise ValueError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add your Groq API key."
            )
        return self.groq_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
