import json
from typing import Any

from app.models.preferences import UserPreferences
from app.models.restaurant import Restaurant

SYSTEM_PROMPT_TEMPLATE = """You are an expert AI restaurant recommendation assistant inspired by Zomato, specializing in dining suggestions across Bangalore and India.

Your objective is to review a provided list of candidate restaurants and select the best personalized recommendations for the user.

CRITICAL RULES:
1. You must ONLY recommend restaurants from the provided [Candidate Restaurants] list.
2. NEVER invent, hallucinate, or recommend any restaurant not explicitly present in the list.
3. Match the exact restaurant name as provided in the candidate list.
4. Rank the chosen restaurants from best to worst fit based on the user's preferences.
5. For each recommendation, provide an insightful 1-2 sentence explanation specifically addressing why it fits the user's cuisine, budget, rating, and any custom preferences.
6. Return your response STRICTLY as a valid JSON object matching the schema below. Do not wrap in markdown or include conversational text outside the JSON.

REQUIRED JSON OUTPUT SCHEMA:
{
  "recommendations": [
    {
      "name": "Exact Restaurant Name",
      "cuisine": "Primary Cuisine or Dish",
      "rating": 4.5,
      "estimated_cost": 800,
      "explanation": "Why this restaurant is a great match for the user's preferences."
    }
  ],
  "summary": "A concise 1-2 sentence overview of your top recommendations."
}"""


class PromptBuilder:
    """Builds structured system and user prompts for Groq LLM reasoning."""

    @staticmethod
    def build_system_prompt() -> str:
        return SYSTEM_PROMPT_TEMPLATE

    @staticmethod
    def build_user_prompt(preferences: UserPreferences, candidates: list[Restaurant]) -> str:
        # Prepare compact representation of candidates to save tokens
        candidates_data: list[dict[str, Any]] = []
        for c in candidates:
            candidates_data.append(
                {
                    "name": c.name,
                    "location": c.location,
                    "cuisines": c.cuisines,
                    "cost_for_two": c.cost_for_two,
                    "budget_tier": c.budget_tier,
                    "rating": c.rating,
                    "votes": c.votes or 0,
                    "rest_type": c.rest_type,
                }
            )

        candidates_json = json.dumps(candidates_data, indent=2)

        prompt_lines = [
            "### USER PREFERENCES",
            f"- Location: {preferences.location}",
            f"- Budget Tier: {preferences.budget}",
            f"- Preferred Cuisine: {preferences.cuisine}",
            f"- Minimum Rating: {preferences.min_rating}",
            f"- Additional Preferences: {preferences.additional_preferences or 'None'}",
            f"- Requested Recommendations Count (top_k): {preferences.top_k}",
            "",
            "### CANDIDATE RESTAURANTS",
            candidates_json,
            "",
            "### YOUR TASK",
            f"1. Select the top {preferences.top_k} restaurants that best satisfy the user's preferences.",
            "2. Rank them by relevance (rank 1 = best fit).",
            "3. Write a personalized 1-2 sentence explanation for each choice.",
            "4. Provide a brief 1-sentence summary of the selection.",
            "5. Output valid JSON according to the required schema.",
        ]

        return "\n".join(prompt_lines)

    @classmethod
    def build_prompts(
        cls, preferences: UserPreferences, candidates: list[Restaurant]
    ) -> tuple[str, str]:
        """Return (system_prompt, user_prompt)."""
        return cls.build_system_prompt(), cls.build_user_prompt(preferences, candidates)
