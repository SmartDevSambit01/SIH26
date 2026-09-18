"""
Pydantic schemas for AI/ML Risk Model endpoints (Task 12).
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class ModelStatusResponse(BaseModel):
    model_name: str
    model_version: str
    model_strategy: str
    model_readiness: str
    supervised_ml_feasibility: str
    verified_positives_count: int
    verified_negatives_count: int
    unlabeled_cells_count: int
    calibration_status: str
    notice: str

class FeatureRegistryCategory(BaseModel):
    name: str
    unit: str
    type: str
    status: str

class FeatureRegistryResponse(BaseModel):
    physical_hazard_features: Dict[str, List[FeatureRegistryCategory]]
    exposure_and_impact_features: List[FeatureRegistryCategory]

class ParameterEvidenceItem(BaseModel):
    parameter_name: str
    current_value: str
    reference_evidence_range: str
    interpretation: str

class ModelPredictionResponse(BaseModel):
    cell_id: str
    district: str
    observation_timestamp: str
    susceptibility_score: Optional[float] = None
    dynamic_trigger_score: Optional[float] = None
    hazard_probability: Optional[float] = None
    probability_status: str
    risk_score: Optional[float] = None
    risk_level: str
    risk_color: str
    model_status: str
    calibration_status: str
    data_completeness_score: float
    top_contributing_factors: List[str]
    missing_features: List[str]
    evidence_sources: List[str]
    parameter_comparisons: List[ParameterEvidenceItem]
    notice: str

class ModelExplanationResponse(BaseModel):
    cell_id: str
    district: str
    risk_level: str
    top_contributing_factors: List[str]
    missing_features: List[str]
    parameter_comparisons: List[ParameterEvidenceItem]
    calibration_status: str
    explanation_notice: str
