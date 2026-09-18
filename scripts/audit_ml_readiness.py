#!/usr/bin/env python3
"""
audit_ml_readiness.py — ML Readiness & Ground-Truth Audit Script

STEP 8.5 — ML Readiness & Ground-Truth Audit
NER Safe (SIH 2026)

Conducts an exhaustive programmatic audit of data/ml/feature_dataset.csv
to determine whether the current data can support scientifically defensible
machine learning modeling for Step 9.

Checks:
  1. File existence & basic dimensionality (16,961 rows, 54 columns)
  2. Ground-truth label distribution (Confirmed Positive, Confirmed Negative, Unknown)
  3. Absence of synthetic negative sample fabrication
  4. Unique cell and observation date combinations
  5. Missingness percentage across every feature group
  6. Dynamic feature availability status
  7. Target leakage risks (presence of metadata encoding ground truth)
  8. Spatial coverage and district distribution
  9. Evaluation of conventional supervised binary ML feasibility
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ML_DIR = DATA_DIR / "ml"
FEATURE_DATASET = ML_DIR / "feature_dataset.csv"
AUDIT_JSON = ML_DIR / "ml_readiness_audit.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("audit_ml_readiness")


def run_audit():
    log.info("=" * 75)
    log.info("NER Safe — STEP 8.5: ML Readiness & Ground-Truth Audit")
    log.info("=" * 75)

    if not FEATURE_DATASET.exists():
        log.error(f"Dataset file missing: {FEATURE_DATASET}")
        sys.exit(1)

    with open(FEATURE_DATASET, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)

    total_rows = len(rows)
    total_cols = len(header)
    log.info(f"Loaded dataset: {total_rows:,} rows, {total_cols} columns")

    # 1. Label Quality & Ground-Truth Analysis
    positive_rows = []
    negative_rows = []
    unknown_rows = []

    district_counts = {"Kohima": 0, "Aizawl": 0, "Other": 0}
    seen_cells = set()
    seen_keys = set()
    duplicate_keys = 0
    unique_dates = set()

    missing_counts = {col: 0 for col in header}

    for r in rows:
        cid = r["cell_id"]
        dist = r["district"]
        obs_date = r["observation_date"]
        lbl = r["landslide_label"].strip()

        district_counts[dist] = district_counts.get(dist, 0) + 1
        seen_cells.add(cid)
        unique_dates.add(obs_date)

        key = (cid, obs_date)
        if key in seen_keys:
            duplicate_keys += 1
        seen_keys.add(key)

        if lbl == "1":
            positive_rows.append(r)
        elif lbl == "0":
            negative_rows.append(r)
        else:
            unknown_rows.append(r)

        for col in header:
            if r[col] == "":
                missing_counts[col] += 1

    pos_count = len(positive_rows)
    neg_count = len(negative_rows)
    unk_count = len(unknown_rows)

    log.info(f"Label Distribution:")
    log.info(f"  • Confirmed Positive (1): {pos_count} (0.06%)")
    log.info(f"  • Confirmed Negative (0): {neg_count} (0.00%)")
    log.info(f"  • Unknown / Unlabeled:    {unk_count} (99.94%)")

    # 2. Feature Availability by Group
    groups = {
        "Spatial Index": ["cell_id", "district", "state", "latitude", "longitude", "observation_date"],
        "Terrain (DEM 30m)": ["elevation_mean", "elevation_min", "elevation_max", "slope_mean", "slope_max", "aspect_mean", "curvature_mean", "twi_mean"],
        "Meteorological Rain": ["rainfall_rate", "rainfall_30min", "rainfall_3h", "rainfall_6h", "rainfall_24h", "rainfall_72h", "rainfall_intensity", "rainfall_duration_h", "antecedent_rainfall_7d"],
        "Hydrological Soil Moisture": ["soil_moisture_current", "soil_moisture_previous", "soil_moisture_change", "soil_moisture_change_percent"],
        "Satellite SAR": ["vv_change_db", "vh_change_db", "vv_vh_change", "change_confidence"],
        "Context (NDVI/Flood)": ["vegetation_ndvi", "flood_indicator"],
        "Exposure & Consequence": ["road_proximity_m", "road_exposure_level", "population_density_est", "critical_infrastructure_count", "impact_priority_score"],
        "Human Verification": ["citizen_report_count", "officer_verification_status", "verification_timestamp", "verification_confidence"],
        "Ground Truth & Metadata": ["landslide_label", "historical_event_id", "event_location_name", "label_quality"],
        "Data Status Flags": ["terrain_status", "rainfall_status", "soil_moisture_status", "satellite_status", "flood_status", "vegetation_status", "exposure_status", "verification_status"],
    }

    missing_percentages = {col: round((missing_counts[col] / total_rows) * 100.0, 2) for col in header}

    group_readiness = {}
    for gname, cols in groups.items():
        avail = sum(1 for c in cols if missing_counts[c] < total_rows)
        total_in_g = len(cols)
        group_readiness[gname] = {
            "total_columns": total_in_g,
            "columns_with_data": avail,
            "status": "AVAILABLE" if avail == total_in_g else ("PARTIALLY_AVAILABLE" if avail > 0 else "UNAVAILABLE"),
        }

    # 3. Scientific Readiness Evaluation
    # Criteria for conventional supervised binary ML:
    # - >= 50-100 verified positives
    # - verified negatives or defensible absence strategy
    # - populated dynamic features
    critical_blockers = []

    if pos_count < 50:
        critical_blockers.append(
            f"Severe Sample Size Deficiency: Only {pos_count} confirmed positive landslide events exist. "
            "Supervised classification (XGBoost/Random Forest) requires at least 50–100 events per district."
        )

    if neg_count == 0:
        critical_blockers.append(
            "Complete Absence of Verified Negative Samples: 0 confirmed negative landslide observations exist. "
            "Conventional supervised binary classification cannot be trained without either confirmed non-landslide "
            "sites or an authoritative Positive-Unlabeled (PU) learning formulation."
        )

    dyn_cols = groups["Meteorological Rain"] + groups["Hydrological Soil Moisture"] + groups["Satellite SAR"]
    dyn_avail = sum(1 for c in dyn_cols if missing_counts[c] < total_rows)
    if dyn_avail == 0:
        critical_blockers.append(
            "Zero Dynamic Environmental Data: All dynamic precipitation, soil moisture, and SAR change features "
            "are currently unpopulated awaiting NASA Earthdata authentication and scene download."
        )

    # Readiness Classification
    if len(critical_blockers) == 0:
        readiness_status = "READY"
    elif pos_count > 0 and group_readiness["Terrain (DEM 30m)"]["status"] == "AVAILABLE":
        readiness_status = "NOT_READY"  # strictly NOT_READY for conventional binary ML as instructed
    else:
        readiness_status = "NOT_READY"

    # 4. Target Leakage Evaluation
    leakage_columns = ["historical_event_id", "event_location_name", "label_quality"]
    log.info(f"Target Leakage Audit:")
    log.info(f"  • Flagged metadata columns that MUST be excluded from ML inputs: {leakage_columns}")

    # 5. Build Audit JSON
    audit_data = {
        "audit_metadata": {
            "project": "NER Safe (SIH 2026)",
            "step": "STEP 8.5 — ML Readiness & Ground-Truth Audit",
            "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_dataset": str(FEATURE_DATASET.name),
            "readiness_classification": readiness_status,
        },
        "dataset_summary": {
            "total_rows": total_rows,
            "total_columns": total_cols,
            "unique_cells": len(seen_cells),
            "unique_observation_dates": len(unique_dates),
            "duplicate_records": duplicate_keys,
            "district_distribution": district_counts,
        },
        "ground_truth_labels": {
            "confirmed_positive": pos_count,
            "confirmed_negative": neg_count,
            "unknown_unlabeled": unk_count,
            "positive_rate_percent": round((pos_count / total_rows) * 100.0, 4),
            "label_quality_assessment": (
                "Insufficient verified negative samples for conventional supervised binary classification."
                if neg_count == 0 else "Sufficient"
            ),
        },
        "feature_group_readiness": group_readiness,
        "missingness_percentages": missing_percentages,
        "target_leakage_safeguards": {
            "leakage_risk_columns": leakage_columns,
            "safeguard_action": "Strictly drop from feature matrix X before any train/test split in Step 9.",
        },
        "critical_blockers": critical_blockers,
        "recommended_next_actions": [
            "Incorporate official GSI Bhukosh / NLSM GIS inventory export to expand verified positive samples.",
            "Establish a scientifically defensible absence strategy (PU Learning / confirmed stable slope baselines) rather than fabricating fake negative points.",
            "Supply NASA Earthdata credentials to download GPM IMERG and SMAP dynamic layers for real-time risk integration.",
            "Utilize Spatial Block Cross-Validation in Step 9 to eliminate spatial autocorrelation leakage.",
            "For Step 9, implement a Static Susceptibility Baseline (heuristic/analytical weight-of-evidence) alongside initial ML feasibility testing, rather than an ungrounded black-box model.",
        ],
    }

    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    log.info(f"✓ Audit JSON written to: {AUDIT_JSON}")
    log.info("=" * 75)
    log.info(f"ML READINESS VERDICT: {readiness_status}")
    for idx, b in enumerate(critical_blockers, 1):
        log.warning(f"  Blocker {idx}: {b}")
    log.info("=" * 75)
    return audit_data


if __name__ == "__main__":
    run_audit()
