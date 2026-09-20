"""
Schema for the real OSM-derived exposure endpoint.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExposureResponse(BaseModel):
    cell_id: str
    district: str
    status: str = Field(..., description="AVAILABLE or UNAVAILABLE")
    nearest_road_distance_m: Optional[float] = None
    nearest_road_class: Optional[str] = None
    road_length_in_cell_m: Optional[float] = None
    nearest_hospital_distance_m: Optional[float] = None
    nearest_hospital_name: Optional[str] = None
    nearest_school_distance_m: Optional[float] = None
    nearest_school_name: Optional[str] = None
    population_density_est: Optional[float] = None
    critical_infrastructure_count: Optional[int] = None
    notice: str
