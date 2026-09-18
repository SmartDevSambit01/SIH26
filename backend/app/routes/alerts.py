"""
Alert Routes — Multi-Level Early Warning & Alert System API (SIH 2026 Task 10).

Endpoints:
  GET  /api/alerts                    — List active/filtered alerts
  GET  /api/alerts/{alert_id}         — Fetch alert by ID
  GET  /api/alerts/history            — Full lifecycle audit history
  POST /api/alerts/generate           — Generate candidate alert from risk assessment
  POST /api/alerts/{alert_id}/verify  — Officer approve/reject/emergency-override
  POST /api/alerts/{alert_id}/acknowledge — Agency receipt acknowledgement
  POST /api/alerts/{alert_id}/expire  — Manual expiry
  GET  /api/alerts/gateway/status     — Telecom gateway / dissemination status
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..services.risk_engine import risk_engine
from ..services.alert_service import alert_service
from ..schemas.alert import (
    AlertModel,
    AlertListResponse,
    AlertVerificationRequest,
    AlertAcknowledgeRequest,
    GenerateFromRiskRequest,
)

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


# ---------------------------------------------------------------------------
# List & Retrieve
# ---------------------------------------------------------------------------


@router.get("", response_model=AlertListResponse)
def list_alerts(
    district: Optional[str] = Query(None, description="Filter by district name (Kohima or Aizawl)"),
    level: Optional[str] = Query(None, description="Filter by operational level: ADVISORY, WATCH, WARNING, EVACUATION"),
    recipient: Optional[str] = Query(None, description="Filter by recipient group: DISTRICT_AUTHORITY, DISASTER_MANAGEMENT_AUTHORITY, LOCAL_COMMUNITY"),
    state: Optional[str] = Query(None, description="Filter by lifecycle state: PENDING_VERIFICATION, DISPATCHED, APPROVED, REJECTED, EXPIRED, etc."),
):
    """
    Returns filtered list of all operational early-warning alerts.
    Alerts that have passed their expiry time window are automatically transitioned to EXPIRED.
    """
    alerts = alert_service.get_active_alerts(
        district=district,
        level=level,
        recipient=recipient,
        state=state,
    )
    pending = sum(1 for a in alerts if a.lifecycle_state.value == "PENDING_VERIFICATION")
    active_states = {"PENDING_VERIFICATION", "APPROVED", "DISPATCHED", "ACKNOWLEDGED"}
    active = sum(1 for a in alerts if a.lifecycle_state.value in active_states)
    return AlertListResponse(total=len(alerts), alerts=alerts, active_count=active, pending_verification_count=pending)


@router.get("/history", response_model=AlertListResponse)
def get_alert_history(
    district: Optional[str] = Query(None, description="Filter history by district name"),
):
    """
    Returns complete audit-trail history of all alerts including expired and rejected records.
    Useful for post-event analysis, regulatory reporting, and NDMA compliance audits.
    """
    alerts = alert_service.get_alert_history(district=district)
    pending = sum(1 for a in alerts if a.lifecycle_state.value == "PENDING_VERIFICATION")
    active_states = {"PENDING_VERIFICATION", "APPROVED", "DISPATCHED", "ACKNOWLEDGED"}
    active = sum(1 for a in alerts if a.lifecycle_state.value in active_states)
    return AlertListResponse(total=len(alerts), alerts=alerts, active_count=active, pending_verification_count=pending)


@router.get("/gateway/status")
def get_gateway_status():
    """
    Returns truthful status of Cell Broadcast, NDMA SACHET, SMS, and Email notification gateways.
    Integration-ready abstractions pending official telecom operator and government gateway sign-off.
    """
    return alert_service.get_telecom_gateway_status()


@router.get("/{alert_id}", response_model=AlertModel)
def get_alert(alert_id: str):
    """Returns a specific alert by its unique ID including full audit trail and CAP payload."""
    alert = alert_service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert ID '{alert_id}' not found.",
        )
    return alert


# ---------------------------------------------------------------------------
# Alert Generation
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=AlertModel, status_code=status.HTTP_201_CREATED)
def generate_alert_from_risk(request: GenerateFromRiskRequest):
    """
    Evaluates the dynamic risk assessment for a given cell and, if thresholds are met,
    generates a PENDING_VERIFICATION candidate alert routed to District Authority,
    Disaster Management Authority, and Local Community.

    Returns 204 if conditions do not warrant an operational warning (risk too low or
    dynamic feeds unavailable). Returns 201 with alert payload when a candidate is created.

    NOTE: The generated alert remains in PENDING_VERIFICATION state and MUST be reviewed
    by an authorized officer before any public dissemination occurs.
    """
    assessment = risk_engine.evaluate_cell_risk(
        request.cell_id,
        dynamic_overrides=request.dynamic_overrides,
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{request.cell_id}' not found in Kohima or Aizawl pilot grids.",
        )

    alert = alert_service.generate_alert_from_risk(assessment)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=(
                "No operational alert warranted. Either dynamic sensor feeds are unavailable "
                "(requiring external authentication) or the combined risk score is below "
                "operational warning thresholds."
            ),
        )
    return alert


# ---------------------------------------------------------------------------
# Authorized Verification Workflow
# ---------------------------------------------------------------------------


@router.post("/{alert_id}/verify", response_model=AlertModel)
def verify_alert(alert_id: str, request: AlertVerificationRequest):
    """
    Authorized officer action on a PENDING_VERIFICATION candidate alert.

    Supported actions:
    - APPROVE: Signs off the alert and transitions to DISPATCHED for recipient notification.
    - REJECT: Overturns the candidate as a false alarm or localized risk.
    - EMERGENCY_OVERRIDE: Bypasses standard verification and immediately dispatches.

    All actions are recorded in the tamper-evident audit trail.
    """
    alert = alert_service.verify_alert(alert_id, request)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert ID '{alert_id}' not found.",
        )
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertModel)
def acknowledge_alert(alert_id: str, request: AlertAcknowledgeRequest):
    """
    Responding agency records receipt and deployment confirmation.
    Transitions the alert to ACKNOWLEDGED state with full audit trail entry.
    """
    alert = alert_service.acknowledge_alert(alert_id, request)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert ID '{alert_id}' not found.",
        )
    return alert


@router.post("/{alert_id}/expire", response_model=AlertModel)
def expire_alert(alert_id: str, notes: Optional[str] = Query(None)):
    """
    Manually expires an alert that has been superseded or resolved.
    Automatic expiry also occurs during list operations past the expiry timestamp.
    """
    alert = alert_service.expire_alert(alert_id, notes)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert ID '{alert_id}' not found.",
        )
    return alert
