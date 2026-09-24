"""
Tests for cell details and parameters endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_valid_cell():
    response = client.get("/api/cells/KOH_00001")
    assert response.status_code == 200
    data = response.json()
    assert data["cell_id"] == "KOH_00001"
    assert data["district"] == "Kohima"
    assert data["state"] == "Nagaland"
    assert "latitude" in data and "longitude" in data
    
    # Terrain fields check
    terrain = data["terrain"]
    assert terrain["status"] == "AVAILABLE"
    assert terrain["elevation_mean"] is not None
    assert terrain["slope_mean"] is not None

    # Baseline susceptibility check
    baseline = data["baseline_susceptibility"]
    assert baseline["status"] == "AVAILABLE"
    assert baseline["tsi_score"] is not None
    assert baseline["tsi_class"] is not None

    # Dynamic status
    assert data["dynamic_risk_status"] in ("ACTIVE", "NOT_AVAILABLE")


def test_get_historical_event_cell():
    # KOH_01378 is Dzudza Bridge historical landslide event site
    response = client.get("/api/cells/KOH_01378")
    assert response.status_code == 200
    data = response.json()
    assert data["cell_id"] == "KOH_01378"
    hist = data["historical"]
    assert hist["has_verified_event"] is True
    assert hist["historical_event_id"] == "LS_KOH_2024_001"
    assert "Dzudza Bridge" in hist["event_location_name"]


def test_get_invalid_cell():
    response = client.get("/api/cells/INVALID_CELL_99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_cell_parameters():
    response = client.get("/api/cells/KOH_00001/parameters")
    assert response.status_code == 200
    data = response.json()
    assert data["cell_id"] == "KOH_00001"

    # Verify that dynamic sensors truthfully report unavailability and DO NOT fabricate 0
    rainfall = data["rainfall"]
    assert rainfall["status"] == "AVAILABLE"
    assert rainfall["rainfall_rate_mm_h"] is not None

    soil = data["soil_moisture"]
    assert soil["status"] == "STALE"
    assert soil["volumetric_moisture_m3_m3"] is not None

    sar = data["satellite"]
    assert sar["status"] == "REQUIRES_EXTERNAL_AUTH"
    assert sar["vv_change_db"] is None
    assert sar["vh_change_db"] is None

    # Verify terrain is available
    assert data["terrain"]["status"] == "AVAILABLE"
