"""
Districts and Grid endpoints.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from ..services import data_service
from ..schemas.district import DistrictListResponse, DistrictRiskResponse
from ..config import TOTAL_CELL_COUNT

router = APIRouter(prefix="/api/districts", tags=["Districts"])


@router.get("", response_model=DistrictListResponse)
def list_districts():
    """Returns the two pilot districts (Kohima, Aizawl) with verified cell counts and center coordinates."""
    districts = data_service.get_districts()
    return DistrictListResponse(
        districts=districts,
        total_districts=len(districts),
        total_cells=TOTAL_CELL_COUNT,
    )


@router.get("/{district}/grid", response_model=Dict[str, Any])
def get_district_grid(district: str):
    """
    Returns the complete 500m analysis grid in GeoJSON format for the requested district.
    Uses the exact pre-generated project grid files without alteration.
    """
    geojson_data = data_service.get_district_grid_geojson(district)
    if not geojson_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district}' not found. Supported pilot districts are Kohima and Aizawl.",
        )
    return geojson_data


@router.get("/{district}/risk", response_model=DistrictRiskResponse)
def get_district_risk(district: str):
    """
    Returns baseline terrain susceptibility (TSI) for each cell in the district.
    Note: Dynamic ML risk is explicitly marked as NOT_AVAILABLE.
    """
    risk_data = data_service.get_district_risk(district)
    if not risk_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"District '{district}' not found. Supported pilot districts are Kohima and Aizawl.",
        )
    return DistrictRiskResponse(**risk_data)
