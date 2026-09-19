import logging
import math
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant
from app.services.dataset_loader import DatasetLoader, get_dataset_loader

logger = logging.getLogger(__name__)

MIN_CANDIDATES_THRESHOLD = 3


class FilterResult(BaseModel):
    """Result of filtering candidate restaurants for LLM reasoning."""

    candidates: list[Restaurant]
    total_matching: int
    filters_applied: dict[str, Any]
    relaxation_applied: list[str] = Field(default_factory=list)
    message: str | None = None


def calculate_candidate_score(restaurant: Restaurant) -> float:
    """
    Calculate composite ranking score for deterministic pre-sorting.
    Combines rating with log-scaled vote count:
    Score = rating * (1.0 + min(log10(votes + 10) / 4.0, 1.0))
    """
    votes = restaurant.votes or 0
    vote_factor = 1.0 + min(math.log10(votes + 10) / 4.0, 1.0)
    return round(restaurant.rating * vote_factor, 4)


class FilteringService:
    """
    Rule-based deterministic candidate generation and filtering service.
    Narrows the full dataset down to a Groq-ready shortlist based on user preferences.
    """

    def __init__(
        self,
        loader: DatasetLoader | None = None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.loader = loader or get_dataset_loader(self.settings)

    def _matches_location(self, restaurant: Restaurant, target_location: str) -> bool:
        """Case-insensitive substring match on locality or address."""
        if not target_location:
            return True
        norm_target = target_location.strip().lower()
        if norm_target in restaurant.location.lower():
            return True
        if restaurant.address and norm_target in restaurant.address.lower():
            return True
        return False

    def _matches_cuisine(self, restaurant: Restaurant, target_cuisine: str, exact_token: bool = False) -> bool:
        """
        Check if restaurant offers the requested cuisine.
        Supports comma-separated user inputs (e.g., 'Italian, Pizza').
        Matches all cuisines if target_cuisine is empty or 'any'/'all'.
        """
        if not target_cuisine:
            return True

        norm_target = target_cuisine.strip().lower()
        if norm_target in ("any", "all", "*", "anything", "all cuisines"):
            return True

        # Split user query into individual cuisine tokens
        user_cuisines = [c.strip().lower() for c in target_cuisine.split(",") if c.strip()]
        if not user_cuisines:
            return True

        restaurant_cuisines = [c.lower() for c in restaurant.cuisines]

        for user_c in user_cuisines:
            for rest_c in restaurant_cuisines:
                if exact_token:
                    if user_c == rest_c:
                        return True
                else:
                    if user_c in rest_c or rest_c in user_c:
                        return True
        return False

    def _matches_keywords(self, restaurant: Restaurant, keywords: str | None) -> bool:
        """
        Check if free-text keywords match restaurant attributes
        (name, rest_type, cuisines, address).
        """
        if not keywords:
            return True
        tokens = [k.strip().lower() for k in keywords.split() if k.strip()]
        if not tokens:
            return True

        search_corpus = " ".join(
            filter(
                None,
                [
                    restaurant.name.lower(),
                    restaurant.rest_type.lower() if restaurant.rest_type else "",
                    " ".join(c.lower() for c in restaurant.cuisines),
                    restaurant.address.lower() if restaurant.address else "",
                ],
            )
        )

        # Match if any meaningful token appears in restaurant details
        return any(token in search_corpus for token in tokens)

    def _apply_filters(
        self,
        pool: list[Restaurant],
        location: str,
        cuisine: str,
        min_rating: float,
        budget: str | None,
        additional_preferences: str | None = None,
    ) -> list[Restaurant]:
        """Apply strict filters on a given pool of restaurants."""
        results = []
        for r in pool:
            # 1. Location
            if not self._matches_location(r, location):
                continue
            # 2. Cuisine
            if not self._matches_cuisine(r, cuisine):
                continue
            # 3. Minimum rating
            if r.rating < min_rating:
                continue
            # 4. Budget tier (if specified)
            if budget and r.budget_tier != budget:
                continue
            # 5. Additional keywords
            if additional_preferences and not self._matches_keywords(r, additional_preferences):
                continue
            results.append(r)
        return results

    def _rank_and_cap(self, candidates: list[Restaurant], limit: int) -> list[Restaurant]:
        """
        Pre-sort candidates by composite score (rating + votes), breaking ties
        by rating, votes, and name. Caps output at limit.
        """
        sorted_candidates = sorted(
            candidates,
            key=lambda r: (
                calculate_candidate_score(r),
                r.rating,
                r.votes or 0,
                r.name,
            ),
            reverse=True,
        )
        return sorted_candidates[:limit]

    def filter(
        self,
        preferences: UserPreferences,
        pool: list[Restaurant] | None = None,
    ) -> FilterResult:
        """
        Filter and rank candidate restaurants based on user preferences.
        Triggers staged filter relaxation if strict matches are below threshold (< 3).
        """
        candidates_pool = pool if pool is not None else self.loader.get_restaurants()
        cap_limit = preferences.top_k * 6  # give LLM up to 6x candidate options
        cap_limit = min(cap_limit, self.settings.max_candidates_for_llm)
        cap_limit = max(cap_limit, preferences.top_k)

        filters_applied = {
            "location": preferences.location,
            "cuisine": preferences.cuisine,
            "min_rating": preferences.min_rating,
            "budget": preferences.budget,
            "additional_preferences": preferences.additional_preferences,
        }

        # Step 1: Strict filtering
        matches = self._apply_filters(
            candidates_pool,
            location=preferences.location,
            cuisine=preferences.cuisine,
            min_rating=preferences.min_rating,
            budget=preferences.budget,
            additional_preferences=preferences.additional_preferences,
        )

        # If keyword filter was used and yielded 0 matches, retry without keyword filter first (F-15)
        if len(matches) < MIN_CANDIDATES_THRESHOLD and preferences.additional_preferences:
            without_keywords = self._apply_filters(
                candidates_pool,
                location=preferences.location,
                cuisine=preferences.cuisine,
                min_rating=preferences.min_rating,
                budget=preferences.budget,
                additional_preferences=None,
            )
            if len(without_keywords) >= len(matches):
                matches = without_keywords

        relaxation_applied: list[str] = []
        current_budget: str | None = preferences.budget
        current_cuisine: str = preferences.cuisine
        current_min_rating: float = preferences.min_rating

        # Step 2: Staged relaxation if matches < 3
        # Relaxation Step A: Relax Budget
        if len(matches) < MIN_CANDIDATES_THRESHOLD and current_budget is not None:
            relaxed_budget_matches = self._apply_filters(
                candidates_pool,
                location=preferences.location,
                cuisine=current_cuisine,
                min_rating=current_min_rating,
                budget=None,  # allow any budget tier
            )
            if len(relaxed_budget_matches) > len(matches):
                matches = relaxed_budget_matches
                current_budget = None
                relaxation_applied.append("budget")

        # Relaxation Step B: Relax Cuisine
        if len(matches) < MIN_CANDIDATES_THRESHOLD and current_cuisine:
            # Try relaxing to any cuisine in the same location and rating
            relaxed_cuisine_matches = self._apply_filters(
                candidates_pool,
                location=preferences.location,
                cuisine="",  # allow any cuisine
                min_rating=current_min_rating,
                budget=current_budget,
            )
            if len(relaxed_cuisine_matches) > len(matches):
                matches = relaxed_cuisine_matches
                current_cuisine = ""
                relaxation_applied.append("cuisine")

        # Relaxation Step C: Relax Rating
        while len(matches) < MIN_CANDIDATES_THRESHOLD and current_min_rating > 0.0:
            current_min_rating = max(0.0, round(current_min_rating - 0.5, 1))
            relaxed_rating_matches = self._apply_filters(
                candidates_pool,
                location=preferences.location,
                cuisine=current_cuisine,
                min_rating=current_min_rating,
                budget=current_budget,
            )
            if len(relaxed_rating_matches) > len(matches):
                matches = relaxed_rating_matches
                if "rating" not in relaxation_applied:
                    relaxation_applied.append("rating")

        total_matching = len(matches)
        ranked_candidates = self._rank_and_cap(matches, cap_limit)

        message = None
        if not ranked_candidates:
            message = (
                f"No restaurants found matching location '{preferences.location}'. "
                "Try searching for popular Bangalore localities such as Indiranagar, Koramangala, Whitefield, or Jayanagar."
            )
        elif relaxation_applied:
            message = (
                f"Expanded search by relaxing filters ({', '.join(relaxation_applied)}) "
                f"to find the best available matches in '{preferences.location}'."
            )

        return FilterResult(
            candidates=ranked_candidates,
            total_matching=total_matching,
            filters_applied=filters_applied,
            relaxation_applied=relaxation_applied,
            message=message,
        )


_default_filtering_service: FilteringService | None = None


def get_filtering_service(
    loader: DatasetLoader | None = None,
    settings: Settings | None = None,
) -> FilteringService:
    """Get or create singleton FilteringService, or fresh instance if custom loader/settings passed."""
    global _default_filtering_service
    if loader is not None or settings is not None:
        return FilteringService(loader=loader, settings=settings)
    if _default_filtering_service is None:
        _default_filtering_service = FilteringService()
    return _default_filtering_service
