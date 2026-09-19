import json
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.services.dataset_loader import DatasetLoader
from app.services.preprocessor import preprocess_dataframe


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    fixtures_path = Path("tests/fixtures/sample_restaurants.json")
    with open(fixtures_path) as f:
        data = json.load(f)
    return pd.DataFrame(data)


def test_dataset_loader_initial_status(tmp_path: Path):
    custom_cache = tmp_path / "cache.parquet"
    settings = Settings(dataset_cache_path=str(custom_cache))
    loader = DatasetLoader(settings)

    assert not loader.is_loaded
    status = loader.get_status()
    assert status["status"] == "not_loaded"
    assert status["row_count"] == 0
    assert not status["cache_exists"]


def test_dataset_loader_from_dataframe(sample_raw_df: pd.DataFrame, tmp_path: Path):
    custom_cache = tmp_path / "cache.parquet"
    settings = Settings(dataset_cache_path=str(custom_cache))
    loader = DatasetLoader(settings)

    df, restaurants = loader.load_from_dataframe(sample_raw_df)
    assert loader.is_loaded
    assert len(restaurants) == 5
    assert len(df) == 5

    status = loader.get_status()
    assert status["status"] == "loaded"
    assert status["row_count"] == 5
    assert "indiranagar" in status["sample_locations"]


def test_dataset_loader_parquet_caching(sample_raw_df: pd.DataFrame, tmp_path: Path):
    parquet_path = tmp_path / "restaurants.parquet"
    settings = Settings(dataset_cache_path=str(parquet_path))

    # 1. Preprocess and save to parquet
    clean_df, _ = preprocess_dataframe(sample_raw_df, settings)
    clean_df.to_parquet(parquet_path, index=False)

    assert parquet_path.exists()

    # 2. Loader should pick up from parquet cache fast
    loader = DatasetLoader(settings)

    start_time = time.perf_counter()
    df, restaurants = loader.load()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    assert loader.is_loaded
    assert len(restaurants) == 5
    assert loader.get_status()["source"] == "cache"
    # Should load in well under 100ms
    assert elapsed_ms < 100


def test_dataset_loader_handles_corrupt_parquet(tmp_path: Path):
    corrupt_path = tmp_path / "corrupt.parquet"
    corrupt_path.write_bytes(b"This is not a valid parquet file")

    settings = Settings(dataset_cache_path=str(corrupt_path))
    loader = DatasetLoader(settings)

    # _load_from_parquet should return None and remove corrupted file
    result = loader._load_from_parquet(corrupt_path)
    assert result is None
    assert not corrupt_path.exists()


def test_api_health_and_dataset_status():
    client = TestClient(app)

    # Health check
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert "dataset_loaded" in health_data

    # Dataset status check
    status_resp = client.get("/api/v1/dataset/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "status" in status_data
    assert "cache_path" in status_data
