"""
Real OSM-derived exposure endpoint (roads/hospitals/schools). Population
density and critical-infrastructure counts remain null pending authoritative
census/GIS data — see data_service.get_exposure for the full disclosure.
"""

from fastapi import APIRouter, HTTPException, status
from ..services import data_service
from ..schemas.exposure import ExposureResponse

router = APIRouter(prefix="/api", tags=["Exposure"])


@router.get("/exposure/{cell_id}", response_model=ExposureResponse)
def get_cell_exposure(cell_id: str):
    """
    Returns real exposure evidence (nearest road/hospital/school, real
    OpenStreetMap data) for a 500m grid cell. Roads/population are exposure
    variables, never physical landslide causes (PRD.md Section 27).
    """
    exposure = data_service.get_exposure(cell_id)
    if not exposure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{cell_id}' not found in Kohima or Aizawl pilot grids.",
        )
    return ExposureResponse(**exposure)
