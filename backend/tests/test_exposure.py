"""
Tests for the real OSM-derived exposure endpoint. Verifies:
1. GET /api/exposure/{cell_id} returns real data, not a NOT_YET_IMPLEMENTED stub.
2. A cell near central Kohima (with real OSM coverage) resolves a real named
   hospital/road within a plausible distance.
3. Population/critical-infrastructure fields stay honestly null — OSM roads/
   hospitals are not a substitute for authoritative census/GIS data.
4. 404 on an unknown cell.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_exposure_endpoint_returns_real_data_not_stub():
    response = client.get("/api/exposure/KOH_00001")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"AVAILABLE", "UNAVAILABLE"}
    # This must no longer be the old hardcoded "NOT_YET_IMPLEMENTED" stub.
    assert data["status"] != "NOT_YET_IMPLEMENTED"


def test_exposure_resolves_real_named_hospital_near_central_kohima():
    response = client.get("/api/exposure/KOH_02553")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "AVAILABLE"
    assert data["nearest_hospital_name"] is not None
    assert data["nearest_hospital_distance_m"] is not None
    assert data["nearest_hospital_distance_m"] >= 0


def test_exposure_population_and_infrastructure_stay_honestly_null():
    response = client.get("/api/exposure/KOH_00001")
    data = response.json()
    # No authoritative census/GIS source is integrated — must not be fabricated.
    assert data["population_density_est"] is None
    assert data["critical_infrastructure_count"] is None


def test_exposure_404_unknown_cell():
    response = client.get("/api/exposure/NOT_A_REAL_CELL")
    assert response.status_code == 404


def test_cell_parameters_exposure_block_is_real():
    response = client.get("/api/cells/KOH_00001/parameters")
    assert response.status_code == 200
    exposure = response.json()["exposure"]
    assert exposure["source"] == "OpenStreetMap Overpass API (real roads/hospitals/schools)"
    assert exposure["status"] != "NOT_YET_IMPLEMENTED"
