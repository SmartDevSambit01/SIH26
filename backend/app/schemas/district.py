"""
Schemas for district and grid endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class DistrictSummary(BaseModel):
    district: str = Field(..., description="District name", examples=["Kohima"])
    state: str = Field(..., description="State name", examples=["Nagaland"])
    cell_count: int = Field(..., description="Total 500m cells", examples=[6055])
    grid_resolution_m: int = Field(500, description="Grid resolution in meters")
    center: List[float] = Field(..., description="District center coordinates [lon, lat]")


class DistrictListResponse(BaseModel):
    districts: List[DistrictSummary]
    total_districts: int
    total_cells: int


class DistrictRiskCell(BaseModel):
    cell_id: str
    district: str
    latitude: float
    longitude: float
    baseline_susceptibility: Optional[float] = Field(None, description="Terrain Susceptibility Score (TSI 0-100)")
    susceptibility_class: Optional[str] = Field(None, description="TSI class: VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH")
    pu_terrain_similarity: Optional[float] = Field(None, description="PU learning similarity to known landslide terrain")
    data_status: str = Field("AVAILABLE", description="Status of baseline data")


class DistrictRiskResponse(BaseModel):
    district: str
    cell_count: int
    baseline_type: str = Field("TERRAIN_SUSCEPTIBILITY_TSI", description="Type of baseline susceptibility")
    dynamic_risk_status: str = Field("NOT_AVAILABLE", description="Dynamic ML risk model status")
    dynamic_engine_status: str = Field(
        "CONFIGURED_PENDING_EXTERNAL_AUTH",
        description="Dynamic policy engine status: configured with policy weights (45% rain, 35% soil, 10% flood, 5% SAR, 5% verif)"
    )
    notice: str = Field(
        "Values represent static baseline terrain susceptibility (TSI) derived from SRTM 30m DEM. "
        "No dynamic ML risk model is currently trained or active.",
        description="Scientific disclosure notice"
    )
    cells: List[DistrictRiskCell]
