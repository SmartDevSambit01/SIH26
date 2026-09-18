from fastapi import APIRouter, HTTPException, status
from ..services import data_service, risk_engine
from ..schemas.cell import CellSummary, CellParametersResponse
from ..schemas.risk import RiskAssessment

router = APIRouter(prefix="/api/cells", tags=["Cells"])


@router.get("/{cell_id}", response_model=CellSummary)
def get_cell_details(cell_id: str):
    """
    Returns detailed terrain morphometry, verified historical landslide incident data,
    baseline terrain susceptibility (TSI), and data availability flags for a 500m grid cell.
    """
    cell_data = data_service.get_cell(cell_id)
    if not cell_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{cell_id}' not found in Kohima or Aizawl pilot grids.",
        )
    return CellSummary(**cell_data)


@router.get("/{cell_id}/parameters", response_model=CellParametersResponse)
def get_cell_parameters(cell_id: str):
    """
    Returns multi-source structured parameters across terrain, rainfall, soil moisture,
    satellite SAR, flood, verification, exposure, and baseline susceptibility.
    Unavailable sources preserve truthful non-fabricated status.
    """
    params = data_service.get_cell_parameters(cell_id)
    if not params:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{cell_id}' not found in Kohima or Aizawl pilot grids.",
        )
    return CellParametersResponse(**params)


@router.get("/{cell_id}/risk", response_model=RiskAssessment)
def get_cell_risk(cell_id: str):
    """
    Returns transparent dynamic landslide risk assessment for a 500m grid cell.
    Explicitly separates static baseline susceptibility from dynamic trigger factors.
    When dynamic feeds require external credentials, reports DYNAMIC_RISK_UNAVAILABLE honestly.
    """
    assessment = risk_engine.evaluate_cell_risk(cell_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{cell_id}' not found in Kohima or Aizawl pilot grids.",
        )
    return assessment
