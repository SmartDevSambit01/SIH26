#!/usr/bin/env python3
"""
audit_dynamic_risk_readiness.py — Dynamic Data Readiness Audit Script

STEP 9B — Task 1: Dynamic Data Readiness Audit
NER Safe (SIH 2026) — AI-Based Early Warning and Landslide Risk Monitoring System
Pilot Districts: Kohima (Nagaland) · Aizawl (Mizoram)

Inspects the existing project datasets and documentation to audit the readiness of:
  1. Rainfall indicators (GPM IMERG 0.1° / ~10 km, 30-minute / multi-temporal)
  2. Soil moisture indicators (SMAP 9 km daily)
  3. Satellite change indicators (Sentinel-1 C-SAR IW GRD 12-day repeat)
  4. Terrain morphometry & baseline susceptibility (Copernicus DEM 30m, Step 9A TSI)
  5. Flood indicators (Surface water model / drainage basin context)
  6. Human verification & field reports (Mobile crowdsource, officer validation)
  7. Exposure & consequence assets (Roads, proximity, villages, population, critical infra)

Strict adherence to the Anti-Fabrication and Scientific Truthfulness Protocol:
  - Missing data remains missing.
  - Zero-imputation is strictly forbidden unless zero is scientifically valid.
  - No synthetic, random, or dummy observations are generated.
  - No ML models are trained.
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ML_DIR = DATA_DIR / "ml"
HISTORICAL_DIR = DATA_DIR / "historical"
SATELLITE_DIR = DATA_DIR / "satellite"

FEATURE_DATASET = ML_DIR / "feature_dataset.csv"
BASELINE_SUSCEPTIBILITY = ML_DIR / "baseline_susceptibility.csv"
LANDSLIDE_RAINFALL = HISTORICAL_DIR / "landslide_rainfall_features.csv"
LANDSLIDE_SOIL_MOISTURE = HISTORICAL_DIR / "landslide_soil_moisture_features.csv"
GRID_SATELLITE = HISTORICAL_DIR / "grid_satellite_features.csv"
SATELLITE_MANIFEST = SATELLITE_DIR / "cache" / "satellite_cache_manifest.json"
OUTPUT_AUDIT_JSON = ML_DIR / "dynamic_risk_readiness_audit.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("audit_dynamic_risk_readiness")


def analyze_csv(filepath):
    """Safely loads a CSV and returns headers, total rows, and non-empty counts per column."""
    if not filepath.exists():
        return None, 0, {}
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        non_empty = {col: 0 for col in headers}
        total_rows = 0
        for row in reader:
            total_rows += 1
            for col in headers:
                val = row[col].strip() if row[col] is not None else ""
                if val != "" and val.lower() not in ("nan", "null", "none"):
                    non_empty[col] += 1
    return headers, total_rows, non_empty


def audit_dynamic_readiness():
    log.info("=" * 80)
    log.info("NER Safe — STEP 9B: DYNAMIC DATA READINESS AUDIT")
    log.info("Pilot Districts: Kohima (Nagaland) & Aizawl (Mizoram)")
    log.info("=" * 80)

    # 1. Inspect feature_dataset.csv
    feat_headers, feat_rows, feat_counts = analyze_csv(FEATURE_DATASET)
    log.info(f"Target Feature Dataset: {FEATURE_DATASET.name}")
    if feat_headers is None:
        log.error(f"Missing feature dataset at {FEATURE_DATASET}")
        sys.exit(1)
    log.info(f"  • Total rows: {feat_rows:,} (Expected: 16,961)")
    log.info(f"  • Total columns: {len(feat_headers)}")

    # 2. Inspect baseline_susceptibility.csv (Step 9A)
    base_headers, base_rows, base_counts = analyze_csv(BASELINE_SUSCEPTIBILITY)
    log.info(f"Baseline Susceptibility: {BASELINE_SUSCEPTIBILITY.name}")
    if base_headers is not None:
        log.info(f"  • Total rows: {base_rows:,} (Expected: 16,961)")
        log.info(f"  • Valid TSI scores: {base_counts.get('terrain_susceptibility_score', 0):,}")
    else:
        log.warning("  • Baseline susceptibility file not found.")

    # 3. Inspect satellite cache manifest
    sat_manifest_data = {}
    if SATELLITE_MANIFEST.exists():
        try:
            with open(SATELLITE_MANIFEST, "r", encoding="utf-8") as f:
                sat_manifest_data = json.load(f)
            log.info(f"Satellite Cache Manifest: Found (Status: {sat_manifest_data.get('metadata', {}).get('status', 'UNKNOWN')})")
        except Exception as e:
            log.warning(f"Error reading satellite cache manifest: {e}")

    # ── Feature Audit Specification ──────────────────────────────────────────
    # Categories to audit:
    # 1. Rainfall
    # 2. Soil Moisture
    # 3. Satellite Change
    # 4. Terrain
    # 5. Flood
    # 6. Human Verification
    # 7. Exposure / Impact

    audit_definitions = {
        "1. RAINFALL": {
            "source_instrument": "NASA GPM IMERG V07B (GPM_3IMERGHH)",
            "native_resolution": "0.1° × 0.1° (~10 km × 10 km)",
            "update_frequency": "30-minute observations, ~4h latency (Early Run)",
            "temporal_nature": "DYNAMIC",
            "features": [
                {
                    "name": "rainfall_rate",
                    "unit": "mm/h",
                    "description": "Instantaneous precipitation rate at observation window",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_rate",
                },
                {
                    "name": "rainfall_30min",
                    "unit": "mm",
                    "description": "Half-hourly calibrated precipitation accumulation",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_30min",
                },
                {
                    "name": "rainfall_3h",
                    "unit": "mm",
                    "description": "3-hour rolling cumulative precipitation burst",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_3h",
                },
                {
                    "name": "rainfall_6h",
                    "unit": "mm",
                    "description": "6-hour rolling cumulative storm accumulation",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_6h",
                },
                {
                    "name": "rainfall_24h",
                    "unit": "mm",
                    "description": "24-hour total daily precipitation (standard IMD threshold)",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_24h",
                },
                {
                    "name": "rainfall_72h",
                    "unit": "mm",
                    "description": "72-hour antecedent storm accumulation",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_72h",
                },
                {
                    "name": "rainfall_duration_h",
                    "unit": "hours",
                    "description": "Continuous precipitation duration with rate > 1.0 mm/h",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "rainfall_duration_h",
                },
                {
                    "name": "antecedent_rainfall_7d",
                    "unit": "mm",
                    "description": "7-day cumulative antecedent precipitation driving soil pore pressure",
                    "expected_status_flag": "rainfall_status",
                    "dataset_col": "antecedent_rainfall_7d",
                },
            ],
            "metadata_fields": {
                "source": "NASA GPM IMERG V07B (GPM_3IMERGHH)",
                "observation_timestamp": "UNAVAILABLE (Requires NASA Earthdata auth & live GPM feed)",
                "status": "UNAVAILABLE_EARTHDATA_AUTH_REQUIRED",
            },
        },
        "2. SOIL MOISTURE": {
            "source_instrument": "NASA SMAP Enhanced L3 Radiometer (SPL3SMP_E V006)",
            "native_resolution": "9 km × 9 km (EASE-Grid 2.0 Global Cylindrical)",
            "update_frequency": "Daily composite (~06:00 local descending AM pass preferred)",
            "temporal_nature": "DYNAMIC",
            "features": [
                {
                    "name": "soil_moisture_current",
                    "unit": "m³/m³",
                    "description": "Current volumetric soil moisture in top 5 cm soil layer",
                    "expected_status_flag": "soil_moisture_status",
                    "dataset_col": "soil_moisture_current",
                },
                {
                    "name": "soil_moisture_previous",
                    "unit": "m³/m³",
                    "description": "Prior day volumetric soil moisture (24-48h antecedent)",
                    "expected_status_flag": "soil_moisture_status",
                    "dataset_col": "soil_moisture_previous",
                },
                {
                    "name": "soil_moisture_change",
                    "unit": "m³/m³",
                    "description": "Absolute moisture change: SM_t - SM_{t-1}",
                    "expected_status_flag": "soil_moisture_status",
                    "dataset_col": "soil_moisture_change",
                },
                {
                    "name": "soil_moisture_change_percent",
                    "unit": "%",
                    "description": "Relative percentage moisture increase towards saturation",
                    "expected_status_flag": "soil_moisture_status",
                    "dataset_col": "soil_moisture_change_percent",
                },
            ],
            "metadata_fields": {
                "source": "NASA SMAP Enhanced L3 Radiometer (SPL3SMP_E V006)",
                "observation_timestamp": "UNAVAILABLE (Requires NASA Earthdata auth & live SMAP feed)",
                "status": "UNAVAILABLE_EARTHDATA_AUTH_REQUIRED",
            },
        },
        "3. SATELLITE CHANGE": {
            "source_instrument": "Copernicus Sentinel-1 C-SAR IW GRD (ESA / ASF DAAC)",
            "native_resolution": "20 m × 22 m (~10 m pixel spacing)",
            "update_frequency": "12-day orbital repeat cycle (NOT continuous live streaming)",
            "temporal_nature": "DYNAMIC",
            "features": [
                {
                    "name": "vv_change_db",
                    "unit": "dB",
                    "description": "Zonal mean co-polarization (VV) backscatter change between repeat passes",
                    "expected_status_flag": "satellite_status",
                    "dataset_col": "vv_change_db",
                },
                {
                    "name": "vh_change_db",
                    "unit": "dB",
                    "description": "Zonal mean cross-polarization (VH) backscatter change (vegetation disturbance proxy)",
                    "expected_status_flag": "satellite_status",
                    "dataset_col": "vh_change_db",
                },
                {
                    "name": "vv_vh_change",
                    "unit": "dB",
                    "description": "Euclidean magnitude of dual-polarization change: sqrt(ΔVV² + ΔVH²)",
                    "expected_status_flag": "satellite_status",
                    "dataset_col": "vv_vh_change",
                },
                {
                    "name": "change_confidence",
                    "unit": "0.0 - 1.0",
                    "description": "Normalized surface disturbance confidence score",
                    "expected_status_flag": "satellite_status",
                    "dataset_col": "change_confidence",
                },
            ],
            "metadata_fields": {
                "source": "Copernicus Sentinel-1 (C-SAR IW GRD)",
                "acquisition_date": "UNAVAILABLE (0 processed real scenes in cache)",
                "status": "PENDING_REAL_SCENE_INGESTION",
            },
        },
        "4. TERRAIN": {
            "source_instrument": "Copernicus DEM GLO-30 (ESA, 30m resolution)",
            "native_resolution": "30 m × 30 m (1.0 arc-sec)",
            "update_frequency": "Time-invariant static baseline",
            "temporal_nature": "STATIC",
            "features": [
                {
                    "name": "elevation",
                    "unit": "meters",
                    "description": "Mean, min, and max elevation above sea level across 500m cell",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "elevation_mean",
                    "extra_cols": ["elevation_min", "elevation_max"],
                },
                {
                    "name": "slope",
                    "unit": "degrees",
                    "description": "Mean and max slope inclination angle within 500m cell",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "slope_mean",
                    "extra_cols": ["slope_max"],
                },
                {
                    "name": "aspect",
                    "unit": "degrees (0-360)",
                    "description": "Circular mean aspect / slope azimuth within cell",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "aspect_mean",
                },
                {
                    "name": "curvature",
                    "unit": "100 * m⁻¹",
                    "description": "Surface profile / planform curvature (concave negative, convex positive)",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "curvature_mean",
                },
                {
                    "name": "TWI",
                    "unit": "dimensionless",
                    "description": "Topographic Wetness Index: ln(a / tan β) hydrological convergence",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "twi_mean",
                },
                {
                    "name": "terrain susceptibility baseline",
                    "unit": "Score (0-100), Class, PU Similarity",
                    "description": "STEP 9A multi-criteria Terrain Susceptibility Index (TSI) & PU similarity",
                    "expected_status_flag": "terrain_status",
                    "dataset_col": "terrain_susceptibility_score",
                    "source_file": "baseline_susceptibility.csv",
                },
            ],
            "metadata_fields": {
                "source": "Copernicus DEM GLO-30 / Step 9A Baseline",
                "observation_timestamp": "STATIC_BASELINE",
                "status": "AVAILABLE",
            },
        },
        "5. FLOOD": {
            "source_instrument": "Surface Water & Inundation Model / Sentinel-2 / Drainage Basins",
            "native_resolution": "Catchment / stream buffer polygon",
            "update_frequency": "Event-driven dynamic / seasonal",
            "temporal_nature": "DYNAMIC",
            "features": [
                {
                    "name": "flood_indicator",
                    "unit": "0.0 - 1.0",
                    "description": "Lowland / valley drainage flood inundation susceptibility flag",
                    "expected_status_flag": "flood_status",
                    "dataset_col": "flood_indicator",
                }
            ],
            "metadata_fields": {
                "source": "Surface Water & Inundation Model",
                "observation_timestamp": "UNAVAILABLE",
                "status": "UNAVAILABLE_PENDING_INGESTION",
            },
        },
        "6. HUMAN VERIFICATION": {
            "source_instrument": "Mobile Field App (Crowdsourced Citizen + Verified Disaster Officer)",
            "native_resolution": "GPS point matched to 500m grid cell",
            "update_frequency": "Asynchronous event-driven updates",
            "temporal_nature": "DYNAMIC",
            "features": [
                {
                    "name": "citizen_report_count",
                    "unit": "integer count",
                    "description": "Number of mobile crowdsourced citizen hazard reports logged for cell",
                    "expected_status_flag": "verification_status",
                    "dataset_col": "citizen_report_count",
                },
                {
                    "name": "verification_timestamp",
                    "unit": "ISO 8601 UTC",
                    "description": "Timestamp of physical on-site or remote verification by disaster officer",
                    "expected_status_flag": "verification_status",
                    "dataset_col": "verification_timestamp",
                },
                {
                    "name": "verification_confidence",
                    "unit": "0.0 - 1.0",
                    "description": "Expert rating of field ground inspection credibility",
                    "expected_status_flag": "verification_status",
                    "dataset_col": "verification_confidence",
                },
                {
                    "name": "officer_verification_status",
                    "unit": "Categorical",
                    "description": "Official inspection verdict: VERIFIED / REJECTED / UNVERIFIED",
                    "expected_status_flag": "verification_status",
                    "dataset_col": "officer_verification_status",
                },
            ],
            "metadata_fields": {
                "source": "Mobile Crowdsource & Disaster Officer App",
                "observation_timestamp": "UNVERIFIED (Default baseline state)",
                "status": "PARTIALLY_AVAILABLE (officer_verification_status initialized to UNVERIFIED; dynamic reports pending)",
            },
        },
        "7. EXPOSURE / IMPACT": {
            "source_instrument": "OpenStreetMap / State PWD GIS / Census / WorldPop",
            "native_resolution": "Vector lines, point features, and census polygons",
            "update_frequency": "Semi-static / annual updates",
            "temporal_nature": "STATIC",
            "features": [
                {
                    "name": "road proximity",
                    "unit": "meters",
                    "description": "Distance from cell centroid to nearest highway (NH-29, NH-54, state arterial)",
                    "expected_status_flag": "exposure_status",
                    "dataset_col": "road_proximity_m",
                },
                {
                    "name": "roads",
                    "unit": "Categorical hierarchy",
                    "description": "Road exposure category: HIGHWAY_NH29 / ARTERIAL / RURAL / NONE",
                    "expected_status_flag": "exposure_status",
                    "dataset_col": "road_exposure_level",
                },
                {
                    "name": "villages",
                    "unit": "Settlement count / name",
                    "description": "Vulnerable village settlements and urban wards intersecting cell",
                    "expected_status_flag": "exposure_status",
                    "dataset_col": "villages",  # to be checked if column exists
                },
                {
                    "name": "population",
                    "unit": "persons / km²",
                    "description": "Estimated local human population density within cell",
                    "expected_status_flag": "exposure_status",
                    "dataset_col": "population_density_est",
                },
                {
                    "name": "critical infrastructure",
                    "unit": "integer count",
                    "description": "Count of hospitals, bridges, telecom towers, power substations",
                    "expected_status_flag": "exposure_status",
                    "dataset_col": "critical_infrastructure_count",
                },
            ],
            "metadata_fields": {
                "source": "Highway GIS / OpenStreetMap / WorldPop / Census",
                "observation_timestamp": "STATIC_PENDING_INGESTION",
                "status": "UNAVAILABLE_PENDING_INGESTION",
            },
        },
    }

    # ── Execute Audit Evaluation ─────────────────────────────────────────────
    audit_report = {
        "metadata": {
            "audit_name": "STEP 9B Dynamic Risk Readiness Audit",
            "project": "NER Safe (SIH 2026)",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_dataset": FEATURE_DATASET.name,
            "total_cells": feat_rows,
            "districts": ["Kohima (Nagaland)", "Aizawl (Mizoram)"],
        },
        "categories": {},
        "overall_summary": {
            "total_features_audited": 0,
            "available_features": 0,
            "unavailable_features": 0,
            "static_features": 0,
            "dynamic_features": 0,
            "requires_external_auth": 0,
            "not_yet_implemented": 0,
        },
    }

    for cat_name, cat_data in audit_definitions.items():
        log.info("-" * 80)
        log.info(f"CATEGORY: {cat_name}")
        log.info(f"  • Source / Instrument: {cat_data['source_instrument']}")
        log.info(f"  • Native Resolution:   {cat_data['native_resolution']}")
        log.info(f"  • Update Frequency:    {cat_data['update_frequency']}")
        log.info(f"  • Temporal Nature:     {cat_data['temporal_nature']}")

        cat_summary = {
            "source_instrument": cat_data["source_instrument"],
            "native_resolution": cat_data["native_resolution"],
            "update_frequency": cat_data["update_frequency"],
            "temporal_nature": cat_data["temporal_nature"],
            "metadata_fields": cat_data["metadata_fields"],
            "features": [],
        }

        for feat in cat_data["features"]:
            audit_report["overall_summary"]["total_features_audited"] += 1
            if cat_data["temporal_nature"] == "STATIC":
                audit_report["overall_summary"]["static_features"] += 1
            else:
                audit_report["overall_summary"]["dynamic_features"] += 1

            col_name = feat["dataset_col"]
            source_file = feat.get("source_file", "feature_dataset.csv")

            # Check existence and population
            field_exists = False
            populated_count = 0
            populated_pct = 0.0

            if source_file == "feature_dataset.csv":
                if col_name in feat_counts:
                    field_exists = True
                    populated_count = feat_counts[col_name]
                    populated_pct = round((populated_count / feat_rows) * 100.0, 2)
            elif source_file == "baseline_susceptibility.csv":
                if base_counts and col_name in base_counts:
                    field_exists = True
                    populated_count = base_counts[col_name]
                    populated_pct = round((populated_count / base_rows) * 100.0, 2)

            # Determine classification status
            if not field_exists:
                status_classification = "NOT_YET_IMPLEMENTED"
                audit_report["overall_summary"]["not_yet_implemented"] += 1
                audit_report["overall_summary"]["unavailable_features"] += 1
            elif populated_count == 0:
                if "RAINFALL" in cat_name or "SOIL MOISTURE" in cat_name:
                    status_classification = "REQUIRES_EXTERNAL_AUTH"
                    audit_report["overall_summary"]["requires_external_auth"] += 1
                    audit_report["overall_summary"]["unavailable_features"] += 1
                elif "SATELLITE" in cat_name:
                    status_classification = "REQUIRES_EXTERNAL_AUTH"  # requires scene download
                    audit_report["overall_summary"]["requires_external_auth"] += 1
                    audit_report["overall_summary"]["unavailable_features"] += 1
                elif "EXPOSURE" in cat_name or "FLOOD" in cat_name:
                    status_classification = "UNAVAILABLE"
                    audit_report["overall_summary"]["unavailable_features"] += 1
                else:
                    status_classification = "UNAVAILABLE"
                    audit_report["overall_summary"]["unavailable_features"] += 1
            else:
                # Populated
                status_classification = "AVAILABLE"
                audit_report["overall_summary"]["available_features"] += 1

            feat_record = {
                "feature_name": feat["name"],
                "dataset_column": col_name,
                "source_file": source_file,
                "field_exists_in_schema": field_exists,
                "populated_count": populated_count,
                "populated_percent": populated_pct,
                "temporal_nature": cat_data["temporal_nature"],
                "status_classification": status_classification,
                "description": feat["description"],
                "unit": feat["unit"],
            }
            cat_summary["features"].append(feat_record)

            log.info(
                f"    - {feat['name']:<32} | Exists: {'YES' if field_exists else 'NO':<3} | "
                f"Populated: {populated_count:>6,}/{feat_rows:,} ({populated_pct:>5.1f}%) | "
                f"Status: {status_classification}"
            )

        audit_report["categories"][cat_name] = cat_summary

    # ── Write Audit JSON ─────────────────────────────────────────────────────
    with open(OUTPUT_AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2)

    log.info("=" * 80)
    log.info(f"✓ Dynamic Risk Readiness Audit exported to: {OUTPUT_AUDIT_JSON.name}")
    log.info("=" * 80)

    # ── Print Executive Summary ──────────────────────────────────────────────
    summ = audit_report["overall_summary"]
    log.info("EXECUTIVE AUDIT SUMMARY:")
    log.info(f"  • Total features audited:        {summ['total_features_audited']}")
    log.info(f"  • Static features:               {summ['static_features']}")
    log.info(f"  • Dynamic features:              {summ['dynamic_features']}")
    log.info(f"  • AVAILABLE (Populated):         {summ['available_features']}")
    log.info(f"  • UNAVAILABLE / Empty:           {summ['unavailable_features']}")
    log.info(f"  • Requires External Auth/Download: {summ['requires_external_auth']}")
    log.info(f"  • Not Yet Implemented in Schema: {summ['not_yet_implemented']}")
    log.info("=" * 80)

    return audit_report


if __name__ == "__main__":
    audit_dynamic_readiness()
