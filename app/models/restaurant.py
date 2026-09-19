from pydantic import BaseModel, Field

from app.models.preferences import BudgetTier


class Restaurant(BaseModel):
    name: str
    location: str
    cuisines: list[str]
    cost_for_two: int = Field(ge=0)
    rating: float = Field(ge=0, le=5)
    votes: int | None = Field(default=None, ge=0)
    address: str | None = None
    rest_type: str | None = None
    budget_tier: BudgetTier
