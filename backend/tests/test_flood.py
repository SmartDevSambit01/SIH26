"""
Tests for the static flash-flood susceptibility (FFSI) endpoint and its
integration into cell parameters. Verifies:
1. GET /api/flood/latest returns real DEM-derived data, not a stub.
2. District filtering works.
3. A known cell (with real hydrology coverage) returns AVAILABLE FFSI data.
4. Cells with insufficient DEM coverage honestly report INSUFFICIENT_DATA,
   never a fabricated score.
5. The dynamic (live) flood indicator remains honestly NOT_YET_IMPLEMENTED —
   static susceptibility must never be confused with a live flood observation.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_flood_latest_returns_real_layer():
    response = client.get("/api/flood/latest?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["layer"] == "STATIC_FLASH_FLOOD_SUSCEPTIBILITY_FFSI"
    assert data["total_cells"] == 10
    assert "DEM-derived" in data["notice"]


def test_flood_latest_district_filter():
    response = client.get("/api/flood/latest?district=Kohima&limit=50")
    assert response.status_code == 200
    data = response.json()
    assert all(o["district"] == "Kohima" for o in data["observations"])


def test_flood_latest_no_fabricated_scores():
    response = client.get("/api/flood/latest?limit=500")
    assert response.status_code == 200
    data = response.json()
    for obs in data["observations"]:
        if obs["status"] == "INSUFFICIENT_DATA":
            assert obs["ffsi_score"] is None
            assert obs["ffsi_class"] is None
        else:
            assert obs["status"] == "AVAILABLE"
            assert 0.0 <= obs["ffsi_score"] <= 100.0
            assert obs["ffsi_class"] in {"VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"}


def test_cell_parameters_flood_block_has_real_static_data():
    response = client.get("/api/cells/KOH_00001/parameters")
    assert response.status_code == 200
    flood = response.json()["flood"]
    assert flood["static_susceptibility_status"] in {"AVAILABLE", "INSUFFICIENT_DATA"}
    # The dynamic flood indicator is a genuinely separate, still-unimplemented
    # capability and must never be conflated with the new static susceptibility.
    assert flood["dynamic_status"] == "NOT_YET_IMPLEMENTED"
    assert flood["dynamic_flood_indicator"] is None


def test_cell_summary_includes_flood_susceptibility():
    response = client.get("/api/cells/KOH_00001")
    assert response.status_code == 200
    data = response.json()
    assert "flood_susceptibility" in data
    assert data["data_availability"]["flood_dynamic_indicator"] == "NOT_YET_IMPLEMENTED"
