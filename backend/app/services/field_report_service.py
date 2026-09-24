"""
Field Verification Service for SARVAS/NER Safe (PRD.md Section 39, 51-52).
Human ground verification (citizen or officer) is a first-class evidence
source: verified reports feed back into the dynamic risk engine's
verification factor (risk_engine._evaluate_verification_factor), reducing
dependence on any single satellite sensor.

In-memory store, matching the existing alert_service.py architecture (no
PostgreSQL/PostGIS is wired up yet — see AUDIT_REPORT.md).
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ..schemas.field_report import (
    FieldReport,
    FieldReportCreate,
    FieldReportVerifyRequest,
    VerificationStatus,
)
from .data_service import DataService


class FieldReportService:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self._reports: Dict[str, FieldReport] = {}

    def create_report(self, payload: FieldReportCreate) -> Optional[FieldReport]:
        cell = self.data_service.get_cell(payload.cell_id)
        if not cell:
            return None

        now = datetime.now(timezone.utc)
        report_id = f"FR_{cell['district'][:3].upper()}_{now.strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"

        report = FieldReport(
            report_id=report_id,
            cell_id=payload.cell_id,
            district=cell["district"],
            latitude=cell["latitude"],
            longitude=cell["longitude"],
            report_type=payload.report_type,
            description=payload.description,
            reporter_role=payload.reporter_role,
            confidence=payload.confidence,
            evidence_note=payload.evidence_note,
            verification_status=VerificationStatus.PENDING,
            created_at=now.isoformat(),
        )
        self._reports[report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[FieldReport]:
        return self._reports.get(report_id)

    def list_reports(
        self,
        cell_id: Optional[str] = None,
        district: Optional[str] = None,
        verification_status: Optional[str] = None,
    ) -> List[FieldReport]:
        results = list(self._reports.values())
        if cell_id:
            results = [r for r in results if r.cell_id == cell_id]
        if district:
            results = [r for r in results if r.district.lower() == district.lower()]
        if verification_status:
            results = [r for r in results if r.verification_status.value == verification_status.upper()]
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def verify_report(self, report_id: str, request: FieldReportVerifyRequest) -> Optional[FieldReport]:
        report = self._reports.get(report_id)
        if not report:
            return None

        action = request.action.upper()
        now = datetime.now(timezone.utc).isoformat()

        if action == "VERIFY":
            report.verification_status = VerificationStatus.VERIFIED
            report.verified_at = now
            report.verified_by = f"{request.officer_role}:{request.officer_id}"
        elif action == "REJECT":
            report.verification_status = VerificationStatus.REJECTED
            report.verified_at = now
            report.verified_by = f"{request.officer_role}:{request.officer_id}"
            report.rejection_reason = request.notes
        else:
            raise ValueError(f"Unknown verification action: {request.action}")

        return report

    def get_cell_verification_summary(self, cell_id: str) -> dict:
        """Feeds risk_engine._evaluate_verification_factor and the cell
        parameters 'verification' block with real (not hardcoded) counts."""
        reports = self.list_reports(cell_id=cell_id)
        verified = [r for r in reports if r.verification_status == VerificationStatus.VERIFIED]
        pending = [r for r in reports if r.verification_status == VerificationStatus.PENDING]

        if verified:
            status = "VERIFIED"
        elif pending:
            status = "REPORTED"
        else:
            status = "UNVERIFIED"

        return {
            "officer_verification_status": status,
            "citizen_reports_filed": len(reports),
            "verified_reports": len(verified),
            "pending_reports": len(pending),
        }


# Singleton instance (constructed against the shared data_service singleton in services/__init__.py)
