"""
Static flash-flood susceptibility endpoint (DEM-derived: HAND, flow accumulation,
TWI, slope, drainage density). Not a live/dynamic flood observation — see
data_service.get_latest_flood for the scientific-disclosure notice.
"""

from typing import Optional
from fastapi import APIRouter, Query
from ..services import data_service
from ..schemas.observations import ObservationListResponse

router = APIRouter(prefix="/api", tags=["Flood"])


@router.get("/flood/latest", response_model=ObservationListResponse)
def get_latest_flood(
    district: Optional[str] = Query(None, description="Filter by district (Kohima, Aizawl)"),
    limit: int = Query(100, ge=1, le=1000, description="Max cells to return"),
):
    """
    Returns static flash-flood susceptibility (FFSI) per 500m cell, derived
    from SRTM/Copernicus DEM hydrology. Cells with insufficient DEM coverage
    (district-boundary edges) honestly report INSUFFICIENT_DATA rather than
    a fabricated score.
    """
    data = data_service.get_latest_flood(district=district, limit=limit)
    return ObservationListResponse(**data)
