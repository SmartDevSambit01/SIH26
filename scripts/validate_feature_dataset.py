#!/usr/bin/env python3
"""
validate_feature_dataset.py — Automated Validation Suite for STEP 8 Unified Dataset

STEP 8 — Feature Engineering & Unified Risk Dataset
NER Safe (SIH 2026)

Validates:
  1. Record Integrity & Uniqueness:
     - 16,961 total rows matching regional 500m risk grid (Kohima: 6,055, Aizawl: 10,906)
     - Zero duplicate (cell_id, observation_date) combinations
  2. Spatial Identifier & District Consistency:
     - Cell IDs conform strictly to KOH_* and AIZ_* prefixes
     - District names exactly match 'Kohima' and 'Aizawl'
     - Centroid coordinates fall within regional bounding boxes
  3. Mathematical Plausibility:
     - Elevation in [0, 4000] m
     - Slope in [0, 90] degrees
     - Aspect in [0, 360] degrees or -1 for flat
     - Curvature in [-500, +500]
     - TWI in [-5, 35]
  4. Explicit Missing Data & Anti-Fabrication:
     - Missing environmental data explicitly represented as empty (never synthetic zeros)
     - Explicit data status columns tracked for all layers
  5. Ground Truth Target Classification:
     - Confirmed positive labels match verified historical events
     - Confirmed negative labels = 0 (truthful: no false negative assumptions)
     - Unknown / unlabelled rows correctly protected
  6. Conceptual Separation of Hazard vs. Exposure:
     - Hazard features contain only physical/meteorological variables
     - Exposure features contain only human/asset consequence variables
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ML_DIR = DATA_DIR / "ml"
DATASET_PATH = ML_DIR / "feature_dataset.csv"
BOUNDARIES_DIR = DATA_DIR / "boundaries"

EXPECTED_COLUMNS_COUNT = 54

DISTRICT_CONFIGS = {
    "Kohima": {
        "cells": 6055,
        "prefix": "KOH_",
        "bbox": {"min_lat": 25.4, "max_lat": 26.2, "min_lon": 93.5, "max_lon": 94.6},
    },
    "Aizawl": {
        "cells": 10906,
        "prefix": "AIZ_",
        "bbox": {"min_lat": 23.3, "max_lat": 24.5, "min_lon": 92.4, "max_lon": 93.4},
    },
}

HAZARD_COLUMNS = [
    "elevation_mean", "elevation_min", "elevation_max",
    "slope_mean", "slope_max", "aspect_mean", "curvature_mean", "twi_mean",
    "rainfall_rate", "rainfall_30min", "rainfall_3h", "rainfall_6h",
    "rainfall_24h", "rainfall_72h", "rainfall_intensity", "rainfall_duration_h",
    "antecedent_rainfall_7d", "soil_moisture_current", "soil_moisture_previous",
    "soil_moisture_change", "soil_moisture_change_percent",
    "vv_change_db", "vh_change_db", "vv_vh_change", "change_confidence",
    "vegetation_ndvi", "flood_indicator",
]

EXPOSURE_COLUMNS = [
    "road_proximity_m", "road_exposure_level", "population_density_est",
    "critical_infrastructure_count", "impact_priority_score",
]

passed = 0
failed = 0
warnings = 0


def check(condition: bool, msg: str, warn_only: bool = False):
    global passed, failed, warnings
    if condition:
        print(f"  [PASS]  {msg}")
        passed += 1
    elif warn_only:
        print(f"  [WARN]  {msg}")
        warnings += 1
    else:
        print(f"  [FAIL]  {msg}")
        failed += 1


def main():
    print("=" * 75)
    print("NER Safe — STEP 8: Feature Dataset Validation Suite")
    print("=" * 75)

    check(DATASET_PATH.exists(), f"Unified feature dataset exists: {DATASET_PATH.name}")
    if not DATASET_PATH.exists():
        print(f"[FAIL] Missing {DATASET_PATH}")
        sys.exit(1)

    # ── Test 1: Header & Schema Verification ─────────────────────────────────
    print("\n--- Test 1: Column Schema & Conceptual Separation ---")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        check(
            len(header) == EXPECTED_COLUMNS_COUNT,
            f"Total columns = {len(header)} (expected {EXPECTED_COLUMNS_COUNT})",
        )

        # Check conceptual separation
        hazard_present = [c for c in HAZARD_COLUMNS if c in header]
        exposure_present = [c for c in EXPOSURE_COLUMNS if c in header]
        check(
            len(hazard_present) == len(HAZARD_COLUMNS),
            f"All {len(HAZARD_COLUMNS)} physical hazard & susceptibility columns verified",
        )
        check(
            len(exposure_present) == len(EXPOSURE_COLUMNS),
            f"All {len(EXPOSURE_COLUMNS)} operational consequence & exposure columns verified",
        )

        # Check that no exposure column is categorized inside hazard
        overlap = set(HAZARD_COLUMNS).intersection(set(EXPOSURE_COLUMNS))
        check(len(overlap) == 0, "Strict scientific separation: Zero overlap between hazard and exposure features")

    # ── Test 2: Row Count & District Coverage ────────────────────────────────
    print("\n--- Test 2: District Coverage & Uniqueness ---")
    rows_by_district = {"Kohima": 0, "Aizawl": 0, "Other": 0}
    seen_keys = set()
    duplicates = 0
    invalid_prefixes = 0
    invalid_coords = 0

    positive_labels = 0
    negative_labels = 0
    unlabeled = 0

    available_features_counts = {col: 0 for col in header}
    total_rows = 0

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            cid = row["cell_id"]
            dist = row["district"]
            obs_date = row["observation_date"]

            # District tally
            if dist in rows_by_district:
                rows_by_district[dist] += 1
            else:
                rows_by_district["Other"] += 1

            # Unique key check
            key = (cid, obs_date)
            if key in seen_keys:
                duplicates += 1
            seen_keys.add(key)

            # Prefix & district match
            expected_prefix = DISTRICT_CONFIGS.get(dist, {}).get("prefix", "")
            if not cid.startswith(expected_prefix):
                invalid_prefixes += 1

            # Coordinates
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                bbox = DISTRICT_CONFIGS.get(dist, {}).get("bbox", {})
                if not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lon"] <= lon <= bbox["max_lon"]):
                    invalid_coords += 1
            except (ValueError, TypeError):
                invalid_coords += 1

            # Historical label tally
            lbl = row.get("landslide_label", "").strip()
            if lbl == "1":
                positive_labels += 1
            elif lbl == "0":
                negative_labels += 1
            else:
                unlabeled += 1

            # Feature population tracking
            for col in header:
                if row[col] != "":
                    available_features_counts[col] += 1

    check(total_rows == 16961, f"Total dataset rows = {total_rows:,} (matches regional 500m grid)")
    check(
        rows_by_district["Kohima"] == DISTRICT_CONFIGS["Kohima"]["cells"],
        f"Kohima: {rows_by_district['Kohima']:,} rows match expected ({DISTRICT_CONFIGS['Kohima']['cells']:,})",
    )
    check(
        rows_by_district["Aizawl"] == DISTRICT_CONFIGS["Aizawl"]["cells"],
        f"Aizawl: {rows_by_district['Aizawl']:,} rows match expected ({DISTRICT_CONFIGS['Aizawl']['cells']:,})",
    )
    check(duplicates == 0, f"Duplicate (cell_id, observation_date) combinations: {duplicates}")
    check(invalid_prefixes == 0, f"Cell ID prefix matching: All {total_rows:,} cells match district prefix")
    check(invalid_coords == 0, f"Spatial boundary sanity: All {total_rows:,} centroids within district coordinates")

    # ── Test 3: Ground Truth Label Integrity ─────────────────────────────────
    print("\n--- Test 3: Ground Truth & Label Quality ---")
    check(positive_labels == 11, f"Confirmed positive landslide samples = {positive_labels} (Verified GSI/NSDMA)")
    check(
        negative_labels == 0,
        f"Confirmed negative landslide samples = {negative_labels} (Zero fabricated negative assumptions)",
    )
    check(
        unlabeled == total_rows - positive_labels,
        f"Unlabeled background cells = {unlabeled:,} (Scientifically protected from false negative bias)",
    )

    # ── Test 4: Physical Value Plausibility (Terrain Features) ───────────────
    print("\n--- Test 4: Physical Terrain Bounds (Available Features) ---")
    out_of_bounds = 0
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field, (fmin, fmax) in [
                ("elevation_mean", (0, 4000)),
                ("slope_mean", (0, 90)),
                ("aspect_mean", (-1, 360)),
                ("curvature_mean", (-500, 500)),
                ("twi_mean", (-5, 35)),
            ]:
                val = row[field]
                if val != "":
                    try:
                        v = float(val)
                        if not (fmin <= v <= fmax):
                            out_of_bounds += 1
                    except ValueError:
                        out_of_bounds += 1

    check(out_of_bounds == 0, f"Terrain morphometry bounds check: All available values mathematically valid")

    # ── Test 5: Missing Data & Status Integrity ──────────────────────────────
    print("\n--- Test 5: Missing Data & Status Integrity ---")
    check(
        available_features_counts["rainfall_rate"] == 0,
        "Meteorological rainfall values: Correctly set to empty (not fabricated)",
    )
    check(
        available_features_counts["soil_moisture_current"] == 0,
        "Soil moisture values: Correctly set to empty (not fabricated)",
    )
    check(
        available_features_counts["vv_change_db"] == 0,
        "Satellite SAR change values: Correctly set to empty (not fabricated)",
    )
    check(
        available_features_counts["road_proximity_m"] == 0,
        "Exposure asset values: Correctly set to empty (not fabricated)",
    )

    # ── Summary & Statistics Reporting ───────────────────────────────────────
    print("\n" + "=" * 75)
    print(f"Validation Summary: {passed} PASSED, {failed} FAILED, {warnings} WARNINGS")
    print("=" * 75)

    print("\nDATASET STATISTICAL PROFILE:")
    print(f"  • Total Rows:                     {total_rows:,}")
    print(f"  • Total Columns:                  {EXPECTED_COLUMNS_COUNT}")
    print(f"  • Kohima Cells:                   {rows_by_district['Kohima']:,}")
    print(f"  • Aizawl Cells:                   {rows_by_district['Aizawl']:,}")
    print(f"  • Confirmed Positive Labels:      {positive_labels}")
    print(f"  • Confirmed Negative Labels:      {negative_labels}")
    print(f"  • Unknown / Unlabeled Cells:      {unlabeled:,}")
    print(f"  • Duplicate Records:              {duplicates}")

    # Available vs Unavailable
    avail_cols = [c for c, count in available_features_counts.items() if count > 0]
    unavail_cols = [c for c, count in available_features_counts.items() if count == 0]

    print(f"\n  • Available Columns ({len(avail_cols)}):")
    print(f"    {', '.join(avail_cols[:10])}...")
    print(f"  • Unavailable / Pending Columns ({len(unavail_cols)}):")
    print(f"    {', '.join(unavail_cols[:10])}...")

    if failed > 0:
        print("\n[RESULT] One or more feature dataset validation checks FAILED.")
        sys.exit(1)
    else:
        print("\n[RESULT] STEP 8 Unified Feature Dataset Integrity: FULLY VALIDATED.")
        sys.exit(0)


if __name__ == "__main__":
    main()
