from typing import Literal

from pydantic import BaseModel, Field, field_validator

BudgetTier = Literal["low", "medium", "high"]


class UserPreferences(BaseModel):
    location: str
    budget: BudgetTier
    cuisine: str
    min_rating: float = Field(default=0.0, ge=0, le=5)
    additional_preferences: str | None = None
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("location", "cuisine")
    @classmethod
    def strip_and_validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("additional_preferences")
    @classmethod
    def strip_optional_preferences(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None
