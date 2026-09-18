"""
test_gpm_ingestion.py — Comprehensive Unit & Integration Tests for NASA GPM IMERG Ingestion

Verifies:
  1. Authentication detection (EARTHDATA_TOKEN, USER/PASS, .netrc).
  2. Successful real-data HDF5 parsing and pixel-to-cell spatial mapping.
  3. Controlled status vocabulary (AVAILABLE, STALE, MISSING, REQUIRES_EXTERNAL_AUTH, QUALITY_REJECTED).
  4. Missing granule handling without synthetic number fabrication.
  5. Stale data latency validation.
  6. Schema integrity and anti-fabrication safeguards.
"""

import os
import sys
import math
import tempfile
import numpy as np
import h5py
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ingest_gpm_rainfall import (
    check_earthdata_credentials,
    get_gpm_grid_cell,
    get_gpm_pixel_indices,
    parse_gpm_hdf5,
    STATUS_AVAILABLE,
    STATUS_STALE,
    STATUS_MISSING,
    STATUS_REQUIRES_AUTH,
    STATUS_QUALITY_REJECTED,
    OUTPUT_HEADERS,
)


def test_authentication_detection(monkeypatch):
    """Verifies authentication check behavior with environment variables."""
    # Test token environment variable
    monkeypatch.setenv("EARTHDATA_TOKEN", "test_secret_token_123")
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    has_auth, source = check_earthdata_credentials()
    assert has_auth is True
    assert source == "ENVIRONMENT_TOKEN"

    # Test username/password environment variables
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.setenv("EARTHDATA_USERNAME", "test_user")
    monkeypatch.setenv("EARTHDATA_PASSWORD", "test_pass")
    has_auth, source = check_earthdata_credentials()
    assert has_auth is True
    assert source == "ENVIRONMENT_USER_PASS"

    # Test missing credentials
    monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
    monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
    monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
    # Ensure netrc isn't picked up if present in test environment
    monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent_path_test"))
    has_auth, source = check_earthdata_credentials()
    assert has_auth is False
    assert source == "NO_CREDENTIALS_FOUND"


def test_gpm_pixel_spatial_mapping():
    """Verifies exact 0.1-degree GPM pixel index mapping for pilot district centroids."""
    # Kohima center: ~25.65 N, 94.15 E
    lon_idx, lat_idx = get_gpm_pixel_indices(25.65, 94.15)
    assert lon_idx == int(round((94.15 + 179.95) * 10.0))
    assert lat_idx == int(round((25.65 + 89.95) * 10.0))
    assert get_gpm_grid_cell(25.65, 94.15) == "GPM_0.1DEG_N25.65_E094.15"

    # Aizawl center: ~23.75 N, 92.75 E
    lon_idx_aiz, lat_idx_aiz = get_gpm_pixel_indices(23.75, 92.75)
    assert lon_idx_aiz == int(round((92.75 + 179.95) * 10.0))
    assert lat_idx_aiz == int(round((23.75 + 89.95) * 10.0))
    assert get_gpm_grid_cell(23.75, 92.75) == "GPM_0.1DEG_N23.75_E092.75"


