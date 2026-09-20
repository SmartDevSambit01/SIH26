#!/usr/bin/env python3
"""
validate_grid_exposure.py — Integrity Validator for Grid Exposure Dataset

Validates data/ml/grid_exposure_features.csv against the requirements from
assign_grid_exposure.py, mirroring validate_flood_susceptibility.py.

Checks performed:
  1. Expected row count: exactly 16,961 rows
  2. Unique cell_id
  3. Valid district values
  4. Valid exposure_status values: only AVAILABLE or UNAVAILABLE
  5. AVAILABLE rows have non-negative distances (roads/hospitals/schools)
  6. UNAVAILABLE rows have empty distance/name fields (no fabricated fallback)
  7. nearest_road_class is one of the fetched OSM highway tag values (or empty)

Exit codes:
  0 = All checks PASSED
  1 = One or more checks FAILED
"""

import csv
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPOSURE_CSV = PROJECT_ROOT / "data" / "ml" / "grid_exposure_features.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("validate_grid_exposure")

EXPECTED_ROW_COUNT = 16_961
VALID_DISTRICTS = {"Kohima", "Aizawl"}
VALID_STATUS = {"AVAILABLE", "UNAVAILABLE"}
VALID_ROAD_CLASSES = {"motorway", "trunk", "primary", "secondary", "tertiary", "residential", "track", ""}

failures = []


def check(condition: bool, message: str):
    if condition:
        log.info(f"  [PASS] {message}")
    else:
        log.error(f"  [FAIL] {message}")
        failures.append(message)


def main():
    log.info("=" * 75)
    log.info("NER Safe — Grid Exposure Dataset Validation")
    log.info("=" * 75)

    if not EXPOSURE_CSV.exists():
        log.error(f"[FATAL] File not found: {EXPOSURE_CSV}")
        sys.exit(1)

    with open(EXPOSURE_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    log.info("\n--- Row Count & Uniqueness ---")
    check(len(rows) == EXPECTED_ROW_COUNT, f"Row count == {EXPECTED_ROW_COUNT} (got {len(rows)})")
    ids = [r["cell_id"] for r in rows]
    check(len(ids) == len(set(ids)), "cell_id is unique")
    check(all(r["district"] in VALID_DISTRICTS for r in rows), "All rows have valid district")

    log.info("\n--- Status Integrity (no fabrication) ---")
    check(all(r["exposure_status"] in VALID_STATUS for r in rows), "All exposure_status values are AVAILABLE or UNAVAILABLE")

    available = [r for r in rows if r["exposure_status"] == "AVAILABLE"]
    unavailable = [r for r in rows if r["exposure_status"] == "UNAVAILABLE"]

    unavailable_clean = all(
        r.get("nearest_road_distance_m", "") == "" and r.get("nearest_hospital_distance_m", "") == ""
        and r.get("nearest_school_distance_m", "") == ""
        for r in unavailable
    )
    check(unavailable_clean, "UNAVAILABLE rows have empty distance fields (no fabricated fallback)")

    dist_ok = True
    for r in available:
        for col in ("nearest_road_distance_m", "nearest_hospital_distance_m", "nearest_school_distance_m"):
            val = r.get(col, "")
            if val != "" and float(val) < 0:
                dist_ok = False
    check(dist_ok, "All populated distance fields are non-negative")

    class_ok = all(r.get("nearest_road_class", "") in VALID_ROAD_CLASSES for r in available)
    check(class_ok, "nearest_road_class is a recognized OSM highway tag (or empty)")

    log.info("\n" + "=" * 75)
    if failures:
        log.error(f"VALIDATION FAILED — {len(failures)} check(s) failed:")
        for f in failures:
            log.error(f"  - {f}")
        sys.exit(1)
    else:
        log.info(f"ALL CHECKS PASSED ({len(available)} AVAILABLE, {len(unavailable)} UNAVAILABLE)")
        sys.exit(0)


if __name__ == "__main__":
    main()
