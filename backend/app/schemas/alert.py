"""
Schemas for Operational Multi-Level Early Warning & Alert System (SIH 2026 Task 10).
Decouples physical AI hazard calculation from operational administrative alerts,
authorized approval workflows, recipient routing, and CAP v1.2 serialization.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class OperationalAlertLevel(str, Enum):
    """
    Operational early-warning tiers for emergency response.
    These are administrative action levels, decoupled from map hazard colors.
    """
    ADVISORY = "ADVISORY"       # General vigilance / monitoring
    WATCH = "WATCH"             # Favorable conditions for slope failure; prepare resources
    WARNING = "WARNING"         # Imminent danger; restrict movement, activate shelters
    EVACUATION = "EVACUATION"   # Extreme threat; mandatory evacuation of toe-slopes


class RecipientGroup(str, Enum):
    """Target audience tiers with tailored actionable language."""
    DISTRICT_AUTHORITY = "DISTRICT_AUTHORITY"                       # DC, District EOC, Police, PWD
    DISASTER_MANAGEMENT_AUTHORITY = "DISASTER_MANAGEMENT_AUTHORITY" # NSDMA / SDMA / NDMA
    LOCAL_COMMUNITY = "LOCAL_COMMUNITY"                             # Village council, citizens, road users


class AlertLifecycleState(str, Enum):
    """Full lifecycle state machine for early warning notices."""
    GENERATED = "GENERATED"                         # Candidate alert produced by decision engine
    PENDING_VERIFICATION = "PENDING_VERIFICATION"   # Awaiting authorized officer review
    APPROVED = "APPROVED"                           # Officially validated and signed off
    REJECTED = "REJECTED"                           # Overturned by officer (false alarm / localized check)
    QUEUED = "QUEUED"                               # Queued in dissemination gateway
    DISPATCHED = "DISPATCHED"                       # Sent to recipient endpoints
    ACKNOWLEDGED = "ACKNOWLEDGED"                   # Receipt confirmed by responding agency
    EXPIRED = "EXPIRED"                             # Passed valid time horizon without re-trigger


class AlertAuditEntry(BaseModel):
    timestamp: str = Field(..., description="ISO8601 event timestamp")
    action: str = Field(..., description="Action taken: GENERATED, APPROVED, REJECTED, EMERGENCY_OVERRIDE, etc.")
    actor: str = Field(..., description="System process or officer ID")
    role: str = Field(..., description="Actor role: SYSTEM_ENGINE, DISTRICT_OFFICER, etc.")
    notes: Optional[str] = Field(None, description="Operational notes or justification")


class RecipientTemplate(BaseModel):
    headline: str = Field(..., description="Audience-targeted header")
    instruction: str = Field(..., description="Actionable safety or deployment instruction")
    recommended_action: str = Field(..., description="Specific directive (prepare, monitor, shelter, evacuate)")
    tone: str = Field(..., description="TECHNICAL, COORDINATION, or PUBLIC_SAFETY")


class CAPArea(BaseModel):
    areaDesc: str = Field(..., description="Textual description of affected area")
    polygon: Optional[List[List[float]]] = Field(None, description="GeoJSON polygon coordinates [[lon, lat], ...]")
    circle: Optional[str] = Field(None, description="Coordinates and radius, e.g. 'lat,lon radius_km'")


class CAPInfo(BaseModel):
    language: str = "en-IN"
    category: str = "Geo"
    event: str = "Landslide Early Warning"
    urgency: str = Field(..., description="Immediate, Expected, Future, Past, Unknown")
    severity: str = Field(..., description="Extreme, Severe, Moderate, Minor, Unknown")
    certainty: str = Field(..., description="Observed, Likely, Possible, Unlikely, Unknown")
    headline: str
    description: str
    instruction: str
    effective: str
    expires: str
    senderName: str = "NER Safe Early Warning Center"
    area: CAPArea


class CAPAlert(BaseModel):
    """OASIS Common Alerting Protocol (CAP) v1.2 representation."""
    identifier: str = Field(..., description="Globally unique CAP identifier")
    sender: str = "ner-safe-backend@sih2026.gov.in"
    sent: str = Field(..., description="ISO8601 dispatch time")
    status: str = Field("Draft", description="Actual, Exercise, System, Test, Draft")
    msgType: str = Field("Alert", description="Alert, Update, Cancel, Ack, Error")
    scope: str = Field("Public", description="Public, Restricted, Private")
    info: CAPInfo


class AlertModel(BaseModel):
    alert_id: str = Field(..., description="Unique operational alert identifier")
    created_at: str = Field(..., description="Creation ISO timestamp")
    updated_at: str = Field(..., description="Last state change timestamp")
    district: str = Field(..., description="Target district: Kohima or Aizawl")
    target_cell_ids: List[str] = Field(..., description="Affected 500m analysis cells")
    target_area_description: str = Field(..., description="Geographic area summary")
    
    # Hazard risk linkage
    risk_score: Optional[float] = Field(None, description="Triggering risk score (0-100)")
    risk_level: Optional[str] = Field(None, description="Hazard map class: Critical, High, Warning, Watch, Low")
    operational_alert_level: OperationalAlertLevel = Field(..., description="Operational warning level")
    lifecycle_state: AlertLifecycleState = Field(..., description="Current lifecycle state")
    risk_status: str = Field(..., description="ACTIVE or DYNAMIC_RISK_UNAVAILABLE")
    
    # Factors & evidence
    triggering_factors: List[Dict[str, Any]] = Field(default_factory=list, description="Structured risk evidence breakdown")
    
    # Recipient routing & templates
    recipient_groups: List[RecipientGroup] = Field(..., description="Target audience tiers")
    templates: Dict[str, RecipientTemplate] = Field(..., description="Rendered template per recipient group")
    
    # Verification & governance
    verification_required: bool = Field(True, description="Whether public dissemination requires officer authorization")
    verification_officer_id: Optional[str] = None
    verification_role: Optional[str] = None
    verified_at: Optional[str] = None
    dispatched_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    expires_at: str = Field(..., description="Expiration timestamp")
    cooldown_until: str = Field(..., description="Duplicate suppression timestamp")
    
    # Audit & CAP
    audit_trail: List[AlertAuditEntry] = Field(default_factory=list, description="Tamper-evident lifecycle history")
    cap_representation: Optional[CAPAlert] = Field(None, description="CAP v1.2 payload envelope")
    
    # Transparency
    notice: str = Field(
        "Prototype operational early-warning record. Requires authorized officer verification before public release. "
        "Cell Broadcast and telecom integrations are integration-ready abstractions pending government telecom gateway.",
        description="Operational disclosure notice"
    )


class AlertVerificationRequest(BaseModel):
    action: str = Field(..., description="APPROVE, REJECT, or EMERGENCY_OVERRIDE")
    officer_id: str = Field("DEMO_AUTHORIZED_OFFICER", description="Authorizing officer ID")
    officer_role: str = Field("DISTRICT_DISASTER_MANAGEMENT_OFFICER", description="Officer designation")
    notes: Optional[str] = Field(None, description="Justification or field verification log")


class AlertAcknowledgeRequest(BaseModel):
    officer_id: str = Field("DEMO_AUTHORIZED_OFFICER", description="Acknowledging officer ID")
    agency: str = Field("DISTRICT_EOC", description="Responding agency: DISTRICT_EOC, POLICE_CONTROL, NSDMA")
    notes: Optional[str] = Field(None, description="Resource deployment acknowledgement notes")


class AlertListResponse(BaseModel):
    total: int
    alerts: List[AlertModel]
    active_count: int
    pending_verification_count: int


class GenerateFromRiskRequest(BaseModel):
    cell_id: str = Field(..., description="Target cell ID, e.g. KOH_01378")
    dynamic_overrides: Optional[Dict[str, Any]] = Field(None, description="Isolated observation overrides for scenario testing")
