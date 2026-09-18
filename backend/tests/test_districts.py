"""
Tests for district and grid endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_districts():
    response = client.get("/api/districts")
    assert response.status_code == 200
    data = response.json()
    assert data["total_districts"] == 2
    assert data["total_cells"] == 16961
    
    district_names = [d["district"] for d in data["districts"]]
    assert "Kohima" in district_names
    assert "Aizawl" in district_names

    kohima = next(d for d in data["districts"] if d["district"] == "Kohima")
    assert kohima["cell_count"] == 6055
    assert kohima["state"] == "Nagaland"

    aizawl = next(d for d in data["districts"] if d["district"] == "Aizawl")
    assert aizawl["cell_count"] == 10906
    assert aizawl["state"] == "Mizoram"


def test_get_kohima_grid():
    response = client.get("/api/districts/Kohima/grid")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 6055
    # Verify first feature retains exact structure
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "geometry" in feat
    assert "cell_id" in feat["properties"]


def test_get_aizawl_grid():
    response = client.get("/api/districts/Aizawl/grid")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 10906


def test_get_invalid_district_grid():
    response = client.get("/api/districts/NonExistentDistrict/grid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_district_risk():
    response = client.get("/api/districts/Kohima/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["district"] == "Kohima"
    assert data["baseline_type"] == "TERRAIN_SUSCEPTIBILITY_TSI"
    assert data["dynamic_risk_status"] == "NOT_AVAILABLE"
    assert len(data["cells"]) == 6055
    # Ensure baseline is not called ML probability
    assert "static baseline terrain susceptibility" in data["notice"].lower()


def test_get_invalid_district_risk():
    response = client.get("/api/districts/UnknownDistrict/risk")
    assert response.status_code == 404
