"""
Field verification endpoints (PRD.md Section 39). Citizen/officer ground
reports are a first-class evidence source that feeds back into the dynamic
risk engine's verification factor — see field_report_service and
risk_engine._evaluate_verification_factor.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

from ..schemas.field_report import FieldReport, FieldReportCreate, FieldReportVerifyRequest
from ..services import field_report_service

router = APIRouter(prefix="/api/field-reports", tags=["Field Reports"])


@router.get("", response_model=List[FieldReport])
def list_field_reports(
    cell_id: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    verification_status: Optional[str] = Query(None, description="PENDING, VERIFIED, or REJECTED"),
):
    """Lists field reports, most recent first."""
    return field_report_service.list_reports(cell_id=cell_id, district=district, verification_status=verification_status)


@router.post("", response_model=FieldReport, status_code=status.HTTP_201_CREATED)
def create_field_report(payload: FieldReportCreate):
    """
    Creates a new field verification report for a 500m cell. The report
    starts PENDING — it only contributes to risk evidence once an officer
    verifies it (see /verify).
    """
    report = field_report_service.create_report(payload)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{payload.cell_id}' not found in Kohima or Aizawl pilot grids.",
        )
    return report


@router.get("/{report_id}", response_model=FieldReport)
def get_field_report(report_id: str):
    report = field_report_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Field report '{report_id}' not found.")
    return report


@router.post("/{report_id}/verify", response_model=FieldReport)
def verify_field_report(report_id: str, request: FieldReportVerifyRequest):
    """
    Officer verification workflow: VERIFY promotes the report into real risk
    evidence (risk_engine's verification factor); REJECT discards it without
    ever contributing a score.
    """
    try:
        report = field_report_service.verify_report(report_id, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Field report '{report_id}' not found.")
    return report