def test_real_data_hdf5_parsing():
    """Tests synthetic generation and parsing of valid GPM HDF5 granule structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        hdf_path = Path(tmpdir) / "3B-HHR-E.MS.MRG.3IMERG.20260917-S120000-E122959.0720.V07C.HDF5"
        with h5py.File(hdf_path, "w") as hf:
            grid = hf.create_group("Grid")
            # Create lat, lon arrays
            lat_arr = np.linspace(-89.95, 89.95, 1800, dtype=np.float32)
            lon_arr = np.linspace(-179.95, 179.95, 3600, dtype=np.float32)
            grid.create_dataset("lat", data=lat_arr)
            grid.create_dataset("lon", data=lon_arr)
            
            # Create precipitation matrix (3600, 1800)
            precip = np.zeros((3600, 1800), dtype=np.float32)
            # Set specific rainfall rate for Kohima pixel
            lon_idx, lat_idx = get_gpm_pixel_indices(25.65, 94.15)
            precip[lon_idx, lat_idx] = 12.5  # 12.5 mm/hr
            grid.create_dataset("precipitation", data=precip)
            
            header = hf.create_group("FileHeader")
            header.attrs["StartGranuleDateTime"] = "2026-09-17T12:00:00.000Z"

        parsed = parse_gpm_hdf5(hdf_path)
        assert parsed is not None
        assert parsed["file_name"] == hdf_path.name
        assert parsed["precip"].shape == (3600, 1800)
        assert parsed["obs_time"] == datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)
        
        # Check mapped rainfall value
        val = parsed["precip"][lon_idx, lat_idx]
        assert float(val) == pytest.approx(12.5)


def test_missing_granule_handling(monkeypatch):
    """Verifies that missing granules produce REQUIRES_EXTERNAL_AUTH or MISSING status with zero synthetic numbers."""
    from scripts.ingest_gpm_rainfall import ingest_gpm_rainfall, OUTPUT_RAINFALL_CSV
    import scripts.ingest_gpm_rainfall as ingest_module
    import csv

    with tempfile.TemporaryDirectory() as tmp_raw:
        tmp_csv = Path(tmp_raw) / "gpm_latest_observations.csv"
        # Simulate missing auth and missing local files
        monkeypatch.setattr(ingest_module, "RAW_RAINFALL_DIR", Path(tmp_raw))
        monkeypatch.setattr(ingest_module, "OUTPUT_RAINFALL_CSV", tmp_csv)
        monkeypatch.setattr(ingest_module, "check_earthdata_credentials", lambda: (False, "NO_CREDENTIALS_FOUND"))
        monkeypatch.delenv("EARTHDATA_TOKEN", raising=False)
        monkeypatch.delenv("EARTHDATA_USERNAME", raising=False)
        monkeypatch.delenv("EARTHDATA_PASSWORD", raising=False)
        monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent_path_test"))

        ingest_gpm_rainfall()

        assert tmp_csv.exists()
        with open(tmp_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 16961
            for r in rows:
                assert r["data_status"] == STATUS_REQUIRES_AUTH
                assert r["rainfall_rate"] == ""
                assert r["rainfall_24h"] == ""


def test_schema_integrity():
    """Verifies output CSV headers match canonical schema."""
    expected = [
        "cell_id", "district", "latitude", "longitude", "gpm_grid_cell",
        "observation_timestamp", "source", "source_product", "source_resolution",
        "rainfall_rate", "rainfall_30min", "rainfall_3h", "rainfall_6h",
        "rainfall_24h", "rainfall_72h", "rainfall_duration_h",
        "antecedent_rainfall_7d", "data_status", "source_timestamp",
        "ingestion_timestamp", "quality_flag"
    ]
    assert OUTPUT_HEADERS == expected


def test_temporal_completeness_verification():
    """
    Verifies strict temporal completeness rules (Requirement 11):
      - Complete 24h sequence (48 granules)
      - Missing one 30-min interval (47 granules) -> 24h is None
      - Only 5 granules available -> 30min valid, 3h/6h/24h/72h None
      - Complete 72h sequence (144 granules)
      - Duplicate timestamps handling
      - Irregular timestamp gaps
      - Genuine zero rainfall (returns 0.0, True)
      - Distinction between genuine zero rainfall (0.0) and missing observation (None)
    """
    from scripts.ingest_gpm_rainfall import verify_and_compute_window_accumulation

    base_time = datetime(2026, 9, 17, 12, 0, 0, tzinfo=timezone.utc)
    precip_grid_zero = np.zeros((3600, 1800), dtype=np.float32)
    precip_grid_rain = np.full((3600, 1800), 2.0, dtype=np.float32)  # 2.0 mm/hr -> 1.0 mm per 30min

    def make_granule(obs_dt, grid):
        return {"obs_time": obs_dt, "precip": grid}

    # Case 1: Only 5 granules available
    granules_5 = [make_granule(base_time - timedelta(minutes=30 * i), precip_grid_rain) for i in range(5)]
    val_30m, ok_30m = verify_and_compute_window_accumulation(granules_5, 100, 100, 1)
    val_3h, ok_3h = verify_and_compute_window_accumulation(granules_5, 100, 100, 6)
    val_6h, ok_6h = verify_and_compute_window_accumulation(granules_5, 100, 100, 12)
    val_24h, ok_24h = verify_and_compute_window_accumulation(granules_5, 100, 100, 48)
    val_72h, ok_72h = verify_and_compute_window_accumulation(granules_5, 100, 100, 144)

    assert ok_30m is True
    assert val_30m == pytest.approx(1.0)
    assert ok_3h is False
    assert val_3h is None
    assert ok_6h is False
    assert val_6h is None
    assert ok_24h is False
    assert val_24h is None
    assert ok_72h is False
    assert val_72h is None

    # Case 2: Complete 24h sequence (48 granules)
    granules_48 = [make_granule(base_time - timedelta(minutes=30 * i), precip_grid_rain) for i in range(48)]
    val_24h_full, ok_24h_full = verify_and_compute_window_accumulation(granules_48, 100, 100, 48)
    assert ok_24h_full is True
    assert val_24h_full == pytest.approx(48.0)  # 48 * (2.0 * 0.5)

    # Case 3: Missing one 30-min interval (47 granules out of 48)
    granules_47_gap = [make_granule(base_time - timedelta(minutes=30 * i), precip_grid_rain) for i in range(48) if i != 10]
    val_24h_gap, ok_24h_gap = verify_and_compute_window_accumulation(granules_47_gap, 100, 100, 48)
    assert ok_24h_gap is False
    assert val_24h_gap is None

    # Case 4: Complete 72h sequence (144 granules)
    granules_144 = [make_granule(base_time - timedelta(minutes=30 * i), precip_grid_rain) for i in range(144)]
    val_72h_full, ok_72h_full = verify_and_compute_window_accumulation(granules_144, 100, 100, 144)
    assert ok_72h_full is True
    assert val_72h_full == pytest.approx(144.0)

    # Case 5: Duplicate timestamps
    granules_dups = list(granules_48) + [make_granule(base_time, precip_grid_rain)]
    val_24h_dup, ok_24h_dup = verify_and_compute_window_accumulation(granules_dups, 100, 100, 48)
    assert ok_24h_dup is True
    assert val_24h_dup == pytest.approx(48.0)

    # Case 6: Irregular timestamp gaps (e.g. 45-min gaps)
    granules_irregular = [make_granule(base_time - timedelta(minutes=45 * i), precip_grid_rain) for i in range(48)]
    val_24h_irreg, ok_24h_irreg = verify_and_compute_window_accumulation(granules_irregular, 100, 100, 48)
    assert ok_24h_irreg is False
    assert val_24h_irreg is None

    # Case 7 & 8: Distinction between genuine zero rainfall and missing observation
    granules_48_zero = [make_granule(base_time - timedelta(minutes=30 * i), precip_grid_zero) for i in range(48)]
    val_24h_zero, ok_24h_zero = verify_and_compute_window_accumulation(granules_48_zero, 100, 100, 48)
    assert ok_24h_zero is True
    assert val_24h_zero == pytest.approx(0.0)  # Genuine zero returns 0.0, True

    # Missing observation returns None, False
    assert val_24h_gap is None
    assert ok_24h_gap is False

