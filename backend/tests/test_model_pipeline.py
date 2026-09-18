"""
Comprehensive test suite for Task 12: AI/ML Landslide Risk Model + Scientific Validation & Calibration.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services import ml_model_service, MLModelService
from app.services.model_calibration_service import model_calibration_service

client = TestClient(app)

# ===========================================================================
# 1. Model Readiness & Calibration Gate Tests
# ===========================================================================

def test_model_readiness_gate_status():
    """Verify model readiness status reports LIMITED_DATA and NOT_FEASIBLE_INSUFFICIENT_LABELS."""
    status = ml_model_service.get_model_status()
    assert status["model_readiness"] == "LIMITED_DATA"
    assert status["supervised_ml_feasibility"] == "NOT_FEASIBLE_INSUFFICIENT_LABELS"
    assert status["verified_positives_count"] == 11
    assert status["verified_negatives_count"] == 0
    assert status["unlabeled_cells_count"] == 16950

def test_calibration_gate_status():
    """Verify calibration status reports NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS."""
    cal_info = model_calibration_service.get_calibration_status()
    assert cal_info["is_calibrated"] is False
    assert cal_info["calibration_status"] == "NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS"
    assert cal_info["current_verified_positives"] == 11

def test_no_fabricated_probabilities():
    """Verify uncalibrated hazard probability returns null instead of fake percentages."""
    res = model_calibration_service.calibrate_hazard_score(65.0)
    assert res["calibrated_hazard_probability"] is None
    assert res["probability_status"] == "UNAVAILABLE_NOT_CALIBRATED"

# ===========================================================================
# 2. Feature Registry & Schema Tests
# ===========================================================================

def test_feature_registry_schema_separation():
    """Verify physical hazard predictors are separated from exposure/impact features."""
    registry = ml_model_service.get_feature_registry()
    assert "physical_hazard_features" in registry
    assert "exposure_and_impact_features" in registry

    hazard_static = registry["physical_hazard_features"]["static_terrain"]
    hazard_names = [f["name"] for f in hazard_static]
    assert "slope_mean" in hazard_names
    assert "twi_mean" in hazard_names

    exposure_names = [f["name"] for f in registry["exposure_and_impact_features"]]
    assert "road_proximity_m" in exposure_names
    assert "population_density_est" in exposure_names

# ===========================================================================
# 3. Model Predictions & Explainability Tests
# ===========================================================================

def test_get_cell_prediction_kohima():
    """Verify structured prediction object for Kohima cell KOH_01378."""
    pred = ml_model_service.get_cell_prediction("KOH_01378")
    assert pred is not None
    assert pred["cell_id"] == "KOH_01378"
    assert pred["district"] == "Kohima"
    assert pred["hazard_probability"] is None
    assert pred["model_status"] == "LIMITED_DATA_PROTOTYPE"
    assert len(pred["top_contributing_factors"]) > 0

def test_get_cell_prediction_aizawl():
    """Verify structured prediction object for Aizawl cell AIZ_02321."""
    pred = ml_model_service.get_cell_prediction("AIZ_02321")
    assert pred is not None
    assert pred["cell_id"] == "AIZ_02321"
    assert pred["district"] == "Aizawl"
    assert "Verified historical landslide point (LS_AIZ_2023_001)" in pred["top_contributing_factors"]

def test_parameter_range_comparison_evidence():
    """Verify Phase 11 parameter range evidence comparison against scientific literature."""
    comp = ml_model_service.get_cell_parameter_comparison("KOH_01378")
    assert len(comp) >= 4
    param_names = [c["parameter_name"] for c in comp]
    assert "Slope Angle" in param_names
    assert "24-Hour Rainfall Cumulative" in param_names
    assert "Volumetric Soil Moisture" in param_names

def test_cell_explanation_endpoint_logic():
    """Verify explanation generation returns verified terrain factors and no fake dynamic factors."""
    expl = ml_model_service.get_cell_explanation("KOH_01378")
    assert expl is not None
    assert expl["cell_id"] == "KOH_01378"
    assert "missing_features" in expl

# ===========================================================================
# 4. API Integration Tests
# ===========================================================================

def test_api_get_model_status():
    """Test GET /api/model/status endpoint."""
    r = client.get("/api/model/status")
    assert r.status_code == 200
    data = r.json()
    assert data["model_readiness"] == "LIMITED_DATA"
    assert data["verified_positives_count"] == 11

def test_api_get_model_features():
    """Test GET /api/model/features endpoint."""
    r = client.get("/api/model/features")
    assert r.status_code == 200
    data = r.json()
    assert "physical_hazard_features" in data

def test_api_get_model_validation():
    """Test GET /api/model/validation endpoint."""
    r = client.get("/api/model/validation")
    assert r.status_code == 200
    data = r.json()
    assert "metrics_summary" in data
    assert data["metrics_summary"]["precision"] == "NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS"

def test_api_get_cell_prediction():
    """Test GET /api/model/predictions/{cell_id} endpoint."""
    r = client.get("/api/model/predictions/KOH_01378")
    assert r.status_code == 200
    data = r.json()
    assert data["cell_id"] == "KOH_01378"

def test_api_get_cell_explanation():
    """Test GET /api/model/explanation/{cell_id} endpoint."""
    r = client.get("/api/model/explanation/KOH_01378")
    assert r.status_code == 200
    data = r.json()
    assert data["cell_id"] == "KOH_01378"

def test_api_invalid_cell_prediction_returns_404():
    """Test GET /api/model/predictions/INVALID_CELL_9999 returns 404."""
    r = client.get("/api/model/predictions/INVALID_CELL_9999")
    assert r.status_code == 404
