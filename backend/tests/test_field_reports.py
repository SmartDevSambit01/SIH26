"""
Tests for the field verification / citizen report workflow (PRD.md Section 39).
Verifies:
1. Creating a report against an unknown cell 404s (no silent fabrication).
2. Full lifecycle: create -> PENDING -> verify -> VERIFIED.
3. REJECT never contributes evidence.
4. A VERIFIED report genuinely changes the cell's verification factor in the
   risk engine (Section 39: "Allow reports to feed back into risk evidence"),
   not just a decorative status flag.
5. citizen_reports_filed in cell parameters reflects the real count, not the
   old hardcoded 0.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

TEST_CELL = "AIZ_00050"  # a cell distinct from other tests' fixtures, no verified historical event expected


def test_create_report_unknown_cell_404s():
    response = client.post("/api/field-reports", json={
        "cell_id": "NOT_A_REAL_CELL",
        "report_type": "ROCKFALL",
        "description": "test",
        "reporter_role": "CITIZEN",
    })
    assert response.status_code == 404


def test_report_lifecycle_create_then_verify():
    create_resp = client.post("/api/field-reports", json={
        "cell_id": TEST_CELL,
        "report_type": "FRESH_DEBRIS",
        "description": "Fresh debris observed on the slope after heavy rain.",
        "reporter_role": "CITIZEN",
        "confidence": "MEDIUM",
    })
    assert create_resp.status_code == 201
    report = create_resp.json()
    assert report["verification_status"] == "PENDING"
    assert report["district"] in {"Kohima", "Aizawl"}

    report_id = report["report_id"]

    get_resp = client.get(f"/api/field-reports/{report_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["verification_status"] == "PENDING"

    verify_resp = client.post(f"/api/field-reports/{report_id}/verify", json={
        "action": "VERIFY",
        "officer_id": "OFFICER_001",
        "officer_role": "FIELD_OFFICER",
    })
    assert verify_resp.status_code == 200
    verified = verify_resp.json()
    assert verified["verification_status"] == "VERIFIED"
    assert verified["verified_by"] == "FIELD_OFFICER:OFFICER_001"


def test_rejected_report_never_contributes_evidence():
    create_resp = client.post("/api/field-reports", json={
        "cell_id": "AIZ_00051",
        "report_type": "OTHER",
        "description": "Unverifiable claim.",
        "reporter_role": "CITIZEN",
    })
    report_id = create_resp.json()["report_id"]

    reject_resp = client.post(f"/api/field-reports/{report_id}/verify", json={
        "action": "REJECT",
        "officer_id": "OFFICER_002",
        "officer_role": "FIELD_OFFICER",
        "notes": "No corroborating evidence.",
    })
    assert reject_resp.status_code == 200
    assert reject_resp.json()["verification_status"] == "REJECTED"

    params = client.get("/api/cells/AIZ_00051/parameters").json()
    assert params["verification"]["officer_verification_status"] != "VERIFIED"


def test_verified_report_feeds_back_into_risk_engine():
    cell_id = "AIZ_00060"
    create_resp = client.post("/api/field-reports", json={
        "cell_id": cell_id,
        "report_type": "ROAD_SETTLEMENT",
        "description": "Road surface settlement observed near the shoulder.",
        "reporter_role": "FIELD_OFFICER",
    })
    report_id = create_resp.json()["report_id"]

    # Before verification: not yet contributing evidence.
    params_before = client.get(f"/api/cells/{cell_id}/parameters").json()
    assert params_before["verification"]["officer_verification_status"] != "VERIFIED"

    client.post(f"/api/field-reports/{report_id}/verify", json={
        "action": "VERIFY", "officer_id": "OFFICER_003", "officer_role": "DISTRICT_ADMIN",
    })

    params_after = client.get(f"/api/cells/{cell_id}/parameters").json()
    assert params_after["verification"]["officer_verification_status"] == "VERIFIED"
    assert params_after["verification"]["citizen_reports_filed"] >= 1
    assert params_after["verification"]["verified_field_reports"] >= 1


def test_list_field_reports_filters_by_cell():
    response = client.get(f"/api/field-reports?cell_id={TEST_CELL}")
    assert response.status_code == 200
    reports = response.json()
    assert all(r["cell_id"] == TEST_CELL for r in reports)
    assert len(reports) >= 1
