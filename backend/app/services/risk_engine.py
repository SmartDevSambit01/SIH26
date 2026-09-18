"""
Dynamic Landslide Risk Engine for NER Safe (SIH 2026).
Implements a transparent, configurable, data-driven policy baseline that combines
static terrain susceptibility with multi-source dynamic triggers.
Enforces strict scientific disclosure: this is NOT a trained supervised ML model.
"""

from typing import Dict, Any, List, Optional, Tuple
from ..schemas.risk import RiskFactorEvidence, RiskAssessment
from .data_service import data_service, clean_val


# ==============================================================================
# 1. TRANSPARENT POLICY WEIGHT CONFIGURATION (PHASE 4)
# Centralized policy weights for dynamic trigger components (Sum = 1.0 / 100%)
# These are policy weights, NOT ML-learned parameters.
# ==============================================================================
DYNAMIC_WEIGHTS: Dict[str, float] = {
    "rainfall": 0.45,        # NASA GPM IMERG Precipitation (45%)
    "soil_moisture": 0.35,   # NASA SMAP Volumetric Soil Moisture (35%)
    "flood": 0.10,           # Hydrological Riverine Inundation (10%)
    "satellite": 0.05,       # Copernicus Sentinel-1 SAR Backscatter Anomaly (5%)
    "verification": 0.05,    # Field Inspection & Citizen Corroboration (5%)
}

# Static vs. Dynamic Trigger Combination Weights (Phase 12)
COMBINATION_WEIGHTS: Dict[str, float] = {
    "baseline_susceptibility": 0.50,  # Static terrain morphometry & TSI (50%)
    "dynamic_triggers": 0.50,         # Multi-source dynamic meteorological & radar triggers (50%)
}

# ==============================================================================
# 2. PROTOTYPE POLICY RISK LEVELS (PHASE 13)
# Explicitly documented as prototype thresholds requiring regional calibration.
# ==============================================================================
RISK_LEVEL_THRESHOLDS: List[Tuple[float, str, str]] = [
    (80.0, "Critical", "#A855F7"),   # Score >= 80.0 -> Purple
    (60.0, "High", "#EF4444"),       # Score >= 60.0 -> Red
    (45.0, "Warning", "#F97316"),    # Score >= 45.0 -> Orange
    (30.0, "Watch", "#EAB308"),      # Score >= 30.0 -> Yellow
    (0.0,  "Low", "#22C55E"),        # Score < 30.0  -> Green
]


