"""
Alert Decision Engine and Multi-Level Early Warning Service for SIH 2026.
Decouples AI physical hazard assessment from operational emergency alerts.
Implements:
1. Configurable risk-to-alert policy mapping.
2. Mandatory recipient group routing (District, SDMA/NDMA, Local Community).
3. Authorized officer verification workflow with audit trails.
4. Duplicate prevention, throttling, cooldown, and escalation logic.
5. OASIS CAP v1.2 envelope serialization.
6. Cell Broadcast & Notification Channel abstractions (Integration-Ready).
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from ..schemas.alert import (
    OperationalAlertLevel,
    RecipientGroup,
    AlertLifecycleState,
    AlertAuditEntry,
    RecipientTemplate,
    CAPArea,
    CAPInfo,
    CAPAlert,
    AlertModel,
    AlertVerificationRequest,
    AlertAcknowledgeRequest,
)
from ..schemas.risk import RiskAssessment


# ==============================================================================
# 1. CONFIGURABLE RISK-TO-ALERT POLICY MAPPING (PHASE 3 & 4)
# Explicitly marked as prototype operational policy requiring empirical calibration.
# ==============================================================================
POLICY_ALERT_THRESHOLDS = [
    (80.0, OperationalAlertLevel.EVACUATION), # Combined score >= 80.0 -> EVACUATION candidate
    (45.0, OperationalAlertLevel.WARNING),    # Combined score 45.0 - 79.9 -> WARNING
    (30.0, OperationalAlertLevel.WATCH),      # Combined score 30.0 - 44.9 -> WATCH
    (0.0,  None),                             # Combined score < 30.0 -> No operational warning
]

DEFAULT_COOLDOWN_HOURS = 6
DEFAULT_EXPIRY_HOURS = 24


class AlertService:
    """
    In-memory alert service managing operational early warning candidates,
    official sign-offs, deduplication, and CAP dissemination formats.
    """

    def __init__(self):
        self._alerts_db: Dict[str, AlertModel] = {}
        self._cell_cooldowns: Dict[str, Tuple[OperationalAlertLevel, datetime]] = {}

    def get_active_alerts(
        self,
        district: Optional[str] = None,
        level: Optional[str] = None,
        recipient: Optional[str] = None,
        state: Optional[str] = None,
    ) -> List[AlertModel]:
        """Returns filtered list of active/operational alerts."""
        results = list(self._alerts_db.values())
        now = datetime.now(timezone.utc)

        # Auto-expire alerts that passed expiry time
        for alert in results:
            if alert.lifecycle_state in [AlertLifecycleState.APPROVED, AlertLifecycleState.DISPATCHED, AlertLifecycleState.ACKNOWLEDGED]:
                try:
                    exp = datetime.fromisoformat(alert.expires_at)
                    if exp < now:
                        self.expire_alert(alert.alert_id, "Automatically expired past validity window")
                except Exception:
                    pass

        # Apply filters
        if district:
            results = [a for a in results if a.district.lower() == district.strip().lower()]
        if level:
            results = [a for a in results if a.operational_alert_level.value.upper() == level.strip().upper()]
        if recipient:
            results = [a for a in results if any(r.value.upper() == recipient.strip().upper() for r in a.recipient_groups)]
        if state:
            results = [a for a in results if a.lifecycle_state.value.upper() == state.strip().upper()]

        return sorted(results, key=lambda a: a.created_at, reverse=True)

    def get_alert_by_id(self, alert_id: str) -> Optional[AlertModel]:
        """Fetches a specific alert by ID."""
        return self._alerts_db.get(alert_id)

    def get_alert_history(self, district: Optional[str] = None) -> List[AlertModel]:
        """Returns full audit history of all alerts."""
        results = list(self._alerts_db.values())
        if district:
            results = [a for a in results if a.district.lower() == district.strip().lower()]
        return sorted(results, key=lambda a: a.created_at, reverse=True)

    # --------------------------------------------------------------------------
    # Decision Engine: Risk -> Candidate Alert (Phase 3, 4, 10)
    # --------------------------------------------------------------------------
    def generate_alert_from_risk(
        self,
        assessment: RiskAssessment,
        target_area_desc: Optional[str] = None,
    ) -> Optional[AlertModel]:
        """
        Evaluates RiskAssessment output. If dynamic inputs are unavailable or risk is low,
        safely refuses to manufacture an operational alert. If high, generates a candidate alert.
        """
        # Rule: Do not generate dynamic operational warnings when dynamic risk is unavailable
        if assessment.risk_status == "DYNAMIC_RISK_UNAVAILABLE" or assessment.combined_risk_score is None:
            return None

        score = assessment.combined_risk_score
        target_level: Optional[OperationalAlertLevel] = None

        for threshold, level in POLICY_ALERT_THRESHOLDS:
            if score >= threshold:
                target_level = level
                break

        # If score < 30.0, conditions are within standard baseline; no operational warning needed
        if target_level is None:
            return None

        cell_id = assessment.cell_id
        district = assessment.district
        now = datetime.now(timezone.utc)

        # Duplicate Prevention & Cooldown / Escalation Logic (Phase 10)
        cooldown_key = f"{district}_{cell_id}"
        if cooldown_key in self._cell_cooldowns:
            last_level, until_time = self._cell_cooldowns[cooldown_key]
            if now < until_time:
                # If level is same or lower, suppress duplicate to prevent alert fatigue
                if self._level_rank(target_level) <= self._level_rank(last_level):
                    return None
                # If level escalated, proceed to create escalation candidate

        # Update cooldown
        expiry_dt = now + timedelta(hours=DEFAULT_EXPIRY_HOURS)
        cooldown_dt = now + timedelta(hours=DEFAULT_COOLDOWN_HOURS)
        self._cell_cooldowns[cooldown_key] = (target_level, cooldown_dt)

        alert_id = f"ALT_{district[:3].upper()}_{now.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
        area_desc = target_area_desc or f"{district} District, 500m Grid Cell {cell_id}"

        # Build recipient templates
        templates = self._generate_recipient_templates(
            district=district,
            cell_id=cell_id,
            level=target_level,
            score=score,
            area_desc=area_desc,
        )

        audit_entry = AlertAuditEntry(
            timestamp=now.isoformat(),
            action="GENERATED",
            actor="SYSTEM_ALERT_ENGINE",
            role="SYSTEM_ALGORITHM",
            notes=f"Candidate {target_level.value} generated from dynamic risk score {score}."
        )

        cap_payload = self._build_cap_representation(
            alert_id=alert_id,
            district=district,
            cell_id=cell_id,
            level=target_level,
            area_desc=area_desc,
            now=now,
            expiry=expiry_dt,
            instruction=templates[RecipientGroup.LOCAL_COMMUNITY.value].instruction,
            headline=templates[RecipientGroup.LOCAL_COMMUNITY.value].headline,
        )

        alert = AlertModel(
            alert_id=alert_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            district=district,
            target_cell_ids=[cell_id],
            target_area_description=area_desc,
            risk_score=score,
            risk_level=assessment.risk_level,
            operational_alert_level=target_level,
            lifecycle_state=AlertLifecycleState.PENDING_VERIFICATION,
            risk_status="ACTIVE",
            triggering_factors=[f.model_dump() for f in assessment.factors],
            recipient_groups=[
                RecipientGroup.DISTRICT_AUTHORITY,
                RecipientGroup.DISASTER_MANAGEMENT_AUTHORITY,
                RecipientGroup.LOCAL_COMMUNITY,
            ],
            templates=templates,
            verification_required=True,
            expires_at=expiry_dt.isoformat(),
            cooldown_until=cooldown_dt.isoformat(),
            audit_trail=[audit_entry],
            cap_representation=cap_payload,
        )

        self._alerts_db[alert_id] = alert
        return alert

    # --------------------------------------------------------------------------
    # Authorized Verification Workflow (Phase 6 & 7)
    # --------------------------------------------------------------------------
    def verify_alert(self, alert_id: str, request: AlertVerificationRequest) -> Optional[AlertModel]:
        """Processes officer review: APPROVE, REJECT, or EMERGENCY_OVERRIDE."""
        alert = self._alerts_db.get(alert_id)
        if not alert:
            return None

        now = datetime.now(timezone.utc).isoformat()
        action_upper = request.action.strip().upper()

        if action_upper == "APPROVE":
            alert.lifecycle_state = AlertLifecycleState.DISPATCHED  # Approved & dispatched
            alert.verified_at = now
            alert.dispatched_at = now
            alert.verification_officer_id = request.officer_id
            alert.verification_role = request.officer_role
            alert.updated_at = now
            alert.audit_trail.append(
                AlertAuditEntry(
                    timestamp=now,
                    action="APPROVED_AND_DISPATCHED",
                    actor=request.officer_id,
                    role=request.officer_role,
                    notes=request.notes or "Alert verified and approved for recipient dissemination.",
                )
            )

        elif action_upper == "REJECT":
            alert.lifecycle_state = AlertLifecycleState.REJECTED
            alert.verified_at = now
            alert.verification_officer_id = request.officer_id
            alert.verification_role = request.officer_role
            alert.updated_at = now
            alert.audit_trail.append(
                AlertAuditEntry(
                    timestamp=now,
                    action="REJECTED",
                    actor=request.officer_id,
                    role=request.officer_role,
                    notes=request.notes or "Candidate alert rejected following officer review.",
                )
            )

        elif action_upper == "EMERGENCY_OVERRIDE":
            alert.lifecycle_state = AlertLifecycleState.DISPATCHED
            alert.verified_at = now
            alert.dispatched_at = now
            alert.verification_officer_id = request.officer_id
            alert.verification_role = request.officer_role
            alert.updated_at = now
            alert.audit_trail.append(
                AlertAuditEntry(
                    timestamp=now,
                    action="EMERGENCY_OVERRIDE",
                    actor=request.officer_id,
                    role=request.officer_role,
                    notes=f"EMERGENCY OVERRIDE ACTIVATED. {request.notes or ''}".strip(),
                )
            )

        return alert

    def acknowledge_alert(self, alert_id: str, request: AlertAcknowledgeRequest) -> Optional[AlertModel]:
        """Records responding agency acknowledgement in the audit trail."""
        alert = self._alerts_db.get(alert_id)
        if not alert:
            return None

        now = datetime.now(timezone.utc).isoformat()
        alert.lifecycle_state = AlertLifecycleState.ACKNOWLEDGED
        alert.acknowledged_at = now
        alert.updated_at = now
        alert.audit_trail.append(
            AlertAuditEntry(
                timestamp=now,
                action="ACKNOWLEDGED",
                actor=f"{request.officer_id} ({request.agency})",
                role=request.agency,
                notes=request.notes or "Receipt and deployment acknowledgement confirmed.",
            )
        )
        return alert

    def expire_alert(self, alert_id: str, notes: Optional[str] = None) -> Optional[AlertModel]:
        """Manually or automatically marks an alert as expired."""
        alert = self._alerts_db.get(alert_id)
        if not alert:
            return None

        now = datetime.now(timezone.utc).isoformat()
        alert.lifecycle_state = AlertLifecycleState.EXPIRED
        alert.updated_at = now
        alert.audit_trail.append(
            AlertAuditEntry(
                timestamp=now,
                action="EXPIRED",
                actor="SYSTEM_MONITOR",
                role="SYSTEM_ALGORITHM",
                notes=notes or "Alert expired past validity time horizon.",
            )
        )
        return alert

    # --------------------------------------------------------------------------
    # Notification & Telecom Gateway Abstraction (Phase 13 & 14)
    # --------------------------------------------------------------------------
    def get_telecom_gateway_status(self) -> Dict[str, Any]:
        """Truthful status of Cell Broadcast and public notification gateways."""
        return {
            "cell_broadcast": {
                "status": "INTEGRATION_PENDING_AUTHORIZATION",
                "notice": "Cell Broadcast Center (CBC) interface is integration-ready. Actual tower broadcast requires official telecom operator gateway sign-off.",
                "delivery_guarantee": "No simulated or fabricated tower delivery.",
            },
            "sachet_ndma": {
                "status": "CAP_PAYLOAD_READY",
                "notice": "OASIS CAP v1.2 XML/JSON payload is generated and ready for NDMA SACHET API ingestion.",
            },
            "sms_gateway": {"status": "NOT_CONFIGURED"},
            "email_service": {"status": "NOT_CONFIGURED"},
            "web_dashboard": {"status": "ACTIVE"},
        }

    # --------------------------------------------------------------------------
    # Helper Utilities
    # --------------------------------------------------------------------------
    def _level_rank(self, level: OperationalAlertLevel) -> int:
        ranks = {
            OperationalAlertLevel.ADVISORY: 1,
            OperationalAlertLevel.WATCH: 2,
            OperationalAlertLevel.WARNING: 3,
            OperationalAlertLevel.EVACUATION: 4,
        }
        return ranks.get(level, 0)

    def _generate_recipient_templates(
        self,
        district: str,
        cell_id: str,
        level: OperationalAlertLevel,
        score: float,
        area_desc: str,
    ) -> Dict[str, RecipientTemplate]:
        """Generates tailored messaging for the three mandatory recipient tiers (Phase 9)."""
        # 1. District Authority
        dist_template = RecipientTemplate(
            headline=f"[{level.value}] LANDSLIDE ACTION DIRECTIVE — {district.upper()}",
            instruction=(
                f"Emergency Operations Center (EOC) alert for {cell_id} ({area_desc}). "
                f"Risk score: {score:.1f}/100. Restrict heavy transit along vulnerable cut-slopes. "
                f"Deploy road inspection teams to NH corridors and pre-position earth-moving machinery."
            ),
            recommended_action=f"ACTIVATE DISTRICT EOC PROTOCOL ({level.value})",
            tone="TECHNICAL",
        )

        # 2. Disaster Management Authority (SDMA / NDMA)
        sdma_template = RecipientTemplate(
            headline=f"REGIONAL EARLY WARNING NOTICE: {district.upper()} ({level.value})",
            instruction=(
                f"High-threat landslide triggering condition detected in {district} at cell {cell_id}. "
                f"State Disaster Management Authority: Standby NDRF/SDRF emergency battalions. "
                f"Coordinate inter-agency relief logistics and monitor riverine drainage confluence."
            ),
            recommended_action=f"RESOURCE MOBILIZATION STANDBY ({level.value})",
            tone="COORDINATION",
        )

        # 3. Local Community / Public
        if level == OperationalAlertLevel.EVACUATION:
            pub_instruction = (
                f"URGENT: Extreme landslide danger near {area_desc}. "
                f"EVACUATE IMMEDIATELY if you are located along steep toe-slopes or cut-embankments. "
                f"Move to designated community relief shelters. Do not travel on hill roads."
            )
        elif level == OperationalAlertLevel.WARNING:
            pub_instruction = (
                f"LANDSLIDE WARNING: High slope failure risk near {area_desc}. "
                f"Stay away from steep cliffs, hillside roads, and active drainage streams. "
                f"Prepare emergency kits and follow official village authority directives."
            )
        else:
            pub_instruction = (
                f"LANDSLIDE WATCH: Saturated soil conditions near {area_desc}. "
                f"Exercise heightened vigilance. Report fresh surface cracks or muddy seepage to village elders."
            )

        comm_template = RecipientTemplate(
            headline=f"LANDSLIDE SAFETY NOTICE: {district.upper()} — {level.value}",
            instruction=pub_instruction,
            recommended_action="FOLLOW OFFICIAL INSTRUCTIONS • AVOID STEEP SLOPES",
            tone="PUBLIC_SAFETY",
        )

        return {
            RecipientGroup.DISTRICT_AUTHORITY.value: dist_template,
            RecipientGroup.DISASTER_MANAGEMENT_AUTHORITY.value: sdma_template,
            RecipientGroup.LOCAL_COMMUNITY.value: comm_template,
        }

    def _build_cap_representation(
        self,
        alert_id: str,
        district: str,
        cell_id: str,
        level: OperationalAlertLevel,
        area_desc: str,
        now: datetime,
        expiry: datetime,
        instruction: str,
        headline: str,
    ) -> CAPAlert:
        """Serializes OASIS CAP v1.2 envelope (Phase 12)."""
        urgency_map = {
            OperationalAlertLevel.EVACUATION: "Immediate",
            OperationalAlertLevel.WARNING: "Expected",
            OperationalAlertLevel.WATCH: "Future",
            OperationalAlertLevel.ADVISORY: "Future",
        }
        severity_map = {
            OperationalAlertLevel.EVACUATION: "Extreme",
            OperationalAlertLevel.WARNING: "Severe",
            OperationalAlertLevel.WATCH: "Moderate",
            OperationalAlertLevel.ADVISORY: "Minor",
        }

        cap_info = CAPInfo(
            urgency=urgency_map.get(level, "Expected"),
            severity=severity_map.get(level, "Moderate"),
            certainty="Possible",
            headline=headline,
            description=f"Automated early-warning evaluation for {district} cell {cell_id}.",
            instruction=instruction,
            effective=now.isoformat(),
            expires=expiry.isoformat(),
            area=CAPArea(
                areaDesc=area_desc,
                circle=None,
                polygon=None,
            ),
        )

        return CAPAlert(
            identifier=f"CAP-IN-NER-{alert_id}",
            sent=now.isoformat(),
            status="Draft",
            msgType="Alert",
            scope="Public",
            info=cap_info,
        )


# Singleton instance
alert_service = AlertService()
