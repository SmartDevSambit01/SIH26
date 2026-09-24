"""
Schemas for citizen/officer field verification reports (PRD.md Section 39).
Human verification is a first-class data source that feeds back into risk
evidence — see risk_engine._evaluate_verification_factor.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    GROUND_CRACK = "GROUND_CRACK"
    ROAD_SETTLEMENT = "ROAD_SETTLEMENT"
    ROCKFALL = "ROCKFALL"
    MUD_MOVEMENT = "MUD_MOVEMENT"
    WATER_SEEPAGE = "WATER_SEEPAGE"
    DRAINAGE_BLOCKAGE = "DRAINAGE_BLOCKAGE"
    FRESH_DEBRIS = "FRESH_DEBRIS"
    FLOODED_ROAD = "FLOODED_ROAD"
    BRIDGE_OVERTOPPING = "BRIDGE_OVERTOPPING"
    OTHER = "OTHER"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class FieldReportCreate(BaseModel):
    cell_id: str = Field(..., description="500m analysis cell this report pertains to")
    report_type: ReportType
    description: str = Field(..., min_length=1, max_length=2000)
    reporter_role: str = Field(..., description="e.g. CITIZEN, FIELD_OFFICER, DISTRICT_ADMIN")
    confidence: Optional[str] = Field(None, description="Reporter's own confidence: LOW, MEDIUM, HIGH")
    evidence_note: Optional[str] = Field(
        None, description="Free-text evidence description; no file/photo upload implemented yet"
    )


class FieldReport(BaseModel):
    report_id: str
    cell_id: str
    district: str
    latitude: float
    longitude: float
    report_type: ReportType
    description: str
    reporter_role: str
    confidence: Optional[str] = None
    evidence_note: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.PENDING
    created_at: str
    verified_at: Optional[str] = None
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class FieldReportVerifyRequest(BaseModel):
    action: str = Field(..., description="VERIFY or REJECT")
    officer_id: str
    officer_role: str
    notes: Optional[str] = None
