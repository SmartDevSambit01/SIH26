"""
Schemas for individual cell queries and multi-source parameters.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TerrainData(BaseModel):
    elevation_mean: Optional[float] = None
    elevation_min: Optional[float] = None
    elevation_max: Optional[float] = None
    slope_mean: Optional[float] = None
    slope_max: Optional[float] = None
    aspect_mean: Optional[float] = None
    curvature_mean: Optional[float] = None
    twi_mean: Optional[float] = None
    status: str = "AVAILABLE"


class HistoricalData(BaseModel):
    has_verified_event: bool = False
    historical_event_id: Optional[str] = None
    event_location_name: Optional[str] = None
    event_date: Optional[str] = None
    event_description: Optional[str] = None
    label_quality: Optional[str] = None
    status: str = "AVAILABLE"


class BaselineSusceptibilityData(BaseModel):
    tsi_score: Optional[float] = Field(None, description="Terrain Susceptibility Index (0-100)")
    tsi_class: Optional[str] = Field(None, description="Susceptibility category")
    pu_terrain_similarity: Optional[float] = Field(None, description="PU learning similarity")
    pu_similarity_class: Optional[str] = None
    primary_terrain_contributors: Optional[str] = None
    status: str = "AVAILABLE"


class CellSummary(BaseModel):
    cell_id: str
    district: str
    state: str
    latitude: float
    longitude: float
    terrain: TerrainData
    historical: HistoricalData
    baseline_susceptibility: BaselineSusceptibilityData
    flood_susceptibility: Dict[str, Any] = Field(
        default_factory=dict,
        description="Static DEM-derived flash-flood susceptibility (FFSI); NOT a dynamic flood observation",
    )
    exposure: Dict[str, Any] = Field(
        default_factory=dict,
        description="Real OSM-derived exposure (roads/hospitals/schools); population/infrastructure counts require authoritative data not yet integrated",
    )
    dynamic_risk_status: str = Field("NOT_AVAILABLE", description="Dynamic ML risk model status")
    data_availability: Dict[str, str] = Field(..., description="Availability flag per sensor/layer")


class CellParametersResponse(BaseModel):
    cell_id: str
    district: str
    latitude: float
    longitude: float
    terrain: Dict[str, Any]
    rainfall: Dict[str, Any]
    soil_moisture: Dict[str, Any]
    satellite: Dict[str, Any]
    flood: Dict[str, Any]
    verification: Dict[str, Any]
    exposure: Dict[str, Any]
    baseline_susceptibility: Dict[str, Any]
