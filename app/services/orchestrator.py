import logging
import time
from typing import Any

from app.config import Settings, get_settings
from app.models.preferences import UserPreferences
from app.models.response import RecommendationResponse
from app.services.dataset_loader import DatasetLoader, get_dataset_loader
from app.services.filtering import FilteringService, get_filtering_service
from app.services.groq_client import GroqClientInterface
from app.services.prompt_builder import PromptBuilder
from app.services.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class RecommendationOrchestrator:
    """
    Orchestrates the retrieve-then-reason recommendation pipeline:
    1. Ensures preprocessed dataset is loaded
    2. Runs deterministic multi-criteria filtering & pre-sorting
    3. Short-circuits zero-candidate scenarios (bypassing LLM)
    4. Builds structured prompts with anti-hallucination constraints
    5. Invokes Groq LLM (or deterministic fallback if unconfigured/failing)
    6. Parses, validates, and enriches recommendations
    7. Attaches execution telemetry to metadata
    """

    def __init__(
        self,
        settings: Settings | None = None,
        loader: DatasetLoader | None = None,
        filtering_service: FilteringService | None = None,
        groq_client: GroqClientInterface | None = None,
    ):
        self.settings = settings or get_settings()
        self.loader = loader or get_dataset_loader(self.settings)
        self.filtering_service = filtering_service or FilteringService(
            loader=self.loader, settings=self.settings
        )
        self.groq_client = groq_client

    def recommend(self, preferences: UserPreferences) -> RecommendationResponse:
        start_time = time.perf_counter()
        logger.info(
            "Starting recommendation pipeline for preferences: location='%s', budget='%s', cuisine='%s', top_k=%d",
            preferences.location,
            preferences.budget,
            preferences.cuisine,
            preferences.top_k,
        )

        # Step 1: Ensure dataset is loaded
        if not self.loader.is_loaded:
            self.loader.load()

        # Step 2: Apply deterministic filtering and pre-sorting
        filter_result = self.filtering_service.filter(preferences)
        candidates = filter_result.candidates

        # Step 3: Zero matches short-circuit (saves LLM call and latency)
        if not candidates:
            message = (
                filter_result.message
                or f"No restaurants found matching location '{preferences.location}' and cuisine '{preferences.cuisine}'."
            )
            logger.info("Zero candidate matches found. Short-circuiting LLM invocation.")
            empty_resp = RecommendationResponse.empty(preferences, message)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            empty_resp.metadata.update(
                {
                    "total_matching": 0,
                    "candidates_considered": 0,
                    "relaxation_applied": filter_result.relaxation_applied,
                    "latency_ms": elapsed_ms,
                    "source": "filtering_short_circuit",
                }
            )
            return empty_resp

        # Step 4: Build prompts
        system_prompt, user_prompt = PromptBuilder.build_prompts(preferences, candidates)

        # Step 5: Groq LLM Reasoning or Fallback
        response: RecommendationResponse
        llm_source = "groq"
        model_name = self.settings.groq_model

        if self.groq_client is None:
            logger.info("Groq client not configured; invoking deterministic fallback generator.")
            response = ResponseParser.generate_fallback_response(
                candidates,
                preferences,
                reason="GROQ_API_KEY is not configured. Displaying top candidates based on ratings and reviews.",
            )
            llm_source = "fallback"
            model_name = "none"
        else:
            try:
                raw_llm_output = self.groq_client.complete(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=self.settings.groq_max_tokens,
                )
                response = ResponseParser.parse_and_validate(
                    raw_llm_output, candidates, preferences
                )
            except Exception as exc:
                logger.warning(
                    "Groq completion failed (%s); triggering deterministic fallback generator.",
                    exc,
                )
                response = ResponseParser.generate_fallback_response(
                    candidates,
                    preferences,
                    reason=f"LLM inference encountered an issue: {exc}. Displaying top candidates based on ratings.",
                )
                llm_source = "fallback"

        # Step 6: Telemetry and metadata enrichment
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.metadata.update(
            {
                "latency_ms": elapsed_ms,
                "candidates_considered": len(candidates),
                "total_matching": filter_result.total_matching,
                "filters_applied": filter_result.filters_applied,
                "relaxation_applied": filter_result.relaxation_applied,
                "source": llm_source,
                "model": model_name,
            }
        )

        logger.info(
            "Recommendation pipeline completed in %.2f ms. Returning %d recommendations.",
            elapsed_ms,
            len(response.recommendations),
        )
        return response
