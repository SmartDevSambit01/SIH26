"""
Tests for observation endpoints (GPM rainfall, SMAP soil moisture, Sentinel-1 SAR).
Verifies that unavailable dynamic data is reported truthfully and not fabricated.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rainfall_latest():
    response = client.get("/api/rainfall/latest?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["layer"] == "GPM_IMERG_PRECIPITATION"
    assert data["data_status"] in {"AVAILABLE", "STALE", "REQUIRES_EXTERNAL_AUTH", "MISSING"}
    assert len(data["observations"]) == 10

    for obs in data["observations"]:
        assert obs["data_status"] in {"AVAILABLE", "STALE", "REQUIRES_EXTERNAL_AUTH", "MISSING"}
        if obs["data_status"] in {"AVAILABLE", "STALE"}:
            assert obs["rainfall_rate"] is not None
            assert float(obs["rainfall_rate"]) >= 0.0
        else:
            assert obs["rainfall_rate"] is None
            assert obs["rainfall_24h"] is None


def test_soil_moisture_latest():
    response = client.get("/api/soil-moisture/latest?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["layer"] == "SMAP_SOIL_MOISTURE"
    assert data["data_status"] in ["AVAILABLE", "STALE", "REQUIRES_EXTERNAL_AUTH"]
    assert len(data["observations"]) == 10

    for obs in data["observations"]:
        assert obs["data_status"] in ["AVAILABLE", "STALE", "REQUIRES_EXTERNAL_AUTH"]
        if obs["data_status"] in ["AVAILABLE", "STALE"]:
            assert obs["soil_moisture_current"] is not None
            assert 0.00 <= obs["soil_moisture_current"] <= 1.00
        else:
            assert obs["soil_moisture_current"] is None


def test_soil_moisture_top_level_status_matches_observations():
    """Regression test: get_latest_soil_moisture() used to hardcode the
    top-level data_status to REQUIRES_EXTERNAL_AUTH regardless of what the
    actual observations said, producing an internally-inconsistent response
    (e.g. top-level REQUIRES_EXTERNAL_AUTH next to a real STALE observation
    with real values and a real timestamp)."""
    response = client.get("/api/soil-moisture/latest?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["observations"]) == 1
    assert data["data_status"] == data["observations"][0]["data_status"]


def test_satellite_latest():
    response = client.get("/api/satellite/latest?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["layer"] == "SENTINEL1_SAR_CHANGE"
    assert data["data_status"] == "REQUIRES_EXTERNAL_AUTH"
    assert len(data["observations"]) == 10

    # Verify no fake numbers were generated
    for obs in data["observations"]:
        assert obs["data_status"] == "REQUIRES_EXTERNAL_AUTH"
        assert obs["vv_change_db"] is None
        assert obs["vh_change_db"] is None
        assert obs["change_confidence"] is None
