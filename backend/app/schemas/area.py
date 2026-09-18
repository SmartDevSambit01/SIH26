"""
Pydantic schemas for Area / Locality endpoints.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class AreaSummary(BaseModel):
    area_id: str
    area_name: str
    place_type: str
    district: str
    state: str
    latitude: float
    longitude: float
    cell_count: int
    max_tsi: Optional[float] = None
    dominant_class: Optional[str] = None
    has_historical_events: bool = False

class AreaDetail(BaseModel):
    area_id: str
    area_name: str
    place_type: str
    district: str
    state: str
    latitude: float
    longitude: float
    source: str
    source_url: str
    source_date: str
    cell_count: int
    associated_cells: List[str]

class AreaRiskSummary(BaseModel):
    area_id: str
    area_name: str
    district: str
    place_type: str
    data_source: str
    cell_count: int
    highest_risk_cell_id: Optional[str] = None
    max_tsi: Optional[float] = None
    dominant_class: Optional[str] = None
    class_distribution: Dict[str, float]
    has_historical_events: bool
    historical_event_ids: List[str]
    associated_cell_ids: List[str]
    notice: str = "Baseline susceptibility is not a live landslide prediction."
    dynamic_status: Dict[str, str] = {
        "rainfall": "Unavailable — NASA Earthdata authentication required",
        "soil_moisture": "Unavailable — NASA Earthdata authentication required",
        "sentinel1": "Unavailable — external authentication/download pending",
        "flood": "Unavailable"
    }

class AreaCellItem(BaseModel):
    cell_id: str
    latitude: float
    longitude: float
    distance_to_locality_m: float
    elevation_mean: Optional[float] = None
    slope_mean: Optional[float] = None
    aspect_mean: Optional[float] = None
    tsi_score: Optional[float] = None
    tsi_class: Optional[str] = None
    has_historical_event: bool = False
    historical_event_id: Optional[str] = None

class AreaCellsResponse(BaseModel):
    area_id: str
    area_name: str
    district: str
    total_cells: int
    cells: List[AreaCellItem]
