"""
FastAPI router for AI/ML Landslide Risk Model status, predictions, explanations, and metrics (Task 12).
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException

from ..schemas.model import ModelMetadata, ModelMetrics
from ..schemas.model_prediction import (
    ModelStatusResponse,
    FeatureRegistryResponse,
    ModelPredictionResponse,
    ModelExplanationResponse
)
from ..services import data_service, ml_model_service, MLModelService
from ..config import ML_DIR

router = APIRouter(prefix="/api/model", tags=["Model"])

def get_ml_service() -> MLModelService:
    ml_model_service.ensure_loaded()
    return ml_model_service

@router.get("/metadata", response_model=ModelMetadata)
def get_model_metadata():
    """
    Returns transparency metadata regarding AI/ML readiness and current baseline status.
    """
    return ModelMetadata(**data_service.get_model_metadata())

@router.get("/metrics", response_model=ModelMetrics)
def get_model_metrics():
    """
    Returns model validation metrics.
    """
    return ModelMetrics(**data_service.get_model_metrics())

@router.get("/status", response_model=ModelStatusResponse)
def get_model_status(service: MLModelService = Depends(get_ml_service)):
    """
    Returns official AI/ML model readiness status, label counts, and calibration gate.
    """
    return service.get_model_status()

@router.get("/features", response_model=FeatureRegistryResponse)
def get_model_features(service: MLModelService = Depends(get_ml_service)):
    """
    Returns feature registry distinguishing physical hazard predictors from exposure features.
    """
    return service.get_feature_registry()

@router.get("/validation")
def get_model_validation():
    """
    Returns spatial block validation metrics and calibration evaluation JSON.
    """
    metrics_file = ML_DIR / "model_metrics.json"
    if metrics_file.exists():
        with open(metrics_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "status": "NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS",
        "notice": "Model metrics file pending generation."
    }

@router.get("/predictions/{cell_id}", response_model=ModelPredictionResponse)
def get_cell_prediction(
    cell_id: str,
    service: MLModelService = Depends(get_ml_service)
):
    """
    Returns structured model prediction for a specific 500m analysis cell.
    """
    prediction = service.get_cell_prediction(cell_id)
    if not prediction:
        raise HTTPException(status_code=404, detail=f"Cell ID '{cell_id}' not found.")
    return prediction

@router.get("/explanation/{cell_id}", response_model=ModelExplanationResponse)
def get_cell_explanation(
    cell_id: str,
    service: MLModelService = Depends(get_ml_service)
):
    """
    Returns explainability factors and parameter evidence range comparison for a specific cell.
    """
    explanation = service.get_cell_explanation(cell_id)
    if not explanation:
        raise HTTPException(status_code=404, detail=f"Cell ID '{cell_id}' not found.")
    return explanation
