"""
Schemas for dynamic sensor observations (GPM rainfall, SMAP soil moisture, Sentinel-1 SAR).
All numeric measurements default to None/null when external auth is missing.
No fake or zero numbers are generated.
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class RainfallObservation(BaseModel):
    cell_id: str
    district: str
    latitude: float
    longitude: float
    gpm_grid_cell: Optional[str] = None
    observation_timestamp: Optional[str] = None
    source: str = "NASA / JAXA GPM Constellation"
    source_product: str = "GPM_3IMERGHH_V07B_EARLY"
    source_resolution: str = "0.1 deg (~10 km) Half-Hourly"
    rainfall_rate: Optional[float] = None
    rainfall_30min: Optional[float] = None
    rainfall_3h: Optional[float] = None
    rainfall_6h: Optional[float] = None
    rainfall_24h: Optional[float] = None
    rainfall_72h: Optional[float] = None
    rainfall_duration_h: Optional[float] = None
    antecedent_rainfall_7d: Optional[float] = None
    data_status: str = Field(..., examples=["REQUIRES_EXTERNAL_AUTH"])
    quality_flag: str = Field(..., examples=["UNAVAILABLE_PENDING_EARTHDATA_LOGIN"])


class SoilMoistureObservation(BaseModel):
    cell_id: str
    district: str
    latitude: float
    longitude: float
    smap_ease2_grid_cell: Optional[str] = None
    observation_timestamp: Optional[str] = None
    soil_moisture_current: Optional[float] = None
    soil_moisture_previous: Optional[float] = None
    soil_moisture_change: Optional[float] = None
    soil_moisture_change_percent: Optional[float] = None
    source: str = "NASA / NSIDC SMAP Mission"
    source_product: str = "SPL3SMP_E_V006"
    source_resolution: str = "9 km (EASE-Grid 2.0) Daily"
    data_status: str = Field(..., examples=["REQUIRES_EXTERNAL_AUTH"])
    quality_flag: str = Field(..., examples=["UNAVAILABLE_PENDING_EARTHDATA_LOGIN"])


class SatelliteObservation(BaseModel):
    cell_id: str
    district: str
    latitude: float
    longitude: float
    observation_timestamp: Optional[str] = None
    source: str = "Copernicus Sentinel-1 (C-SAR IW GRD)"
    source_product: str = "S1_IW_GRDH_DUAL_POL"
    source_resolution: str = "10m pixel spacing (IW GRDH); 500m = project analysis grid"
    platform: Optional[str] = None
    relative_orbit: Optional[int] = None
    flight_direction: Optional[str] = None
    polarization: Optional[str] = None
    pre_scene_date: Optional[str] = None
    post_scene_date: Optional[str] = None
    repeat_interval_days: Optional[int] = None
    vv_change_db: Optional[float] = None
    vh_change_db: Optional[float] = None
    vv_vh_change: Optional[float] = None
    change_confidence: Optional[float] = None
    data_status: str = Field(..., examples=["REQUIRES_EXTERNAL_AUTH"])
    quality_flag: str = Field(..., examples=["UNAVAILABLE_PENDING_EARTHDATA_LOGIN"])
    scientific_notice: Optional[str] = None


class ObservationListResponse(BaseModel):
    layer: str
    total_cells: int
    data_status: str
    notice: str
    observations: List[Any]
