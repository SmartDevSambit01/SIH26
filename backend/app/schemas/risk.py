"""
Schemas for Dynamic Landslide Risk Engine.
Distinguishes baseline terrain susceptibility from dynamic triggers and enforces
transparent, explainable evidence tracking without synthetic or fabricated data.
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class RiskFactorEvidence(BaseModel):
    factor: str = Field(..., description="Risk factor name (e.g., rainfall, soil_moisture, terrain_baseline)")
    status: str = Field(..., description="Data status: AVAILABLE, REQUIRES_EXTERNAL_AUTH, NOT_YET_IMPLEMENTED, UNVERIFIED")
    raw_value: Optional[Any] = Field(None, description="Observed sensor or index measurement")
    normalized_score: Optional[float] = Field(None, description="Normalized score (0-100) or null if uncalibrated/unavailable")
    weight: float = Field(..., description="Configured policy weight (0.0 - 1.0)")
    weighted_contribution: Optional[float] = Field(None, description="Contribution to trigger score (weight * normalized_score)")
    description: str = Field(..., description="Scientific or operational status explanation")


class RiskAssessment(BaseModel):
    cell_id: str = Field(..., description="500m Grid Cell Identifier")
    district: str = Field(..., description="Pilot district (Kohima or Aizawl)")
    observation_timestamp: Optional[str] = Field(None, description="Dynamic observation timestamp")
    
    # Baseline terrain susceptibility (STATIC)
    baseline_susceptibility: Optional[float] = Field(None, description="Static Terrain Susceptibility Index (TSI 0-100)")
    baseline_class: Optional[str] = Field(None, description="Static TSI class: VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH")
    
    # Dynamic trigger evaluation
    dynamic_trigger_score: Optional[float] = Field(
        None,
        description="Weighted multi-source dynamic trigger score (0-100). Null when dynamic sensors are unavailable."
    )
    combined_risk_score: Optional[float] = Field(
        None,
        description="Combined risk score (baseline + dynamic triggers). Null when dynamic triggers are unavailable."
    )
    
    # Risk categorization
    risk_level: Optional[str] = Field(
        None,
        description="Categorical risk level: Critical, High, Warning, Watch, Low (or null if unavailable)"
    )
    risk_color: Optional[str] = Field(
        None,
        description="Map display color hex code: Purple, Red, Orange, Yellow, Green"
    )
    
    # Operational status & transparency
    risk_status: str = Field(
        ...,
        description="DYNAMIC_RISK_UNAVAILABLE, ACTIVE, or PENDING_CALIBRATION"
    )
    data_completeness: float = Field(
        ...,
        description="Fraction of required dynamic inputs currently available (0.0 to 1.0)"
    )
    calibration_status: str = Field(
        "NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS",
        description="Calibration state against verified landslide events"
    )
    
    # Contributing factors & explanation
    factors: List[RiskFactorEvidence] = Field(
        ...,
        description="Detailed evidence breakdown for every risk factor"
    )
    recommendation: str = Field(
        ...,
        description="Operational action or caution based on current risk assessment"
    )
    notice: str = Field(
        "Transparent configurable data-driven policy engine. This is NOT a trained supervised ML probability model.",
        description="Scientific disclosure statement"
    )
