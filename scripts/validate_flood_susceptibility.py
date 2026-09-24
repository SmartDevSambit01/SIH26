#!/usr/bin/env python3
"""
validate_flood_susceptibility.py — Integrity Validator for Flood Susceptibility Dataset

Validates data/ml/grid_hydrology_features.csv and data/ml/flood_susceptibility.csv
against the scientific-integrity requirements from build_flood_susceptibility.py
and derive_hydrology.py, mirroring validate_baseline_susceptibility.py.

Checks performed:
  1. Expected row count: exactly 16,961 rows in both CSVs
  2. Required columns present in both CSVs
  3. Unique cell_id in both CSVs
  4. Valid district values: only 'Kohima' or 'Aizawl'
  5. Valid status values: only AVAILABLE or INSUFFICIENT_DATA
  6. ffsi_score range: 0.0-100.0 for AVAILABLE rows only
  7. Valid ffsi_class set for AVAILABLE rows
  8. INSUFFICIENT_DATA rows have empty score/class (no fabricated fallback)
  9. HAND values are non-negative (hand_min, hand_mean) where present
  10. drainage_density values within [0.0, 1.0] where present
  11. AVAILABLE/INSUFFICIENT_DATA row sets match between the two CSVs

Exit codes:
  0 = All checks PASSED
  1 = One or more checks FAILED
"""

import csv
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HYDROLOGY_CSV = PROJECT_ROOT / "data" / "ml" / "grid_hydrology_features.csv"
FLOOD_CSV = PROJECT_ROOT / "data" / "ml" / "flood_susceptibility.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("validate_flood_susceptibility")

EXPECTED_ROW_COUNT = 16_961
VALID_DISTRICTS = {"Kohima", "Aizawl"}
VALID_STATUS = {"AVAILABLE", "INSUFFICIENT_DATA"}
VALID_FFSI_CLASSES = {"VERY_LOW", "LOW", "MODERATE", "HIGH", "VERY_HIGH"}

HYDROLOGY_COLUMNS = ["cell_id", "district", "flow_accumulation_max", "drainage_density",
                     "distance_to_drainage_m", "hand_mean", "hand_min"]
FLOOD_COLUMNS = ["cell_id", "district", "ffsi_score", "ffsi_class", "primary_contributor", "status"]

failures = []


def check(condition: bool, message: str):
    if condition:
        log.info(f"  [PASS] {message}")
    else:
        log.error(f"  [FAIL] {message}")
        failures.append(message)


def load_csv(path: Path):
    if not path.exists():
        log.error(f"[FATAL] File not found: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    log.info("=" * 75)
    log.info("NER Safe — Flood Susceptibility Dataset Validation")
    log.info("=" * 75)

    hydro_rows = load_csv(HYDROLOGY_CSV)
    flood_rows = load_csv(FLOOD_CSV)

    log.info(f"\n--- Row Count & Schema ---")
    check(len(hydro_rows) == EXPECTED_ROW_COUNT, f"grid_hydrology_features.csv row count == {EXPECTED_ROW_COUNT} (got {len(hydro_rows)})")
    check(len(flood_rows) == EXPECTED_ROW_COUNT, f"flood_susceptibility.csv row count == {EXPECTED_ROW_COUNT} (got {len(flood_rows)})")
    check(set(hydro_rows[0].keys()) == set(HYDROLOGY_COLUMNS), "grid_hydrology_features.csv has expected columns")
    check(set(flood_rows[0].keys()) == set(FLOOD_COLUMNS), "flood_susceptibility.csv has expected columns")

    log.info(f"\n--- Uniqueness & District Validity ---")
    hydro_ids = [r["cell_id"] for r in hydro_rows]
    flood_ids = [r["cell_id"] for r in flood_rows]
    check(len(hydro_ids) == len(set(hydro_ids)), "grid_hydrology_features.csv cell_id is unique")
    check(len(flood_ids) == len(set(flood_ids)), "flood_susceptibility.csv cell_id is unique")
    check(all(r["district"] in VALID_DISTRICTS for r in hydro_rows), "All hydrology rows have valid district")
    check(all(r["district"] in VALID_DISTRICTS for r in flood_rows), "All flood rows have valid district")

    log.info(f"\n--- Status & Score Integrity (no fabrication) ---")
    check(all(r["status"] in VALID_STATUS for r in flood_rows), "All status values are AVAILABLE or INSUFFICIENT_DATA")

    available = [r for r in flood_rows if r["status"] == "AVAILABLE"]
    insufficient = [r for r in flood_rows if r["status"] == "INSUFFICIENT_DATA"]
    check(len(available) + len(insufficient) == len(flood_rows), "AVAILABLE + INSUFFICIENT_DATA covers all rows")

    score_ok = True
    for r in available:
        try:
            s = float(r["ffsi_score"])
            if not (0.0 <= s <= 100.0):
                score_ok = False
                break
        except (ValueError, TypeError):
            score_ok = False
            break
    check(score_ok, "ffsi_score in [0.0, 100.0] for every AVAILABLE row")
    check(all(r["ffsi_class"] in VALID_FFSI_CLASSES for r in available), "ffsi_class is a valid class for every AVAILABLE row")
    check(all(r["ffsi_score"] == "" and r["ffsi_class"] == "" for r in insufficient),
          "INSUFFICIENT_DATA rows have empty score/class (no fabricated fallback value)")

    log.info(f"\n--- Physical Plausibility ---")
    hand_ok = True
    dd_ok = True
    for r in hydro_rows:
        for col in ("hand_min", "hand_mean"):
            if r[col] != "" and float(r[col]) < 0:
                hand_ok = False
        if r["drainage_density"] != "" and not (0.0 <= float(r["drainage_density"]) <= 1.0):
            dd_ok = False
    check(hand_ok, "HAND (hand_min, hand_mean) is non-negative everywhere it is populated")
    check(dd_ok, "drainage_density is within [0.0, 1.0] everywhere it is populated")

    log.info(f"\n--- Cross-File Consistency ---")
    hydro_missing = {r["cell_id"] for r in hydro_rows if r["hand_mean"] == ""}
    flood_missing = {r["cell_id"] for r in flood_rows if r["status"] == "INSUFFICIENT_DATA"}
    # flood_missing may be a superset (it also requires slope/twi from the terrain CSV)
    check(hydro_missing.issubset(flood_missing),
          "Every cell missing hydrology data is marked INSUFFICIENT_DATA in flood_susceptibility.csv")

    log.info("\n" + "=" * 75)
    if failures:
        log.error(f"VALIDATION FAILED — {len(failures)} check(s) failed:")
        for f in failures:
            log.error(f"  - {f}")
        sys.exit(1)
    else:
        log.info("ALL CHECKS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
