import logging
import math
import re
from typing import Any

import pandas as pd

from app.config import Settings, get_settings
from app.models.preferences import BudgetTier
from app.models.restaurant import Restaurant

logger = logging.getLogger(__name__)

# Precompiled regex for rating extraction (e.g. "4.1/5", "3.5", "-1.0")
RATING_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)")


def clean_text(value: Any) -> str | None:
    """Return stripped text, or None if empty, null, or NaN."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value).strip()
    return text if text else None


def parse_rating(value: Any) -> float:
    """
    Parse rating to a float clamped to [0.0, 5.0].
    Defaults to 0.0 for 'NEW', '-', None, NaN, or unparseable inputs.
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return 0.0
        return max(0.0, min(5.0, float(value)))

    text = str(value).strip()
    if not text or text in ("NEW", "-", "nan", "None"):
        return 0.0

    match = RATING_PATTERN.search(text)
    if match:
        try:
            val = float(match.group(1))
            return max(0.0, min(5.0, val))
        except ValueError:
            return 0.0
    return 0.0


def parse_cost(value: Any) -> int:
    """
    Parse cost to an integer (INR).
    Strips commas, currency symbols, and non-numeric suffixes.
    Returns 0 if missing, NaN, or unparseable.
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return 0
        return max(0, int(value))

    text = str(value).strip()
    if not text or text in ("nan", "None", "-"):
        return 0

    # Remove commas and extract numeric sequence
    digits = re.sub(r"[^\d]", "", text)
    if digits:
        try:
            return max(0, int(digits))
        except ValueError:
            return 0
    return 0


def parse_cuisines(value: Any) -> list[str]:
    """
    Split comma-, pipe-, or slash-delimited cuisine string into a cleaned list of cuisines.
    """
    if value is None:
        return []
    if isinstance(value, float) and math.isnan(value):
        return []
    if isinstance(value, list):
        return [str(c).strip() for c in value if str(c).strip()]

    text = str(value).strip()
    if not text or text in ("nan", "None"):
        return []

    # Replace pipe or semicolon with comma
    normalized = re.sub(r"[|;]", ",", text)
    tokens = [c.strip() for c in normalized.split(",") if c.strip()]
    return tokens


def normalize_location(value: Any) -> str:
    """Normalize location string for consistent indexing and case-insensitive matching."""
    cleaned = clean_text(value)
    return cleaned.lower() if cleaned else ""


def compute_budget_tier(
    cost_for_two: int,
    budget_low_max: int = 500,
    budget_medium_max: int = 1500,
) -> BudgetTier:
    """
    Compute budget tier from cost for two:
    - <= budget_low_max: 'low'
    - <= budget_medium_max: 'medium'
    - > budget_medium_max: 'high'
    """
    if cost_for_two <= budget_low_max:
        return "low"
    if cost_for_two <= budget_medium_max:
        return "medium"
    return "high"


def parse_votes(value: Any) -> int | None:
    """Parse vote count into a non-negative integer or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return None
        return max(0, int(value))
    text = clean_text(value)
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def preprocess_record(raw: dict[str, Any], settings: Settings | None = None) -> Restaurant | None:
    """
    Transform a raw dictionary into a validated Restaurant model instance.
    Returns None if critical fields (name or location) are missing.
    """
    cfg = settings or get_settings()

    raw_name = raw.get("name")
    name = clean_text(raw_name)
    if not name:
        return None

    raw_location = raw.get("location")
    location = clean_text(raw_location)
    if not location:
        return None

    norm_location = normalize_location(location)
    rating = parse_rating(raw.get("rate") if "rate" in raw else raw.get("rating"))
    cost_val = (
        raw.get("approx_cost(for two people)")
        if "approx_cost(for two people)" in raw
        else raw.get("cost_for_two")
    )
    cost_for_two = parse_cost(cost_val)
    cuisines = parse_cuisines(raw.get("cuisines"))
    votes = parse_votes(raw.get("votes"))
    address = clean_text(raw.get("address"))
    rest_type = clean_text(raw.get("rest_type"))

    budget_tier = compute_budget_tier(
        cost_for_two,
        budget_low_max=cfg.budget_low_max,
        budget_medium_max=cfg.budget_medium_max,
    )

    return Restaurant(
        name=name,
        location=norm_location,
        cuisines=cuisines,
        cost_for_two=cost_for_two,
        rating=rating,
        votes=votes,
        address=address,
        rest_type=rest_type,
        budget_tier=budget_tier,
    )


