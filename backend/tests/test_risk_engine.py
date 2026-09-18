"""
Comprehensive tests for Dynamic Landslide Risk Engine (Step 9B Task 9).
Verifies:
1. Static baseline susceptibility is retrieved without alteration.
2. Missing dynamic feeds (GPM, SMAP, SAR) are preserved as unavailable without fake values.
3. Factor explainability and weight configuration integrity.
4. Calibration and data completeness reporting.
5. Isolated calculation logic via test fixtures without modifying production datasets.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk_engine import risk_engine, DYNAMIC_WEIGHTS, COMBINATION_WEIGHTS

client = TestClient(app)


def test_weight_configuration_integrity():
    """Verifies that dynamic policy weights sum to 1.0 (100%)."""
    assert DYNAMIC_WEIGHTS["rainfall"] == 0.45
    assert DYNAMIC_WEIGHTS["soil_moisture"] == 0.35
    assert DYNAMIC_WEIGHTS["flood"] == 0.10
    assert DYNAMIC_WEIGHTS["satellite"] == 0.05
    assert DYNAMIC_WEIGHTS["verification"] == 0.05
    assert round(sum(DYNAMIC_WEIGHTS.values()), 6) == 1.0

    assert COMBINATION_WEIGHTS["baseline_susceptibility"] == 0.50
    assert COMBINATION_WEIGHTS["dynamic_triggers"] == 0.50
    assert round(sum(COMBINATION_WEIGHTS.values()), 6) == 1.0


def test_get_valid_cell_risk():
    """Verifies cell dynamic risk endpoint response for a standard cell."""
    response = client.get("/api/cells/KOH_00001/risk")
    assert response.status_code == 200
    data = response.json()

    assert data["cell_id"] == "KOH_00001"
    assert data["district"] == "Kohima"

    # Static baseline susceptibility must be available
    assert data["baseline_susceptibility"] is not None
    assert data["baseline_class"] in ["VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"]

    # Dynamic risk is active when live GPM and SMAP observations exist
    assert data["dynamic_trigger_score"] is not None
    assert data["combined_risk_score"] is not None
    assert data["risk_level"] in ["Low", "Watch", "Warning", "High", "Critical"]
    assert data["risk_status"] == "ACTIVE"
    assert data["calibration_status"] == "NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS"

    # Verify notice of transparency
    assert "not a trained supervised ml" in data["notice"].lower()


def test_get_historical_event_cell_risk():
    """Verifies that historical landslide ground truth site is marked in verification factor."""
    response = client.get("/api/cells/KOH_01378/risk")
    assert response.status_code == 200
    data = response.json()

    # Find verification factor
    ver_factor = next(f for f in data["factors"] if f["factor"] == "verification")
    assert ver_factor["status"] == "VERIFIED_INCIDENT"
    assert ver_factor["raw_value"] == "LS_KOH_2024_001"
    assert ver_factor["normalized_score"] == 100.0


def test_get_invalid_cell_risk():
    """Verifies 404 response for non-existent cell ID."""
    response = client.get("/api/cells/NON_EXISTENT_CELL/risk")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_risk_factors_explainability():
    """Verifies that every risk factor produces structured evidence."""
    response = client.get("/api/cells/KOH_00001/risk")
    assert response.status_code == 200
    factors = response.json()["factors"]

    factor_names = [f["factor"] for f in factors]
    expected_factors = ["terrain_baseline", "rainfall", "soil_moisture", "flood", "satellite", "verification"]
    for expected in expected_factors:
        assert expected in factor_names

    # Check rainfall factor reports AVAILABLE with real values
    rf = next(f for f in factors if f["factor"] == "rainfall")
    assert rf["status"] == "AVAILABLE"
    assert rf["raw_value"] is not None
    assert rf["normalized_score"] is not None
    assert rf["weight"] == 0.45

    # Check soil moisture factor reports STALE with real values
    sm = next(f for f in factors if f["factor"] == "soil_moisture")
    assert sm["status"] == "STALE"
    assert sm["raw_value"] is not None
    assert sm["normalized_score"] is not None
    assert sm["weight"] == 0.35

    # Check flood factor
    fl = next(f for f in factors if f["factor"] == "flood")
    assert fl["status"] == "NOT_YET_IMPLEMENTED"
    assert fl["raw_value"] is None
    assert fl["weight"] == 0.10

    # Check satellite factor
    sat = next(f for f in factors if f["factor"] == "satellite")
    assert sat["status"] == "REQUIRES_EXTERNAL_AUTH"
    assert sat["raw_value"] is None
    assert sat["weight"] == 0.05


def test_isolated_calculation_with_test_fixtures():
    """
    Unit test for mathematical risk calculation logic using isolated test fixtures.
    Does NOT modify production data or API files.
    """
    # Test fixture with simulated high rainfall and saturation
    test_overrides = {
        "rainfall": {"rainfall_rate": 35.0, "rainfall_24h": 120.0, "rainfall_72h": 180.0},
        "soil_moisture": {"soil_moisture_current": 0.42, "soil_moisture_change_percent": 25.0},
        "flood": {"flood_indicator": False},
        "satellite": {"vv_change_db": -4.2, "vh_change_db": -3.8, "change_confidence": 0.85},
        "verification": {"officer_verification_status": "REPORTED"},
    }

    assessment = risk_engine.evaluate_cell_risk("KOH_00001", dynamic_overrides=test_overrides)
    assert assessment is not None
    assert assessment.risk_status == "ACTIVE"
    assert assessment.dynamic_trigger_score is not None
    assert assessment.combined_risk_score is not None
    assert assessment.risk_level in ["Critical", "High", "Warning", "Watch", "Low"]
    assert assessment.risk_color is not None
    assert assessment.data_completeness == 1.0

    # Verify rainfall contribution was calculated mathematically
    rf = next(f for f in assessment.factors if f.factor == "rainfall")
    assert rf.status == "AVAILABLE"
    assert rf.normalized_score is not None and rf.normalized_score > 0
    assert rf.weighted_contribution is not None and rf.weighted_contribution > 0


def test_existing_district_risk_endpoint():
    """Verifies that GET /api/districts/{district}/risk continues working and includes dynamic engine disclosure."""
    response = client.get("/api/districts/Kohima/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["district"] == "Kohima"
    assert data["baseline_type"] == "TERRAIN_SUSCEPTIBILITY_TSI"
    assert data["dynamic_risk_status"] == "NOT_AVAILABLE"
    assert "dynamic_engine_status" in data
    assert len(data["cells"]) == 6055
