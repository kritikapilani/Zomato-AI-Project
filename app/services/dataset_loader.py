import datetime
import logging
import math
import os
import threading
import time
from pathlib import Path
from typing import Any

import pandas as pd

from app.config import Settings, get_settings
from app.models.restaurant import Restaurant
from app.services.preprocessor import preprocess_dataframe

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Thread-safe loader and cache for the Zomato restaurant dataset.
    Loads from local Parquet cache if available (<100ms), otherwise downloads
    from Hugging Face Hub with retry, preprocesses, and caches to disk.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._lock = threading.Lock()
        self._df: pd.DataFrame | None = None
        self._restaurants: list[Restaurant] | None = None
        self._loaded_at: datetime.datetime | None = None
        self._source: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._df is not None and self._restaurants is not None

    def _load_from_parquet(self, path: Path) -> tuple[pd.DataFrame, list[Restaurant]] | None:
        """Attempt to load and validate dataset from local Parquet file."""
        if not path.exists():
            return None

        try:
            logger.info("Loading preprocessed dataset from Parquet cache: %s", path)
            df = pd.read_parquet(path)
            if df.empty:
                logger.warning("Parquet cache is empty: %s", path)
                return None

            # Validate expected columns
            required_cols = {"name", "location", "cuisines", "cost_for_two", "rating", "budget_tier"}
            if not required_cols.issubset(df.columns):
                logger.warning("Parquet cache missing required columns: %s", path)
                return None

            # Convert to list of Restaurant objects
            # Ensure cuisines column is converted to Python list[str] (handles numpy.ndarray)
            restaurants: list[Restaurant] = []
            for row in df.to_dict(orient="records"):
                c_val = row.get("cuisines")
                if hasattr(c_val, "__iter__") and not isinstance(c_val, (str, bytes)):
                    row["cuisines"] = [str(x) for x in c_val]
                elif c_val is None or (isinstance(c_val, float) and math.isnan(c_val)):
                    row["cuisines"] = []
                else:
                    row["cuisines"] = [str(c_val)]

                for key in ("votes", "address", "rest_type"):
                    val = row.get(key)
                    if val is not None and isinstance(val, float) and math.isnan(val):
                        row[key] = None
                if row.get("votes") is not None:
                    row["votes"] = int(row["votes"])

                restaurants.append(Restaurant(**row))

            logger.info("Successfully loaded %d restaurants from Parquet cache.", len(restaurants))
            return df, restaurants

        except Exception as exc:
            logger.warning("Failed to read Parquet cache (%s). Will re-fetch. Error: %s", path, exc)
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

    def _save_to_parquet(self, df: pd.DataFrame, path: Path) -> bool:
        """Save preprocessed DataFrame to local Parquet cache."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure cuisines list is stored as clean list
            df.to_parquet(path, index=False, engine="pyarrow")
            logger.info("Saved %d records to Parquet cache at %s", len(df), path)
            return True
        except PermissionError as pe:
            logger.warning("Permission denied saving Parquet cache to %s: %s", path, pe)
            return False
        except Exception as exc:
            logger.warning("Could not write Parquet cache (%s): %s", path, exc)
            return False

    def _download_from_huggingface(self, max_retries: int = 3) -> pd.DataFrame:
        """
        Download dataset from Hugging Face Hub with exponential backoff retries.
        """
        from datasets import load_dataset

        dataset_name = self.settings.hf_dataset_name
        logger.info("Downloading dataset '%s' from Hugging Face Hub...", dataset_name)

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                hf_data = load_dataset(dataset_name, split="train")
                raw_df = hf_data.to_pandas()
                logger.info(
                    "Downloaded %d raw rows from Hugging Face (attempt %d).",
                    len(raw_df),
                    attempt,
                )
                return raw_df
            except Exception as exc:
                last_error = exc
                wait_time = 2 ** (attempt - 1)
                logger.warning(
                    "Hugging Face download failed (attempt %d/%d): %s. Retrying in %ds...",
                    attempt,
                    max_retries,
                    exc,
                    wait_time,
                )
                if attempt < max_retries:
                    time.sleep(wait_time)

        raise RuntimeError(
            f"Failed to download dataset '{dataset_name}' from Hugging Face Hub after {max_retries} attempts: {last_error}"
        )

    def load(self, force_reload: bool = False) -> tuple[pd.DataFrame, list[Restaurant]]:
        """
        Load dataset into memory. Uses double-checked locking for thread safety.
        Checks local Parquet cache first; falls back to Hugging Face download.
        """
        if not force_reload and self.is_loaded:
            return self._df, self._restaurants  # type: ignore

        with self._lock:
            # Double check after acquiring lock
            if not force_reload and self.is_loaded:
                return self._df, self._restaurants  # type: ignore

            cache_path = Path(self.settings.dataset_cache_path)

            # Step 1: Check Parquet cache
            if not force_reload:
                cached = self._load_from_parquet(cache_path)
                if cached is not None:
                    self._df, self._restaurants = cached
                    self._loaded_at = datetime.datetime.now(datetime.timezone.utc)
                    self._source = "cache"
                    return self._df, self._restaurants

            # Step 2: Download and preprocess
            raw_df = self._download_from_huggingface()
            processed_df, restaurants = preprocess_dataframe(raw_df, self.settings)

            if processed_df.empty:
                raise ValueError("Preprocessing resulted in an empty restaurant dataset.")

            # Step 3: Save to Parquet cache
            self._save_to_parquet(processed_df, cache_path)

            self._df = processed_df
            self._restaurants = restaurants
            self._loaded_at = datetime.datetime.now(datetime.timezone.utc)
            self._source = "huggingface"

            return self._df, self._restaurants

    def load_from_dataframe(self, raw_df: pd.DataFrame) -> tuple[pd.DataFrame, list[Restaurant]]:
        """Convenience method for testing: preprocesses and sets in-memory cache directly."""
        with self._lock:
            processed_df, restaurants = preprocess_dataframe(raw_df, self.settings)
            self._df = processed_df
            self._restaurants = restaurants
            self._loaded_at = datetime.datetime.now(datetime.timezone.utc)
            self._source = "custom_dataframe"
            return self._df, self._restaurants

    def get_restaurants(self) -> list[Restaurant]:
        """Return cached restaurants, loading if necessary."""
        if not self.is_loaded:
            self.load()
        return self._restaurants or []

    def get_dataframe(self) -> pd.DataFrame:
        """Return cached DataFrame, loading if necessary."""
        if not self.is_loaded:
            self.load()
        return self._df if self._df is not None else pd.DataFrame()

    def get_status(self) -> dict[str, Any]:
        """Return current status of dataset loader and cache."""
        cache_path = Path(self.settings.dataset_cache_path)
        cache_exists = cache_path.exists()
        cache_size = cache_path.stat().st_size if cache_exists else None

        unique_locations = []
        budget_counts: dict[str, int] = {}
        if self._df is not None and not self._df.empty:
            unique_locations = sorted(self._df["location"].dropna().unique().tolist())
            if "budget_tier" in self._df.columns:
                budget_counts = self._df["budget_tier"].value_counts().to_dict()

        return {
            "status": "loaded" if self.is_loaded else "not_loaded",
            "is_loaded": self.is_loaded,
            "row_count": len(self._restaurants) if self._restaurants else 0,
            "dataset_name": self.settings.hf_dataset_name,
            "cache_path": str(cache_path),
            "cache_exists": cache_exists,
            "cache_size_bytes": cache_size,
            "source": self._source,
            "loaded_at": self._loaded_at.isoformat() if self._loaded_at else None,
            "locations_count": len(unique_locations),
            "sample_locations": unique_locations[:10],
            "budget_distribution": budget_counts,
        }


# Global module singleton
_default_loader: DatasetLoader | None = None
_loader_init_lock = threading.Lock()


def get_dataset_loader(settings: Settings | None = None) -> DatasetLoader:
    """Get or create the global singleton DatasetLoader."""
    global _default_loader
    if _default_loader is None:
        with _loader_init_lock:
            if _default_loader is None:
                _default_loader = DatasetLoader(settings)
    return _default_loader
