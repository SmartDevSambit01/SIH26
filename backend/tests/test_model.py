"""
Tests for model metadata and evaluation metrics endpoints.
Verifies transparency: model is not trained, metrics do not exist.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_model_metadata():
    response = client.get("/api/model/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["model_status"] == "NOT_TRAINED"
    assert data["baseline_status"] == "AVAILABLE"
    assert data["dynamic_model_status"] == "NOT_READY"
    assert data["training_data_status"] == "INSUFFICIENT_VERIFIED_LABELS"
    assert data["verified_positive_cells"] == 11
    assert data["verified_negative_cells"] == 0
    assert data["unlabeled_cells"] == 16950
    assert data["total_cells"] == 16961
    assert "terrain" in data["baseline_type"].lower() or "tsi" in data["baseline_type"].lower()


def test_model_metrics():
    response = client.get("/api/model/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "NOT_AVAILABLE"
    assert data["metrics_available"] is False
    # Verify no fake accuracy or F1 was created
    assert data["accuracy"] is None
    assert data["precision"] is None
    assert data["recall"] is None
    assert data["f1"] is None
    assert data["roc_auc"] is None
