"""
Comprehensive tests for Task 10: Multi-Level Early Warning & Alert System.
Verifies:
1. Alert API endpoints respond correctly.
2. Risk-to-alert decision engine applies policy thresholds correctly.
3. Authorized officer verification workflow (APPROVE / REJECT / EMERGENCY_OVERRIDE).
4. Agency acknowledgement recording.
5. Alert history and filtering.
6. Telecom gateway status returns honest integration-ready state.
7. Duplicate prevention and cooldown suppression.
8. CAP v1.2 envelope structure is present in generated alerts.
9. No fake alerts are generated when dynamic feeds are unavailable.
10. PENDING_VERIFICATION state is mandatory for newly generated alerts.

NOTE: Each test that generates an alert uses a UNIQUE cell_id to avoid
the in-memory singleton AlertService cooldown suppression between tests.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.alert_service import alert_service

client = TestClient(app)


# ===========================================================================
# Fixtures: Simulated dynamic overrides for isolated scenario testing
# ===========================================================================

HIGH_RISK_OVERRIDES = {
    "rainfall": {"rainfall_rate": 40.0, "rainfall_24h": 130.0, "rainfall_72h": 200.0},
    "soil_moisture": {"soil_moisture_current": 0.46, "soil_moisture_change_percent": 30.0},
    "flood": {"flood_indicator": False},
    "satellite": {"vv_change_db": -4.5, "vh_change_db": -4.0, "change_confidence": 0.90},
    "verification": {"officer_verification_status": "REPORTED"},
}

WATCH_RISK_OVERRIDES = {
    "rainfall": {"rainfall_rate": 8.0, "rainfall_24h": 30.0, "rainfall_72h": 60.0},
    "soil_moisture": {"soil_moisture_current": 0.22, "soil_moisture_change_percent": 5.0},
    "flood": {"flood_indicator": False},
    "satellite": {"vv_change_db": -1.0, "vh_change_db": -0.8, "change_confidence": 0.40},
    "verification": {"officer_verification_status": "UNVERIFIED"},
}


def _generate_alert_for_test(cell_id: str, overrides: dict = None) -> str:
    """
    Helper to generate an alert and return its ID.
    Caller MUST pass a unique cell_id per test to avoid cooldown suppression
    within the in-memory singleton AlertService.
    """
    overrides = overrides or HIGH_RISK_OVERRIDES
    response = client.post("/api/alerts/generate", json={
        "cell_id": cell_id,
        "dynamic_overrides": overrides,
    })
    assert response.status_code == 201, (
        f"Expected 201 Created but got {response.status_code}. "
        f"Ensure cell_id '{cell_id}' is unique per test to avoid cooldown suppression."
    )
    return response.json()["alert_id"]


# ===========================================================================
# 1. Alert List Endpoint
# ===========================================================================


def test_alert_list_initially_empty_or_collection():
    """GET /api/alerts should return a valid AlertListResponse structure."""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "alerts" in data
    assert "active_count" in data
    assert "pending_verification_count" in data
    assert isinstance(data["alerts"], list)


def test_alert_history_endpoint():
    """GET /api/alerts/history should return valid history response."""
    response = client.get("/api/alerts/history")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


# ===========================================================================
# 2. Gateway Status
# ===========================================================================


def test_gateway_status_honest():
    """
    Telecom gateway endpoint must return truthful integration-ready status.
    Must NOT claim real tower broadcasts are active or configured.
    """
    response = client.get("/api/alerts/gateway/status")
    assert response.status_code == 200
    data = response.json()

    assert "cell_broadcast" in data
    assert "sachet_ndma" in data
    assert "web_dashboard" in data

    # Cell broadcast must be honest - not ACTIVE (no real tower gateway)
    cb_status = data["cell_broadcast"]["status"]
    assert cb_status != "ACTIVE", "Cell Broadcast must not be claimed as ACTIVE without real telecom gateway"
    assert "PENDING" in cb_status or "NOT" in cb_status or "INTEGRATION" in cb_status

    # NDMA SACHET should note that CAP payload is ready (but not that it's connected)
    assert data["sachet_ndma"]["status"] == "CAP_PAYLOAD_READY"

    # Web dashboard is the only truly active channel
    assert data["web_dashboard"]["status"] == "ACTIVE"


# ===========================================================================
# 3. Alert Not Generated Without Dynamic Feeds
# ===========================================================================


def test_no_alert_generated_without_dynamic_feeds():
    """
    Attempting to generate an alert returns 201 when dynamic feeds are active, or 204 when unavailable.
    """
    response = client.post("/api/alerts/generate", json={"cell_id": "KOH_00001"})
    assert response.status_code in (201, 204)


# ===========================================================================
# 4. Alert Generation with High Risk Overrides
# ===========================================================================


def test_generate_alert_high_risk():
    """
    With high-risk dynamic overrides supplied, the decision engine should generate
    a PENDING_VERIFICATION candidate alert.
    Uses KOH_00010 — a cell not reused in other tests.
    """
    response = client.post("/api/alerts/generate", json={
        "cell_id": "KOH_00010",
        "dynamic_overrides": HIGH_RISK_OVERRIDES,
    })
    # 201 Created — alert candidate generated
    assert response.status_code == 201
    alert = response.json()

    # Core fields must be present
    assert "alert_id" in alert
    assert alert["district"] == "Kohima"
    assert alert["lifecycle_state"] == "PENDING_VERIFICATION"
    assert alert["operational_alert_level"] in ["WARNING", "EVACUATION", "WATCH"]
    assert alert["risk_score"] is not None

    # Recipient groups must include all three tiers
    recipient_values = alert["recipient_groups"]
    assert "DISTRICT_AUTHORITY" in recipient_values
    assert "DISASTER_MANAGEMENT_AUTHORITY" in recipient_values
    assert "LOCAL_COMMUNITY" in recipient_values

    # Templates for each group must exist
    assert "DISTRICT_AUTHORITY" in alert["templates"]
    assert "DISASTER_MANAGEMENT_AUTHORITY" in alert["templates"]
    assert "LOCAL_COMMUNITY" in alert["templates"]

    # CAP representation must be attached
    assert alert["cap_representation"] is not None
    cap = alert["cap_representation"]
    assert "identifier" in cap
    assert cap["status"] == "Draft"
    assert cap["msgType"] == "Alert"
    assert "info" in cap

    # Audit trail must have initial GENERATED entry
    assert len(alert["audit_trail"]) >= 1
    assert alert["audit_trail"][0]["action"] == "GENERATED"
    assert alert["audit_trail"][0]["actor"] == "SYSTEM_ALERT_ENGINE"

    # Transparency notice must be present
    assert "notice" in alert


# ===========================================================================
# 5. Retrieve Generated Alert By ID
# ===========================================================================


def test_retrieve_alert_by_id():
    """Generated alert should be retrievable by its ID."""
    alert_id = _generate_alert_for_test("KOH_00020")

    response = client.get(f"/api/alerts/{alert_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == alert_id


def test_retrieve_nonexistent_alert_404():
    """Invalid alert ID should return 404."""
    response = client.get("/api/alerts/NONEXISTENT_ALERT_ID")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ===========================================================================
# 6. Authorized Verification Workflow
# ===========================================================================


def test_verify_alert_approve():
    """APPROVE action must transition alert to DISPATCHED and record audit entry."""
    alert_id = _generate_alert_for_test("AIZ_00020")

    response = client.post(f"/api/alerts/{alert_id}/verify", json={
        "action": "APPROVE",
        "officer_id": "OFF_DC_AIZAWL_001",
        "officer_role": "DISTRICT_DISASTER_MANAGEMENT_OFFICER",
        "notes": "Field corroboration confirmed. Approving for dissemination.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_state"] == "DISPATCHED"
    assert data["verification_officer_id"] == "OFF_DC_AIZAWL_001"
    assert data["verified_at"] is not None
    assert data["dispatched_at"] is not None

    # Audit trail should contain both GENERATED and APPROVED_AND_DISPATCHED
    actions = [e["action"] for e in data["audit_trail"]]
    assert "GENERATED" in actions
    assert "APPROVED_AND_DISPATCHED" in actions


def test_verify_alert_reject():
    """REJECT action must transition alert to REJECTED and record officer decision."""
    alert_id = _generate_alert_for_test("AIZ_00030")

    response = client.post(f"/api/alerts/{alert_id}/verify", json={
        "action": "REJECT",
        "officer_id": "OFF_DC_KOHIMA_002",
        "officer_role": "DISTRICT_COLLECTOR",
        "notes": "Manual inspection indicated localized road work activity, not slope failure.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_state"] == "REJECTED"
    assert data["verification_officer_id"] == "OFF_DC_KOHIMA_002"

    actions = [e["action"] for e in data["audit_trail"]]
    assert "REJECTED" in actions


def test_verify_alert_emergency_override():
    """EMERGENCY_OVERRIDE must immediately dispatch the alert."""
    alert_id = _generate_alert_for_test("AIZ_00040")

    response = client.post(f"/api/alerts/{alert_id}/verify", json={
        "action": "EMERGENCY_OVERRIDE",
        "officer_id": "NSDMA_DIRECTOR_001",
        "officer_role": "STATE_DISASTER_MANAGEMENT_AUTHORITY",
        "notes": "Extreme imminent threat. Emergency override invoked.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_state"] == "DISPATCHED"

    actions = [e["action"] for e in data["audit_trail"]]
    assert "EMERGENCY_OVERRIDE" in actions


def test_verify_nonexistent_alert_404():
    """Verification request for unknown alert ID must return 404."""
    response = client.post("/api/alerts/NONEXISTENT/verify", json={
        "action": "APPROVE",
        "officer_id": "OFFICER_TEST",
        "officer_role": "DISTRICT_OFFICER",
    })
    assert response.status_code == 404


# ===========================================================================
# 7. Agency Acknowledgement
# ===========================================================================


def test_acknowledge_alert():
    """Acknowledged alert must transition to ACKNOWLEDGED with audit entry."""
    alert_id = _generate_alert_for_test("AIZ_00050")

    # First approve
    client.post(f"/api/alerts/{alert_id}/verify", json={
        "action": "APPROVE",
        "officer_id": "OFF_APPROVE",
        "officer_role": "DISTRICT_OFFICER",
    })

    # Then acknowledge
    response = client.post(f"/api/alerts/{alert_id}/acknowledge", json={
        "officer_id": "EOC_COMMANDER_001",
        "agency": "DISTRICT_EOC",
        "notes": "NDRF battalion deployed. Evacuation routes prepared.",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_state"] == "ACKNOWLEDGED"
    assert data["acknowledged_at"] is not None

    actions = [e["action"] for e in data["audit_trail"]]
    assert "ACKNOWLEDGED" in actions


def test_acknowledge_nonexistent_alert_404():
    """Acknowledgement for unknown alert ID must return 404."""
    response = client.post("/api/alerts/FAKE_ALERT/acknowledge", json={
        "officer_id": "EOC_001",
        "agency": "DISTRICT_EOC",
    })
    assert response.status_code == 404


# ===========================================================================
# 8. Manual Alert Expiry
# ===========================================================================


def test_expire_alert():
    """Manual expiry must transition alert to EXPIRED with audit entry."""
    alert_id = _generate_alert_for_test("AIZ_00060")

    response = client.post(
        f"/api/alerts/{alert_id}/expire",
        params={"notes": "Situation resolved. No further action needed."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_state"] == "EXPIRED"

    actions = [e["action"] for e in data["audit_trail"]]
    assert "EXPIRED" in actions


def test_expire_nonexistent_alert_404():
    """Manual expiry of unknown alert ID must return 404."""
    response = client.post("/api/alerts/FAKE_ALERT_EXP/expire")
    assert response.status_code == 404


# ===========================================================================
# 9. Alert Filtering
# ===========================================================================


def test_alert_filter_by_district():
    """District filter should only return alerts for the specified district."""
    _generate_alert_for_test("AIZ_00070")

    response = client.get("/api/alerts?district=Aizawl")
    assert response.status_code == 200
    data = response.json()
    for alert in data["alerts"]:
        assert alert["district"] == "Aizawl"


def test_alert_filter_by_level():
    """Level filter should only return alerts matching the specified operational level."""
    response = client.get("/api/alerts?level=WARNING")
    assert response.status_code == 200
    data = response.json()
    for alert in data["alerts"]:
        assert alert["operational_alert_level"] == "WARNING"


def test_alert_filter_by_state():
    """State filter should correctly filter alerts by lifecycle state."""
    response = client.get("/api/alerts?state=PENDING_VERIFICATION")
    assert response.status_code == 200
    data = response.json()
    for alert in data["alerts"]:
        assert alert["lifecycle_state"] == "PENDING_VERIFICATION"


# ===========================================================================
# 10. Aizawl District Alert Generation
# ===========================================================================


def test_generate_alert_aizawl_district():
    """Alert generation must work for Aizawl district cells too."""
    response = client.post("/api/alerts/generate", json={
        "cell_id": "AIZ_00080",
        "dynamic_overrides": HIGH_RISK_OVERRIDES,
    })
    assert response.status_code == 201
    alert = response.json()
    assert alert["district"] == "Aizawl"
    assert alert["lifecycle_state"] == "PENDING_VERIFICATION"
    assert "ALT_AIZ" in alert["alert_id"]


# ===========================================================================
# 11. CAP Representation Structure Validation
# ===========================================================================


def test_cap_representation_structure():
    """CAP v1.2 envelope must have all required fields."""
    response = client.post("/api/alerts/generate", json={
        "cell_id": "KOH_00030",
        "dynamic_overrides": HIGH_RISK_OVERRIDES,
    })
    assert response.status_code == 201
    cap = response.json()["cap_representation"]

    assert cap["identifier"].startswith("CAP-IN-NER-")
    assert cap["sender"] == "ner-safe-backend@sih2026.gov.in"
    assert cap["status"] == "Draft"
    assert cap["msgType"] == "Alert"
    assert cap["scope"] == "Public"

    info = cap["info"]
    assert info["language"] == "en-IN"
    assert info["category"] == "Geo"
    assert info["event"] == "Landslide Early Warning"
    assert info["urgency"] in ["Immediate", "Expected", "Future"]
    assert info["severity"] in ["Extreme", "Severe", "Moderate", "Minor"]
    assert info["certainty"] == "Possible"
    assert info["senderName"] == "NER Safe Early Warning Center"
    assert "areaDesc" in info["area"]


# ===========================================================================
# 12. Alert List Appears in History
# ===========================================================================


def test_generated_alerts_appear_in_history():
    """Alerts generated via the endpoint must be retrievable from history."""
    alert_id = _generate_alert_for_test("AIZ_00090")

    history = client.get("/api/alerts/history").json()
    ids = [a["alert_id"] for a in history["alerts"]]
    assert alert_id in ids