class RiskEngine:
    """
    Evaluates dynamic landslide risk for 500m grid cells.
    Maintains strict separation between physical hazard risk and exposure/impact.
    Preserves honest unavailable states when external sensor feeds require authentication.
    """

    def __init__(self):
        self.weights = DYNAMIC_WEIGHTS
        self.combination_weights = COMBINATION_WEIGHTS

    def evaluate_cell_risk(
        self,
        cell_id: str,
        dynamic_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[RiskAssessment]:
        """
        Computes dynamic risk assessment for a specific cell.
        dynamic_overrides: Optional dictionary of observation values used for isolated
                           testing of calculation logic without modifying production data.
        """
        cell_summary = data_service.get_cell(cell_id)
        if not cell_summary:
            return None

        district = cell_summary["district"]
        terrain = cell_summary["terrain"]
        baseline = cell_summary["baseline_susceptibility"]
        historical = cell_summary["historical"]

        # Static baseline values
        tsi_score = baseline.get("tsi_score")
        tsi_class = baseline.get("tsi_class")

        # Gather dynamic observations (from overrides or live pipeline data)
        if dynamic_overrides is not None:
            obs = dynamic_overrides
        else:
            params = data_service.get_cell_parameters(cell_id)
            obs = params if params else {}

        factors: List[RiskFactorEvidence] = []
        available_feeds = 0
        total_feeds = 5

        # 1. Baseline Terrain Factor (Static Reference)
        factors.append(
            RiskFactorEvidence(
                factor="terrain_baseline",
                status="AVAILABLE" if tsi_score is not None else "UNAVAILABLE",
                raw_value=tsi_score,
                normalized_score=tsi_score,
                weight=self.combination_weights["baseline_susceptibility"],
                weighted_contribution=(
                    round(tsi_score * self.combination_weights["baseline_susceptibility"], 2)
                    if tsi_score is not None else None
                ),
                description=f"Static Terrain Susceptibility Index (TSI: {tsi_score}/100, Class: {tsi_class or 'N/A'}) derived from SRTM 30m DEM.",
            )
        )

        # 2. Rainfall Scoring (Phase 5)
        rf_factor, rf_available = self._evaluate_rainfall_factor(obs.get("rainfall"))
        factors.append(rf_factor)
        if rf_available:
            available_feeds += 1

        # 3. Soil Moisture Scoring (Phase 6)
        sm_factor, sm_available = self._evaluate_soil_moisture_factor(obs.get("soil_moisture"))
        factors.append(sm_factor)
        if sm_available:
            available_feeds += 1

        # 4. Flood Factor (Phase 7)
        fl_factor, fl_available = self._evaluate_flood_factor(obs.get("flood"))
        factors.append(fl_factor)
        if fl_available:
            available_feeds += 1

        # 5. Satellite SAR Change Factor (Phase 8)
        sat_factor, sat_available = self._evaluate_satellite_factor(obs.get("satellite"))
        factors.append(sat_factor)
        if sat_available:
            available_feeds += 1

        # 6. Verification / Incident Factor (Phase 9)
        ver_factor, ver_available = self._evaluate_verification_factor(
            obs.get("verification"),
            has_verified_historical=historical.get("has_verified_event", False),
            historical_event_id=historical.get("historical_event_id"),
        )
        factors.append(ver_factor)
        if ver_available:
            available_feeds += 1

        data_completeness = round(available_feeds / total_feeds, 2)

        # Availability check (Phase 10 & 12):
        # In the actual prototype project, dynamic feeds (GPM, SMAP, SAR) require NASA/Copernicus auth.
        # If dynamic data is not available, DO NOT manufacture a dynamic trigger score or combined score.
        dynamic_trigger_score: Optional[float] = None
        combined_risk_score: Optional[float] = None
        risk_level: Optional[str] = None
        risk_color: Optional[str] = None
        risk_status: str = "DYNAMIC_RISK_UNAVAILABLE"
        recommendation: str = (
            "Rely on static terrain susceptibility (TSI). Live dynamic risk calculation is suspended "
            "because dynamic sensor feeds (GPM rainfall, SMAP soil moisture) require external authentication."
        )

        # If dynamic feeds ARE available (e.g. through testing fixtures or future authenticated feeds)
        if rf_available and sm_available:
            # Calculate dynamic trigger score
            trigger_sum = sum(
                f.weighted_contribution for f in factors
                if f.factor != "terrain_baseline" and f.weighted_contribution is not None
            )
            dynamic_trigger_score = round(trigger_sum, 2)

            if tsi_score is not None:
                # Combine static baseline (50%) and dynamic triggers (50%)
                combined_risk_score = round(
                    (tsi_score * self.combination_weights["baseline_susceptibility"]) +
                    (dynamic_trigger_score * self.combination_weights["dynamic_triggers"]),
                    2
                )
                risk_level, risk_color = self._map_score_to_risk_level(combined_risk_score)
                risk_status = "ACTIVE"
                recommendation = self._generate_recommendation(risk_level, tsi_class)
            else:
                risk_status = "PENDING_BASELINE_DATA"
                recommendation = "Static terrain baseline is incomplete for this cell."

        return RiskAssessment(
            cell_id=cell_id,
            district=district,
            observation_timestamp=obs.get("observation_timestamp"),
            baseline_susceptibility=tsi_score,
            baseline_class=tsi_class,
            dynamic_trigger_score=dynamic_trigger_score,
            combined_risk_score=combined_risk_score,
            risk_level=risk_level,
            risk_color=risk_color,
            risk_status=risk_status,
            data_completeness=data_completeness,
            calibration_status="NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS",
            factors=factors,
            recommendation=recommendation,
            notice=(
                "Transparent configurable data-driven policy engine. This is NOT a trained supervised "
                "ML probability model. Prototype policy thresholds require regional empirical calibration."
            ),
        )

    # --------------------------------------------------------------------------
    # Factor Evaluation Helpers
    # --------------------------------------------------------------------------

    def _evaluate_rainfall_factor(self, rainfall_obs: Optional[Dict[str, Any]]) -> Tuple[RiskFactorEvidence, bool]:
        """Evaluates precipitation factor across multiple temporal windows."""
        weight = self.weights["rainfall"]

        rate_val = rainfall_obs.get("rainfall_rate_mm_h") if rainfall_obs else None
        if rate_val is None and rainfall_obs:
            rate_val = rainfall_obs.get("rainfall_rate")

        status = rainfall_obs.get("status", "AVAILABLE") if rainfall_obs else "REQUIRES_EXTERNAL_AUTH"

        if not rainfall_obs or (rate_val is None and status == "REQUIRES_EXTERNAL_AUTH"):
            return (
                RiskFactorEvidence(
                    factor="rainfall",
                    status="REQUIRES_EXTERNAL_AUTH",
                    raw_value=None,
                    normalized_score=None,
                    weight=weight,
                    weighted_contribution=None,
                    description="NASA GPM IMERG observations require NASA Earthdata login credentials. No fake rainfall values generated.",
                ),
                False,
            )

        # If actual numerical observation is provided
        rate = float(rate_val or 0.0)
        r24h = float(rainfall_obs.get("rainfall_24h_mm") or rainfall_obs.get("rainfall_24h") or 0.0)
        r72h = float(rainfall_obs.get("rainfall_72h_mm") or rainfall_obs.get("rainfall_72h") or 0.0)

        # Configurable prototype normalization formula:
        # Intensity (rate mm/h up to 50 mm/h) + 24h accumulation (up to 150 mm)
        normalized = min(100.0, max(0.0, (rate / 50.0 * 40.0) + (r24h / 150.0 * 60.0)))
        normalized = round(normalized, 2)
        contribution = round(normalized * weight, 2)

        return (
            RiskFactorEvidence(
                factor="rainfall",
                status=status,
                raw_value={"rate_mm_h": rate, "24h_mm": r24h, "72h_mm": r72h},
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=contribution,
                description=f"Observed NASA GPM rainfall: rate={rate} mm/h, 24h={r24h} mm. Status: {status}.",
            ),
            True,
        )

    def _evaluate_soil_moisture_factor(self, smap_obs: Optional[Dict[str, Any]]) -> Tuple[RiskFactorEvidence, bool]:
        """Evaluates volumetric soil moisture and saturation degree."""
        weight = self.weights["soil_moisture"]

        vol_val = smap_obs.get("volumetric_moisture_m3_m3") if smap_obs else None
        if vol_val is None and smap_obs:
            vol_val = smap_obs.get("soil_moisture_current")

        status = smap_obs.get("status", "STALE") if smap_obs else "REQUIRES_EXTERNAL_AUTH"

        if not smap_obs or (vol_val is None and status == "REQUIRES_EXTERNAL_AUTH"):
            return (
                RiskFactorEvidence(
                    factor="soil_moisture",
                    status="REQUIRES_EXTERNAL_AUTH",
                    raw_value=None,
                    normalized_score=None,
                    weight=weight,
                    weighted_contribution=None,
                    description="NASA SMAP 9km soil moisture observations require NASA Earthdata login credentials. No fake soil moisture values generated.",
                ),
                False,
            )

        current = float(vol_val or 0.0)
        change_pct = float(smap_obs.get("moisture_change_percent") or smap_obs.get("soil_moisture_change_percent") or 0.0)

        # Configurable prototype normalization:
        # Volumetric moisture typically ranges from 0.05 to 0.50 m³/m³ in saturated hillslopes
        normalized = min(100.0, max(0.0, (current / 0.50) * 100.0))
        normalized = round(normalized, 2)
        contribution = round(normalized * weight, 2)

        return (
            RiskFactorEvidence(
                factor="soil_moisture",
                status=status,
                raw_value={"volumetric_m3_m3": current, "change_percent": change_pct},
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=contribution,
                description=f"NASA SMAP Volumetric water content: {current} m³/m³ (saturation ratio: {normalized}%). Status: {status}.",
            ),
            True,
        )

    def _evaluate_flood_factor(self, flood_obs: Optional[Dict[str, Any]]) -> Tuple[RiskFactorEvidence, bool]:
        """Evaluates riverine/drainage flood inundation indicator."""
        weight = self.weights["flood"]

        if not flood_obs or flood_obs.get("flood_indicator") is None:
            return (
                RiskFactorEvidence(
                    factor="flood",
                    status="NOT_YET_IMPLEMENTED",
                    raw_value=None,
                    normalized_score=None,
                    weight=weight,
                    weighted_contribution=None,
                    description="Hydrological flood hazard layer is not yet implemented. Cannot assume zero or safe without data.",
                ),
                False,
            )

        indicator = bool(flood_obs.get("flood_indicator", False))
        normalized = 100.0 if indicator else 0.0
        contribution = round(normalized * weight, 2)

        return (
            RiskFactorEvidence(
                factor="flood",
                status="AVAILABLE",
                raw_value=indicator,
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=contribution,
                description=f"Hydrological flood indicator: {'ACTIVE INUNDATION' if indicator else 'NO INUNDATION'}.",
            ),
            True,
        )

    def _evaluate_satellite_factor(self, sat_obs: Optional[Dict[str, Any]]) -> Tuple[RiskFactorEvidence, bool]:
        """Evaluates Sentinel-1 C-SAR radar backscatter difference."""
        weight = self.weights["satellite"]

        if not sat_obs or sat_obs.get("vv_change_db") is None:
            return (
                RiskFactorEvidence(
                    factor="satellite",
                    status="REQUIRES_EXTERNAL_AUTH",
                    raw_value=None,
                    normalized_score=None,
                    weight=weight,
                    weighted_contribution=None,
                    description="Sentinel-1 SAR scene downloads require Copernicus/Earthdata authentication. Preserved empty without placeholder dB numbers.",
                ),
                False,
            )

        vv = float(sat_obs.get("vv_change_db", 0.0))
        vh = float(sat_obs.get("vh_change_db", 0.0))
        conf = float(sat_obs.get("change_confidence", 0.0))

        # Absolute backscatter change >= 3 dB is treated as significant ground anomaly
        abs_change = max(abs(vv), abs(vh))
        normalized = min(100.0, max(0.0, (abs_change / 6.0) * 100.0))
        normalized = round(normalized, 2)
        contribution = round(normalized * weight, 2)

        return (
            RiskFactorEvidence(
                factor="satellite",
                status="AVAILABLE",
                raw_value={"vv_change_db": vv, "vh_change_db": vh, "confidence": conf},
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=contribution,
                description="SAR backscatter anomaly detected. Corroborating evidence only; never an automatic landslide label.",
            ),
            True,
        )

    def _evaluate_verification_factor(
        self,
        ver_obs: Optional[Dict[str, Any]],
        has_verified_historical: bool = False,
        historical_event_id: Optional[str] = None,
    ) -> Tuple[RiskFactorEvidence, bool]:
        """Evaluates ground verification and citizen field reports."""
        weight = self.weights["verification"]

        if has_verified_historical:
            return (
                RiskFactorEvidence(
                    factor="verification",
                    status="VERIFIED_INCIDENT",
                    raw_value=historical_event_id,
                    normalized_score=100.0,
                    weight=weight,
                    weighted_contribution=round(100.0 * weight, 2),
                    description=f"Confirmed historical landslide ground truth site ({historical_event_id}).",
                ),
                True,
            )

        if not ver_obs or not ver_obs.get("officer_verification_status"):
            return (
                RiskFactorEvidence(
                    factor="verification",
                    status="UNVERIFIED",
                    raw_value=None,
                    normalized_score=0.0,
                    weight=weight,
                    weighted_contribution=0.0,
                    description="No ground officer reports or citizen incident verifications filed for this cell.",
                ),
                True,
            )

        status_str = ver_obs.get("officer_verification_status", "UNVERIFIED")
        normalized = 100.0 if status_str == "VERIFIED" else 50.0 if status_str == "REPORTED" else 0.0

        return (
            RiskFactorEvidence(
                factor="verification",
                status=status_str,
                raw_value=ver_obs,
                normalized_score=normalized,
                weight=weight,
                weighted_contribution=round(normalized * weight, 2),
                description=f"Field verification status: {status_str}.",
            ),
            True,
        )

    def _map_score_to_risk_level(self, score: float) -> Tuple[str, str]:
        """Maps a 0-100 combined score to standard project risk level and color."""
        for threshold, level, color in RISK_LEVEL_THRESHOLDS:
            if score >= threshold:
                return level, color
        return "Low", "#22C55E"

    def _generate_recommendation(self, risk_level: str, tsi_class: Optional[str]) -> str:
        """Generates operational recommendations based on risk categorization."""
        if risk_level == "Critical":
            return "CRITICAL ALERT: Immediate slope stability advisory. Evacuate vulnerable settlements along toe-slopes."
        elif risk_level == "High":
            return "HIGH WARNING: Severe slope distress conditions. Restrict non-essential heavy transport along hill roads."
        elif risk_level == "Warning":
            return "EARLY WARNING: Enhanced vigilance required. Drainage monitoring along highway cut-slopes advised."
        elif risk_level == "Watch":
            return "ADVISORY WATCH: Moderate susceptibility under elevated antecedent saturation. Standard monitoring."
        return "LOW RISK: Stable conditions observed based on current inputs."


# Singleton instance
risk_engine = RiskEngine()
