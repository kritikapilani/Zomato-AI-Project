import json
import logging
import re
from typing import Any

from app.models.preferences import UserPreferences
from app.models.response import Recommendation, RecommendationResponse
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)


def extract_json_from_text(raw_text: str) -> dict[str, Any]:
    """
    Extract and parse JSON from raw LLM output, handling markdown code fences
    and leading/trailing conversational text.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Empty response text received from LLM.")

    text = raw_text.strip()

    # Step 1: Remove markdown code fences if present (```json ... ``` or ``` ... ```)
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
    match = fence_pattern.search(text)
    if match:
        text = match.group(1).strip()

    # Step 2: Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 3: Find outermost curly braces {...}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate_json = text[start : end + 1]
        try:
            return json.loads(candidate_json)
        except json.JSONDecodeError as err:
            raise ValueError(f"Extracted JSON block was invalid: {err}") from err

    raise ValueError("No valid JSON object found in response.")


class ResponseParser:
    """
    Parses, validates, and enriches Groq LLM responses.
    Strictly filters out hallucinations and enriches ground truth data.
    """

    @classmethod
    def parse_and_validate(
        cls,
        raw_text: str,
        candidates: list[Restaurant],
        preferences: UserPreferences,
    ) -> RecommendationResponse:
        """
        Parse LLM JSON, enforce anti-hallucination rules against the candidate pool,
        enrich ground-truth attributes, and construct RecommendationResponse.
        """
        data = extract_json_from_text(raw_text)

        raw_recs = (
            data.get("recommendations")
            or data.get("results")
            or data.get("restaurants")
            or []
        )
        summary = data.get("summary")

        # Build candidate lookup by lowercase name
        candidate_map: dict[str, Restaurant] = {
            c.name.strip().lower(): c for c in candidates
        }

        validated_recommendations: list[Recommendation] = []
        seen_names: set[str] = set()
        hallucinations_count = 0

        for item in raw_recs:
            if not isinstance(item, dict):
                continue

            rec_name = str(item.get("name", "")).strip()
            norm_name = rec_name.lower()

            # Anti-hallucination check: match against candidate pool
            matched_candidate = candidate_map.get(norm_name)

            # Fallback substring match if LLM slightly altered the name
            if not matched_candidate:
                for c_name, c_obj in candidate_map.items():
                    if norm_name and (norm_name in c_name or c_name in norm_name):
                        matched_candidate = c_obj
                        break

            if not matched_candidate:
                logger.warning(
                    "Dropping hallucinated restaurant not present in candidates: '%s'",
                    rec_name,
                )
                hallucinations_count += 1
                continue

            # Deduplicate by canonical candidate name
            if matched_candidate.name.lower() in seen_names:
                continue
            seen_names.add(matched_candidate.name.lower())

            # Explanation from LLM
            explanation = str(item.get("explanation", "")).strip()
            if not explanation:
                explanation = (
                    f"Recommended for its {matched_candidate.rating}★ rating and "
                    f"{', '.join(matched_candidate.cuisines)} in {matched_candidate.location}."
                )

            # Ground-truth attributes from candidate record
            cuisine_val = str(item.get("cuisine", "")).strip()
            if not cuisine_val or cuisine_val.lower() == "various":
                cuisine_val = ", ".join(matched_candidate.cuisines)

            rec = Recommendation(
                name=matched_candidate.name,
                cuisine=cuisine_val,
                rating=matched_candidate.rating,
                estimated_cost=matched_candidate.cost_for_two,
                explanation=explanation,
            )
            validated_recommendations.append(rec)

            if len(validated_recommendations) >= preferences.top_k:
                break

        # If LLM under-returned or hallucinations were dropped, top up from candidate pool
        if len(validated_recommendations) < preferences.top_k:
            for c in candidates:
                if c.name.lower() not in seen_names:
                    seen_names.add(c.name.lower())
                    validated_recommendations.append(
                        Recommendation(
                            name=c.name,
                            cuisine=", ".join(c.cuisines),
                            rating=c.rating,
                            estimated_cost=c.cost_for_two,
                            explanation=(
                                f"Top pick in {c.location} with {c.rating}★ rating "
                                f"fitting your {c.budget_tier} budget preference."
                            ),
                        )
                    )
                    if len(validated_recommendations) >= preferences.top_k:
                        break

        if not summary:
            summary = (
                f"Here are the top {len(validated_recommendations)} restaurant recommendations "
                f"in {preferences.location} matching your dining preferences."
            )

        metadata = {
            "source": "groq",
            "candidates_considered": len(candidates),
            "hallucinations_dropped": hallucinations_count,
            "preferences": preferences.model_dump(),
        }

        return RecommendationResponse(
            recommendations=validated_recommendations,
            summary=summary,
            metadata=metadata,
        )

    @classmethod
    def generate_fallback_response(
        cls,
        candidates: list[Restaurant],
        preferences: UserPreferences,
        reason: str,
    ) -> RecommendationResponse:
        """
        Deterministic fallback response generator when Groq is unreachable, times out,
        or response parsing fails.
        """
        top_candidates = candidates[: preferences.top_k]
        recommendations: list[Recommendation] = []

        for idx, c in enumerate(top_candidates, start=1):
            votes_info = f" ({c.votes} reviews)" if c.votes else ""
            explanation = (
                f"Ranked #{idx} in {c.location}: {c.rating}★ rating{votes_info}, "
                f"serving {', '.join(c.cuisines)} for approx ₹{c.cost_for_two} for two."
            )
            recommendations.append(
                Recommendation(
                    name=c.name,
                    cuisine=", ".join(c.cuisines),
                    rating=c.rating,
                    estimated_cost=c.cost_for_two,
                    explanation=explanation,
                )
            )

        summary = (
            f"Here are the top {len(recommendations)} dining recommendations in {preferences.location} "
            f"ranked by rating and popularity."
        )

        metadata = {
            "source": "fallback",
            "fallback_reason": reason,
            "candidates_considered": len(candidates),
            "preferences": preferences.model_dump(),
        }

        return RecommendationResponse(
            recommendations=recommendations,
            summary=summary,
            metadata=metadata,
        )
