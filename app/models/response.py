from typing import Any

from pydantic import BaseModel, Field

from app.models.preferences import UserPreferences


class Recommendation(BaseModel):
    name: str
    cuisine: str
    rating: float = Field(ge=0, le=5)
    estimated_cost: int = Field(ge=0)
    explanation: str


class RecommendationResponse(BaseModel):
    recommendations: list[Recommendation]
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def empty(cls, preferences: UserPreferences, message: str) -> "RecommendationResponse":
        return cls(
            recommendations=[],
            summary=message,
            metadata={
                "preferences": preferences.model_dump(),
                "candidates_considered": 0,
            },
        )
