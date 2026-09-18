"""
Dynamic observation endpoints for rainfall, soil moisture, and satellite radar change.
All endpoints preserve honest unavailable states when external authentication is required.
"""

from typing import Optional
from fastapi import APIRouter, Query
from ..services import data_service
from ..schemas.observations import ObservationListResponse

router = APIRouter(prefix="/api", tags=["Observations"])


@router.get("/rainfall/latest", response_model=ObservationListResponse)
def get_latest_rainfall(
    district: Optional[str] = Query(None, description="Filter by district (Kohima, Aizawl)"),
    limit: int = Query(100, ge=1, le=1000, description="Max cells to return"),
):
    """
    Returns latest GPM IMERG half-hourly precipitation observations.
    Currently indicates REQUIRES_EXTERNAL_AUTH as NASA Earthdata login is pending.
    """
    data = data_service.get_latest_rainfall(district=district, limit=limit)
    return ObservationListResponse(**data)


@router.get("/soil-moisture/latest", response_model=ObservationListResponse)
def get_latest_soil_moisture(
    district: Optional[str] = Query(None, description="Filter by district (Kohima, Aizawl)"),
    limit: int = Query(100, ge=1, le=1000, description="Max cells to return"),
):
    """
    Returns latest SMAP 9km volumetric soil moisture observations.
    Currently indicates REQUIRES_EXTERNAL_AUTH as NASA Earthdata login is pending.
    """
    data = data_service.get_latest_soil_moisture(district=district, limit=limit)
    return ObservationListResponse(**data)


@router.get("/satellite/latest", response_model=ObservationListResponse)
def get_latest_satellite(
    district: Optional[str] = Query(None, description="Filter by district (Kohima, Aizawl)"),
    limit: int = Query(100, ge=1, le=1000, description="Max cells to return"),
):
    """
    Returns latest Sentinel-1 C-SAR backscatter change observations.
    Currently indicates REQUIRES_EXTERNAL_AUTH as Copernicus/Earthdata download login is pending.
    """
    data = data_service.get_latest_satellite(district=district, limit=limit)
    return ObservationListResponse(**data)