def preprocess_dataframe(
    df: pd.DataFrame, settings: Settings | None = None
) -> tuple[pd.DataFrame, list[Restaurant]]:
    """
    Clean, validate, and convert a raw pandas DataFrame into:
    1. A cleaned pandas DataFrame with standardized schema
    2. A list of validated Restaurant Pydantic models

    Filters out missing names/locations and deduplicates identical records.
    """
    cfg = settings or get_settings()
    initial_count = len(df)

    # Standardize column lookup
    col_map = {}
    for col in df.columns:
        norm_col = col.strip().lower()
        if norm_col in ("name", "restaurant_name"):
            col_map["name"] = col
        elif norm_col in ("location", "locality", "city"):
            col_map["location"] = col
        elif norm_col in ("rate", "rating"):
            col_map["rate"] = col
        elif norm_col in ("votes", "vote_count"):
            col_map["votes"] = col
        elif norm_col in ("cuisines", "cuisine"):
            col_map["cuisines"] = col
        elif "approx_cost" in norm_col or "cost_for_two" in norm_col:
            col_map["cost"] = col
        elif norm_col == "address":
            col_map["address"] = col
        elif norm_col in ("rest_type", "type"):
            col_map["rest_type"] = col

    # Check required columns
    if "name" not in col_map or "location" not in col_map:
        raise ValueError(
            f"Dataset missing required columns: name and/or location. Found columns: {list(df.columns)}"
        )

    records: list[dict[str, Any]] = []
    restaurants: list[Restaurant] = []

    # Drop obvious nulls in name and location first
    name_col = col_map["name"]
    loc_col = col_map["location"]
    rate_col = col_map.get("rate")
    cost_col = col_map.get("cost")
    cuisines_col = col_map.get("cuisines")
    votes_col = col_map.get("votes")
    addr_col = col_map.get("address")
    rest_type_col = col_map.get("rest_type")

    filtered_df = df.dropna(subset=[name_col, loc_col]).copy()

    for _, row in filtered_df.iterrows():
        raw_name = row.get(name_col)
        name = clean_text(raw_name)
        if not name:
            continue

        raw_loc = row.get(loc_col)
        norm_loc = normalize_location(raw_loc)
        if not norm_loc:
            continue

        rating = parse_rating(row.get(rate_col)) if rate_col else 0.0
        cost_for_two = parse_cost(row.get(cost_col)) if cost_col else 0
        cuisines = parse_cuisines(row.get(cuisines_col)) if cuisines_col else []
        votes = parse_votes(row.get(votes_col)) if votes_col else None
        address = clean_text(row.get(addr_col)) if addr_col else None
        rest_type = clean_text(row.get(rest_type_col)) if rest_type_col else None

        budget_tier = compute_budget_tier(
            cost_for_two,
            budget_low_max=cfg.budget_low_max,
            budget_medium_max=cfg.budget_medium_max,
        )

        rec = {
            "name": name,
            "location": norm_loc,
            "cuisines": cuisines,
            "cost_for_two": cost_for_two,
            "rating": rating,
            "votes": votes,
            "address": address,
            "rest_type": rest_type,
            "budget_tier": budget_tier,
        }
        records.append(rec)

    if not records:
        logger.warning("No valid records found after preprocessing.")
        empty_df = pd.DataFrame(
            columns=[
                "name",
                "location",
                "cuisines",
                "cost_for_two",
                "rating",
                "votes",
                "address",
                "rest_type",
                "budget_tier",
            ]
        )
        return empty_df, []

    processed_df = pd.DataFrame(records)

    # Deduplicate on (name, location, address)
    processed_df.drop_duplicates(subset=["name", "location", "address"], inplace=True)
    processed_df.reset_index(drop=True, inplace=True)

    # Build Pydantic models
    for row_dict in processed_df.to_dict(orient="records"):
        for key in ("votes", "address", "rest_type"):
            val = row_dict.get(key)
            if val is not None and isinstance(val, float) and math.isnan(val):
                row_dict[key] = None
        if row_dict.get("votes") is not None:
            row_dict["votes"] = int(row_dict["votes"])
        restaurants.append(Restaurant(**row_dict))

    logger.info(
        "Preprocessing complete: %d raw rows -> %d filtered -> %d final deduplicated records.",
        initial_count,
        len(records),
        len(restaurants),
    )

    return processed_df, restaurants
