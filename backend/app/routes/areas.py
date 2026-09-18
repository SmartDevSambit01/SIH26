"""
FastAPI router for Area and Locality Intelligence endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas.area import AreaSummary, AreaDetail, AreaRiskSummary, AreaCellsResponse
from ..services.area_service import AreaService
from ..services.data_service import DataService

router = APIRouter(prefix="/api/areas", tags=["Areas"])

# Dependency injection helpers
_data_service_instance = DataService()
_area_service_instance = AreaService(_data_service_instance)

def get_area_service() -> AreaService:
    _area_service_instance.ensure_loaded()
    return _area_service_instance

@router.get("", response_model=List[AreaSummary])
def get_areas(
    district: Optional[str] = Query(None, description="Filter by district name (e.g., Kohima, Aizawl)"),
    search: Optional[str] = Query(None, description="Search term for area name, district, or place type"),
    limit: int = Query(100, ge=1, le=1000, description="Max results to return"),
    area_service: AreaService = Depends(get_area_service)
):
    """
    Retrieve list of recognized localities/areas for Kohima and Aizawl.
    """
    return area_service.get_areas(district=district, search=search, limit=limit)

@router.get("/{area_id}", response_model=AreaDetail)
def get_area(
    area_id: str,
    area_service: AreaService = Depends(get_area_service)
):
    """
    Retrieve details for a specific area/locality by ID.
    """
    area = area_service.get_area_by_id(area_id)
    if not area:
        raise HTTPException(status_code=404, detail=f"Area '{area_id}' not found.")
    return area

@router.get("/{area_id}/risk", response_model=AreaRiskSummary)
def get_area_risk(
    area_id: str,
    area_service: AreaService = Depends(get_area_service)
):
    """
    Retrieve Baseline Susceptibility (TSI) aggregation summary for a specific area.
    """
    risk_summary = area_service.get_area_risk(area_id)
    if not risk_summary:
        raise HTTPException(status_code=404, detail=f"Area '{area_id}' not found.")
    return risk_summary

@router.get("/{area_id}/cells", response_model=AreaCellsResponse)
def get_area_cells(
    area_id: str,
    area_service: AreaService = Depends(get_area_service)
):
    """
    Retrieve associated 500m cells for a specific area with terrain and baseline risk details.
    """
    cells_resp = area_service.get_area_cells(area_id)
    if not cells_resp:
        raise HTTPException(status_code=404, detail=f"Area '{area_id}' not found.")
    return cells_resp

@router.get("/cell/{cell_id}/locality")
def get_cell_locality_info(
    cell_id: str,
    area_service: AreaService = Depends(get_area_service)
):
    """
    Retrieve locality association for a 500m cell or return standard fallback name.
    """
    return area_service.get_cell_locality_info(cell_id)
