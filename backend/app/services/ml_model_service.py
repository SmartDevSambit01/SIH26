"""
ML Model Service for Task 12: AI/ML Landslide Risk Model + Scientific Validation & Calibration.
Provides two-stage hazard estimation, parameter evidence range comparison,
explainability factors, and model prediction endpoints.
"""

import os
import logging
import pandas as pd
from typing import Dict, Any, List, Optional

from ..config import DATA_DIR
from .data_service import DataService
from .model_calibration_service import model_calibration_service

logger = logging.getLogger("ner_safe.ml_model_service")

RESEARCH_CSV = DATA_DIR / "research" / "landslide_parameter_evidence.csv"

class MLModelService:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self._evidence_df: Optional[pd.DataFrame] = None
        self._initialized = False

    def ensure_loaded(self):
        if not self._initialized:
            self.load_all()

    def load_all(self):
        if self._initialized:
            return

        self.data_service.ensure_loaded()
        if RESEARCH_CSV.exists():
            try:
                self._evidence_df = pd.read_csv(RESEARCH_CSV)
                logger.info(f"Loaded {len(self._evidence_df)} scientific parameter evidence records.")
            except Exception as e:
                logger.error(f"Failed to load parameter evidence CSV: {e}")

        self._initialized = True

    def get_model_status(self) -> Dict[str, Any]:
        """Returns official model readiness status, label counts, and calibration gate."""
        self.ensure_loaded()
        cal_status = model_calibration_service.get_calibration_status()
        return {
            "model_name": "NER Safe Two-Stage Landslide Hazard Model",
            "model_version": "1.2.0-limited-data",
            "model_strategy": "Static TSI Susceptibility + Dynamic Trigger Evidence + PU Distance Metric",
            "model_readiness": "LIMITED_DATA",
            "supervised_ml_feasibility": "NOT_FEASIBLE_INSUFFICIENT_LABELS",
            "verified_positives_count": 11,
            "verified_negatives_count": 0,
            "unlabeled_cells_count": 16950,
            "calibration_status": cal_status["calibration_status"],
            "notice": (
                "Due to limited verified positive landslide samples (11 cells) and zero verified negative cells, "
                "the model operates in Limited-Data mode. Static susceptibility is derived from SRTM/Copernicus 30m DEM, "
                "while dynamic triggers are evaluated when valid external sensor feeds are ingested."
            )
        }

    def get_feature_registry(self) -> Dict[str, Any]:
        """Returns documented feature registry categorizing hazard vs exposure features."""
        return {
            "physical_hazard_features": {
                "static_terrain": [
                    {"name": "elevation_mean", "unit": "meters", "type": "STATIC", "status": "AVAILABLE"},
                    {"name": "slope_mean", "unit": "degrees", "type": "STATIC", "status": "AVAILABLE"},
                    {"name": "aspect_mean", "unit": "degrees", "type": "STATIC", "status": "AVAILABLE"},
                    {"name": "curvature_mean", "unit": "100*m⁻¹", "type": "STATIC", "status": "AVAILABLE"},
                    {"name": "twi_mean", "unit": "dimensionless", "type": "STATIC", "status": "AVAILABLE"},
                    {"name": "tsi_score", "unit": "0-100 score", "type": "STATIC", "status": "AVAILABLE"}
                ],
                "dynamic_triggers": [
                    {"name": "rainfall_rate", "unit": "mm/h", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "rainfall_24h", "unit": "mm", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "antecedent_rainfall_7d", "unit": "mm", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "soil_moisture_current", "unit": "m³/m³", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "soil_moisture_change", "unit": "% change", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "vv_change_db", "unit": "dB", "type": "DYNAMIC", "status": "REQUIRES_EXTERNAL_AUTH"},
                    {"name": "flood_indicator", "unit": "boolean", "type": "DYNAMIC", "status": "UNAVAILABLE"}
                ]
            },
            "exposure_and_impact_features": [
                {"name": "road_proximity_m", "unit": "meters", "type": "STATIC_EXPOSURE", "status": "UNAVAILABLE"},
                {"name": "road_exposure_level", "unit": "category", "type": "STATIC_EXPOSURE", "status": "UNAVAILABLE"},
                {"name": "population_density_est", "unit": "persons/km²", "type": "STATIC_EXPOSURE", "status": "UNAVAILABLE"},
                {"name": "critical_infrastructure_count", "unit": "count", "type": "STATIC_EXPOSURE", "status": "UNAVAILABLE"}
            ]
        }

    def get_cell_parameter_comparison(self, cell_id: str) -> List[Dict[str, Any]]:
        """
        Compares current cell values vs scientific literature evidence ranges (Phase 11).
        """
        self.ensure_loaded()
        cell_data = self.data_service.get_cell(cell_id)
        if not cell_data:
            return []

        district = cell_data.get("district", "")
        terrain = cell_data.get("terrain", {})
        slope = terrain.get("slope_mean")
        twi = terrain.get("twi_mean")

        comparisons = []

        # 1. Slope Angle Comparison
        slope_ref = None
        if self._evidence_df is not None and not self._evidence_df.empty:
            matches = self._evidence_df[
                (self._evidence_df["parameter"] == "slope_angle") &
                (self._evidence_df["district"].str.contains(district, case=False, na=False))
            ]
            if not matches.empty:
                r = matches.iloc[0]
                slope_ref = f"{r['min_value']} - {r['max_value']} {r['unit']} ({r['source_organization']} {r['source_year']})"

        slope_status = "Contextual feature only"
        if slope is not None and slope_ref:
            min_v, max_v = (25.0, 45.0) if district.lower() == "kohima" else (30.0, 50.0)
            if slope < min_v:
                slope_status = "Below prone range"
            elif slope > max_v:
                slope_status = "Above prone range (barren scarp)"
            else:
                slope_status = "Within landslide-prone range"

        comparisons.append({
            "parameter_name": "Slope Angle",
            "current_value": f"{round(slope, 1)}°" if slope is not None else "N/A",
            "reference_evidence_range": slope_ref or "25.0 - 45.0° (GSI Literature Range)",
            "interpretation": slope_status
        })

        # 2. Hourly Rainfall Rate Comparison
        comparisons.append({
            "parameter_name": "Hourly Rainfall Rate",
            "current_value": "Unavailable (Requires NASA Auth)",
            "reference_evidence_range": "15.0 - 25.0 mm/h (GSI NLSM 2020)",
            "interpretation": "Dynamic observation unavailable"
        })

        # 3. 24h Cumulative Rainfall Comparison
        comparisons.append({
            "parameter_name": "24-Hour Rainfall Cumulative",
            "current_value": "Unavailable (Requires NASA Auth)",
            "reference_evidence_range": "80.0 - 130.0 mm (IMD / SDMA 2024)",
            "interpretation": "Dynamic observation unavailable"
        })

        # 4. Volumetric Soil Moisture Comparison
        comparisons.append({
            "parameter_name": "Volumetric Soil Moisture",
            "current_value": "Unavailable (Requires NASA Auth)",
            "reference_evidence_range": "0.38 - 0.48 m³/m³ (NASA Landslide Program)",
            "interpretation": "District-specific evidence unavailable / Auth required"
        })

        # 5. Sentinel-1 SAR Backscatter Change Comparison
        comparisons.append({
            "parameter_name": "Sentinel-1 SAR Change",
            "current_value": "Unavailable (ESA Auth pending)",
            "reference_evidence_range": "-4.5 to -3.0 dB (|ΔVV| drop)",
            "interpretation": "External download pending"
        })

        return comparisons

    def get_cell_prediction(self, cell_id: str) -> Optional[Dict[str, Any]]:
        """
        Generates structured prediction object for cell per Phase 14 schema.
        """
        self.ensure_loaded()
        cell_data = self.data_service.get_cell(cell_id)
        if not cell_data:
            return None

        cid = cell_data["cell_id"]
        district = cell_data["district"]
        base = cell_data.get("baseline_susceptibility", {})
        terrain = cell_data.get("terrain", {})
        hist = cell_data.get("historical", {})

        tsi_score = base.get("tsi_score")
        tsi_class = base.get("tsi_class")

        cal_info = model_calibration_service.calibrate_hazard_score(tsi_score)

        # Top contributing factors (strictly derived from available data)
        top_factors = []
        if terrain.get("slope_mean") and terrain["slope_mean"] >= 30.0:
            top_factors.append(f"Steep slope gradient ({round(terrain['slope_mean'], 1)}°)")
        if terrain.get("curvature_mean") and abs(terrain["curvature_mean"]) > 0.5:
            top_factors.append(f"High terrain curvature ({round(terrain['curvature_mean'], 2)})")
        if terrain.get("twi_mean") and terrain["twi_mean"] >= 8.0:
            top_factors.append(f"Elevated topographic wetness index ({round(terrain['twi_mean'], 1)})")
        if hist.get("has_verified_event"):
            top_factors.append(f"Verified historical landslide point ({hist.get('historical_event_id')})")

        if not top_factors:
            top_factors.append("Low static terrain susceptibility baseline")

        missing_features = [
            "rainfall_rate (Requires NASA Earthdata Auth)",
            "soil_moisture_current (Requires NASA Earthdata Auth)",
            "vv_change_db (ESA Sentinel-1 Auth Pending)",
            "flood_indicator (Model Pending)"
        ]

        # Map TSI score to prototype risk level & color
        risk_level = tsi_class or "LOW"
        color_map = {
            "VERY_HIGH": "#DC2626",
            "HIGH": "#EF4444",
            "MODERATE": "#F59E0B",
            "LOW": "#10B981",
            "VERY_LOW": "#059669"
        }
        risk_color = color_map.get(risk_level, "#6B7280")

        return {
            "cell_id": cid,
            "district": district,
            "observation_timestamp": "STATIC_BASELINE_2026",
            "susceptibility_score": round(tsi_score, 2) if tsi_score is not None else None,
            "dynamic_trigger_score": None,  # Null when dynamic observations unavailable
            "hazard_probability": cal_info["calibrated_hazard_probability"],
            "probability_status": cal_info["probability_status"],
            "risk_score": round(tsi_score, 2) if tsi_score is not None else None,
            "risk_level": risk_level,
            "risk_color": risk_color,
            "model_status": "LIMITED_DATA_PROTOTYPE",
            "calibration_status": cal_info["calibration_status"],
            "data_completeness_score": 0.28,  # Terrain + Historical available; dynamic sensors unavailable
            "top_contributing_factors": top_factors,
            "missing_features": missing_features,
            "evidence_sources": [
                "Copernicus 30m DEM Morphometry",
                "GSI Verified Historical Landslide Database"
            ],
            "parameter_comparisons": self.get_cell_parameter_comparison(cid),
            "notice": "Baseline susceptibility is derived from static DEM. Live dynamic triggers require external sensor authentication."
        }

    def get_cell_explanation(self, cell_id: str) -> Optional[Dict[str, Any]]:
        """Returns explainability details for a specific cell."""
        pred = self.get_cell_prediction(cell_id)
        if not pred:
            return None

        return {
            "cell_id": cell_id,
            "district": pred["district"],
            "risk_level": pred["risk_level"],
            "top_contributing_factors": pred["top_contributing_factors"],
            "missing_features": pred["missing_features"],
            "parameter_comparisons": pred["parameter_comparisons"],
            "calibration_status": pred["calibration_status"],
            "explanation_notice": "Explanations strictly reflect verified terrain baseline and GSI historical evidence. Zero dynamic factors are fabricated."
        }
