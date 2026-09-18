#!/usr/bin/env python3
"""
validate_baseline_susceptibility.py — Integrity Validator for Baseline Susceptibility Dataset

STEP 9A — NER Safe (SIH 2026)

Validates data/ml/baseline_susceptibility.csv against all scientific and
integrity requirements established during the STEP 9A baseline pipeline.

Checks performed:
  1.  Expected row count: exactly 16,961 rows
  2.  Required columns: all 16 schema columns present
  3.  Unique cell_id: no duplicate cell identifiers
  4.  Valid district names: only 'Kohima' or 'Aizawl'
  5.  Valid label_status values: only CONFIRMED_POSITIVE or UNKNOWN
  6.  Confirmed positive count: exactly 11
  7.  UNKNOWN count: exactly 16,950 (all remaining cells)
  8.  Zero fabricated negatives: no 'CONFIRMED_NEGATIVE' or 'NEGATIVE' labels
  9.  TSI score range: 0.0 to 100.0 (only for non-NODATA cells)
  10. Valid terrain susceptibility classes: {VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH, NODATA_BORDER}
  11. NODATA_BORDER cell handling: empty numeric fields allowed; TSI class must be NODATA_BORDER
  12. PU similarity values: 0.0-1.0 only for non-NODATA cells; empty for NODATA cells
  13. Valid PU similarity classes: {HIGH_TERRAIN_SIMILARITY, MODERATE_TERRAIN_SIMILARITY, LOW_TERRAIN_SIMILARITY, DISSIMILAR_TERRAIN, NODATA_BORDER}
  14. Coordinate ranges: latitude within [22.0, 27.0], longitude within [91.0, 96.0]
  15. Spatial block identifiers: non-empty, correctly prefixed BLK_KOH or BLK_AIZ per district
  16. Confirmed positive cells: each must have a non-empty historical_event_id
  17. UNKNOWN cells: must have empty historical_event_id
  18. No NaN/blank values in required string columns
  19. Terrain numeric fields populated for all non-NODATA cells

Exit codes:
  0 = All checks PASSED
  1 = One or more checks FAILED
"""

import csv
import logging
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = PROJECT_ROOT / "data" / "ml" / "baseline_susceptibility.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("validate_baseline_susceptibility")

# Expected Schema Constants
EXPECTED_ROW_COUNT = 16_961
EXPECTED_CONFIRMED_POSITIVES = 11
EXPECTED_UNKNOWN_COUNT = 16_950
EXPECTED_NODATA_COUNT = 2_895

REQUIRED_COLUMNS = [
    "cell_id",
    "district",
    "latitude",
    "longitude",
    "spatial_block_id",
    "slope_mean",
    "elevation_mean",
    "curvature_mean",
    "twi_mean",
    "terrain_susceptibility_score",
    "terrain_susceptibility_class",
    "pu_terrain_similarity",
    "pu_similarity_class",
    "primary_terrain_contributors",
    "label_status",
    "historical_event_id",
]

VALID_DISTRICTS = {"Kohima", "Aizawl"}
VALID_LABEL_STATUSES = {"CONFIRMED_POSITIVE", "UNKNOWN"}
FORBIDDEN_LABEL_STATUSES = {"CONFIRMED_NEGATIVE", "NEGATIVE", "FALSE", "0", "NON_LANDSLIDE"}

VALID_TSI_CLASSES = {
    "VERY_LOW",
    "LOW",
    "MODERATE",
    "HIGH",
    "VERY_HIGH",
    "NODATA_BORDER",
}

VALID_PU_CLASSES = {
    "HIGH_TERRAIN_SIMILARITY",
    "MODERATE_TERRAIN_SIMILARITY",
    "LOW_TERRAIN_SIMILARITY",
    "DISSIMILAR_TERRAIN",
    "NODATA_BORDER",
}

# Known confirmed positive cell IDs verified from historical landslide inventory
KNOWN_POSITIVE_CELL_IDS = {
    "KOH_01187",  # LS_KOH_2022_001
    "KOH_01378",  # LS_KOH_2024_001
    "KOH_02654",  # LS_KOH_2021_001
    "KOH_03071",  # LS_KOH_2023_001
    "KOH_03175",  # LS_KOH_2024_002
    "AIZ_01960",  # LS_AIZ_2024_001
    "AIZ_02185",  # LS_AIZ_2024_002
    "AIZ_02314",  # LS_AIZ_2021_001
    "AIZ_02321",  # LS_AIZ_2023_001
    "AIZ_02431",  # LS_AIZ_2020_001
    "AIZ_02559",  # LS_AIZ_2022_001
}

COORD_LAT_MIN, COORD_LAT_MAX = 22.0, 27.0
COORD_LON_MIN, COORD_LON_MAX = 91.0, 96.0
TSI_SCORE_MIN, TSI_SCORE_MAX = 0.0, 100.0
PU_SIM_MIN, PU_SIM_MAX = 0.0, 1.0


def _check(passed, name, detail, failures):
    """Log check result; append to failures list if failed."""
    if passed:
        log.info(f"  PASS  {name}")
    else:
        log.error(f"  FAIL  {name}: {detail}")
        failures.append(f"{name}: {detail}")
    return passed


def check_file_exists(path, failures):
    ok = path.exists() and path.is_file()
    return _check(ok, "File existence", f"{path} not found", failures)


def check_row_count(rows, failures):
    n = len(rows)
    return _check(
        n == EXPECTED_ROW_COUNT,
        "Row count",
        f"Expected {EXPECTED_ROW_COUNT:,}, found {n:,}",
        failures,
    )


def check_required_columns(header, failures):
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    return _check(
        len(missing) == 0,
        "Required columns",
        f"Missing columns: {missing}",
        failures,
    )


def check_unique_cell_ids(rows, failures):
    ids = [r["cell_id"] for r in rows]
    duplicates = len(ids) - len(set(ids))
    return _check(
        duplicates == 0,
        "Unique cell_id",
        f"{duplicates} duplicate cell IDs found",
        failures,
    )


def check_district_values(rows, failures):
    invalid = [r["cell_id"] for r in rows if r["district"] not in VALID_DISTRICTS]
    return _check(
        len(invalid) == 0,
        "Valid district names",
        f"{len(invalid)} cells have invalid district: sample={invalid[:5]}",
        failures,
    )


def check_label_status_values(rows, failures):
    invalid = [r["cell_id"] for r in rows if r["label_status"] not in VALID_LABEL_STATUSES]
    return _check(
        len(invalid) == 0,
        "Valid label_status values",
        f"{len(invalid)} cells have invalid label_status: sample={invalid[:5]}",
        failures,
    )


def check_no_fabricated_negatives(rows, failures):
    fabricated = [
        r["cell_id"]
        for r in rows
        if r["label_status"].upper() in FORBIDDEN_LABEL_STATUSES
    ]
    return _check(
        len(fabricated) == 0,
        "No fabricated negatives",
        f"{len(fabricated)} cells have forbidden negative label: sample={fabricated[:5]}",
        failures,
    )


def check_confirmed_positive_count(rows, failures):
    positives = [r for r in rows if r["label_status"] == "CONFIRMED_POSITIVE"]
    n = len(positives)
    return _check(
        n == EXPECTED_CONFIRMED_POSITIVES,
        "Confirmed positive count",
        f"Expected {EXPECTED_CONFIRMED_POSITIVES}, found {n}",
        failures,
    )


def check_unknown_count(rows, failures):
    unknowns = [r for r in rows if r["label_status"] == "UNKNOWN"]
    n = len(unknowns)
    return _check(
        n == EXPECTED_UNKNOWN_COUNT,
        "UNKNOWN cell count",
        f"Expected {EXPECTED_UNKNOWN_COUNT:,}, found {n:,}",
        failures,
    )


def check_positive_cell_ids(rows, failures):
    actual_pos_ids = {r["cell_id"] for r in rows if r["label_status"] == "CONFIRMED_POSITIVE"}
    missing_in_file = KNOWN_POSITIVE_CELL_IDS - actual_pos_ids
    extra_in_file = actual_pos_ids - KNOWN_POSITIVE_CELL_IDS
    ok = len(missing_in_file) == 0 and len(extra_in_file) == 0
    detail = []
    if missing_in_file:
        detail.append(f"Missing known positives: {missing_in_file}")
    if extra_in_file:
        detail.append(f"Unexpected positives: {extra_in_file}")
    return _check(ok, "Known positive cell IDs", "; ".join(detail) or "OK", failures)


def check_positive_event_ids(rows, failures):
    bad = [
        r["cell_id"]
        for r in rows
        if r["label_status"] == "CONFIRMED_POSITIVE" and not r.get("historical_event_id", "").strip()
    ]
    return _check(
        len(bad) == 0,
        "Confirmed positives have historical_event_id",
        f"{len(bad)} positives missing event ID: {bad}",
        failures,
    )


def check_unknown_event_ids(rows, failures):
    bad = [
        r["cell_id"]
        for r in rows
        if r["label_status"] == "UNKNOWN" and r.get("historical_event_id", "").strip()
    ]
    return _check(
        len(bad) == 0,
        "UNKNOWN cells have empty historical_event_id",
        f"{len(bad)} UNKNOWN cells have non-empty event ID: sample={bad[:5]}",
        failures,
    )


def check_tsi_classes(rows, failures):
    invalid = [r["cell_id"] for r in rows if r["terrain_susceptibility_class"] not in VALID_TSI_CLASSES]
    return _check(
        len(invalid) == 0,
        "Valid terrain_susceptibility_class values",
        f"{len(invalid)} cells with invalid class: sample={invalid[:5]}",
        failures,
    )


def check_tsi_scores_range(rows, failures):
    """TSI score must be numeric 0-100 for non-NODATA cells; empty for NODATA."""
    errors = []
    for r in rows:
        score_raw = r["terrain_susceptibility_score"].strip()
        tsi_class = r["terrain_susceptibility_class"]

        if tsi_class == "NODATA_BORDER":
            if score_raw != "":
                errors.append(f"{r['cell_id']}: NODATA_BORDER has non-empty score '{score_raw}'")
        else:
            if score_raw == "":
                errors.append(f"{r['cell_id']}: Non-NODATA cell has empty TSI score")
                continue
            try:
                score = float(score_raw)
            except ValueError:
                errors.append(f"{r['cell_id']}: Non-numeric TSI score '{score_raw}'")
                continue
            if not (TSI_SCORE_MIN <= score <= TSI_SCORE_MAX):
                errors.append(f"{r['cell_id']}: TSI score {score:.2f} outside [0, 100]")

    return _check(
        len(errors) == 0,
        "TSI score range [0.0, 100.0]",
        f"{len(errors)} violations. First: {errors[0] if errors else ''}",
        failures,
    )


def check_pu_classes(rows, failures):
    invalid = [r["cell_id"] for r in rows if r["pu_similarity_class"] not in VALID_PU_CLASSES]
    return _check(
        len(invalid) == 0,
        "Valid pu_similarity_class values",
        f"{len(invalid)} cells with invalid PU class: sample={invalid[:5]}",
        failures,
    )


def check_pu_similarity_range(rows, failures):
    """PU similarity must be numeric 0-1 for non-NODATA cells; empty for NODATA."""
    errors = []
    for r in rows:
        sim_raw = r["pu_terrain_similarity"].strip()
        tsi_class = r["terrain_susceptibility_class"]

        if tsi_class == "NODATA_BORDER":
            if sim_raw != "":
                errors.append(f"{r['cell_id']}: NODATA_BORDER has non-empty PU similarity '{sim_raw}'")
        else:
            if sim_raw == "":
                errors.append(f"{r['cell_id']}: Non-NODATA cell has empty PU similarity")
                continue
            try:
                sim = float(sim_raw)
            except ValueError:
                errors.append(f"{r['cell_id']}: Non-numeric PU similarity '{sim_raw}'")
                continue
            if not (PU_SIM_MIN <= sim <= PU_SIM_MAX):
                errors.append(f"{r['cell_id']}: PU similarity {sim:.4f} outside [0, 1]")

    return _check(
        len(errors) == 0,
        "PU similarity range [0.0, 1.0]",
        f"{len(errors)} violations. First: {errors[0] if errors else ''}",
        failures,
    )


def check_terrain_numerics_for_non_nodata(rows, failures):
    """slope_mean, elevation_mean, curvature_mean, twi_mean must be non-empty floats for non-NODATA cells."""
    terrain_fields = ["slope_mean", "elevation_mean", "curvature_mean", "twi_mean"]
    errors = []
    for r in rows:
        if r["terrain_susceptibility_class"] == "NODATA_BORDER":
            continue
        for field in terrain_fields:
            val = r[field].strip()
            if val == "":
                errors.append(f"{r['cell_id']}.{field}: empty on non-NODATA cell")
            else:
                try:
                    float(val)
                except ValueError:
                    errors.append(f"{r['cell_id']}.{field}: non-numeric '{val}'")

    return _check(
        len(errors) == 0,
        "Terrain numeric fields populated for non-NODATA cells",
        f"{len(errors)} violations. First: {errors[0] if errors else ''}",
        failures,
    )


def check_coordinate_ranges(rows, failures):
    errors = []
    for r in rows:
        try:
            lat = float(r["latitude"])
            lon = float(r["longitude"])
        except ValueError:
            errors.append(f"{r['cell_id']}: non-numeric coordinates")
            continue
        if not (COORD_LAT_MIN <= lat <= COORD_LAT_MAX):
            errors.append(f"{r['cell_id']}: lat {lat:.4f} outside [{COORD_LAT_MIN}, {COORD_LAT_MAX}]")
        if not (COORD_LON_MIN <= lon <= COORD_LON_MAX):
            errors.append(f"{r['cell_id']}: lon {lon:.4f} outside [{COORD_LON_MIN}, {COORD_LON_MAX}]")

    return _check(
        len(errors) == 0,
        "Coordinate ranges (lat 22-27 N, lon 91-96 E)",
        f"{len(errors)} violations. First: {errors[0] if errors else ''}",
        failures,
    )


def check_spatial_block_format(rows, failures):
    errors = []
    for r in rows:
        block = r["spatial_block_id"].strip()
        district = r["district"]
        if not block:
            errors.append(f"{r['cell_id']}: empty spatial_block_id")
            continue
        expected_prefix = "BLK_KOH" if district == "Kohima" else "BLK_AIZ"
        if not block.startswith(expected_prefix):
            errors.append(f"{r['cell_id']}: block '{block}' does not match district '{district}'")

    return _check(
        len(errors) == 0,
        "Spatial block prefix matches district",
        f"{len(errors)} violations. First: {errors[0] if errors else ''}",
        failures,
    )


def check_primary_contributors_nonempty(rows, failures):
    empty = [r["cell_id"] for r in rows if not r["primary_terrain_contributors"].strip()]
    return _check(
        len(empty) == 0,
        "primary_terrain_contributors field non-empty",
        f"{len(empty)} cells have empty contributors: sample={empty[:5]}",
        failures,
    )


def check_nodata_count(rows, failures):
    nodata = [r for r in rows if r["terrain_susceptibility_class"] == "NODATA_BORDER"]
    n = len(nodata)
    return _check(
        n == EXPECTED_NODATA_COUNT,
        "NODATA_BORDER count",
        f"Expected {EXPECTED_NODATA_COUNT:,}, found {n:,}",
        failures,
    )


def check_district_cell_counts(rows, failures):
    kohima = sum(1 for r in rows if r["district"] == "Kohima")
    aizawl = sum(1 for r in rows if r["district"] == "Aizawl")
    total = kohima + aizawl
    ok = total == EXPECTED_ROW_COUNT
    return _check(
        ok,
        "District cell counts sum to total",
        f"Kohima ({kohima:,}) + Aizawl ({aizawl:,}) = {total:,}, expected {EXPECTED_ROW_COUNT:,}",
        failures,
    )


def run_validation():
    log.info("=" * 75)
    log.info("NER Safe -- STEP 9A: Baseline Susceptibility Validation")
    log.info(f"Target file: {OUTPUT_CSV}")
    log.info("=" * 75)

    failures = []

    # Check 0: File existence
    if not check_file_exists(OUTPUT_CSV, failures):
        log.error("Cannot proceed: file not found. Aborting.")
        log.error("=" * 75)
        log.error("VALIDATION RESULT: FAILED")
        return 1

    # Load CSV
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        header = reader.fieldnames or []

    log.info(f"Loaded {len(rows):,} rows, {len(header)} columns from {OUTPUT_CSV.name}")
    log.info("")
    log.info("Running integrity checks...")
    log.info("")

    total_checks = 0

    # Structural checks
    log.info("[ STRUCTURAL INTEGRITY ]")
    check_row_count(rows, failures); total_checks += 1
    check_required_columns(header, failures); total_checks += 1
    check_unique_cell_ids(rows, failures); total_checks += 1
    check_district_cell_counts(rows, failures); total_checks += 1

    # Geographic checks
    log.info("")
    log.info("[ GEOGRAPHIC VALIDITY ]")
    check_district_values(rows, failures); total_checks += 1
    check_coordinate_ranges(rows, failures); total_checks += 1
    check_spatial_block_format(rows, failures); total_checks += 1

    # Label integrity -- anti-fabrication protocol
    log.info("")
    log.info("[ LABEL INTEGRITY & ANTI-FABRICATION ]")
    check_label_status_values(rows, failures); total_checks += 1
    check_no_fabricated_negatives(rows, failures); total_checks += 1
    check_confirmed_positive_count(rows, failures); total_checks += 1
    check_unknown_count(rows, failures); total_checks += 1
    check_positive_cell_ids(rows, failures); total_checks += 1
    check_positive_event_ids(rows, failures); total_checks += 1
    check_unknown_event_ids(rows, failures); total_checks += 1

    # Terrain feature checks
    log.info("")
    log.info("[ TERRAIN FEATURE VALUES ]")
    check_tsi_classes(rows, failures); total_checks += 1
    check_tsi_scores_range(rows, failures); total_checks += 1
    check_terrain_numerics_for_non_nodata(rows, failures); total_checks += 1
    check_nodata_count(rows, failures); total_checks += 1

    # PU analysis checks
    log.info("")
    log.info("[ POSITIVE-UNLABELED ANALYSIS VALUES ]")
    check_pu_classes(rows, failures); total_checks += 1
    check_pu_similarity_range(rows, failures); total_checks += 1

    # Attribution checks
    log.info("")
    log.info("[ EXPLAINABILITY FIELDS ]")
    check_primary_contributors_nonempty(rows, failures); total_checks += 1

    # Summary
    passed = total_checks - len(failures)
    log.info("")
    log.info("=" * 75)

    if failures:
        log.error(f"VALIDATION RESULT: *** FAILED *** -- {len(failures)} of {total_checks} checks FAILED")
        log.error("")
        log.error("Failed checks:")
        for i, f in enumerate(failures, 1):
            log.error(f"  [{i}] {f}")
        log.info("=" * 75)
        return 1
    else:
        log.info(f"VALIDATION RESULT: ALL PASSED -- {passed}/{total_checks} checks PASSED")
        log.info("")
        # Summary statistics
        kohima_count = sum(1 for r in rows if r["district"] == "Kohima")
        aizawl_count = sum(1 for r in rows if r["district"] == "Aizawl")
        nodata_count = sum(1 for r in rows if r["terrain_susceptibility_class"] == "NODATA_BORDER")
        class_counts = {}
        for r in rows:
            c = r["terrain_susceptibility_class"]
            class_counts[c] = class_counts.get(c, 0) + 1

        log.info("  Dataset Summary:")
        log.info(f"    Total cells        : {len(rows):,}")
        log.info(f"    Kohima cells       : {kohima_count:,}")
        log.info(f"    Aizawl cells       : {aizawl_count:,}")
        log.info(f"    Confirmed positive : {EXPECTED_CONFIRMED_POSITIVES}")
        log.info(f"    Unknown            : {EXPECTED_UNKNOWN_COUNT:,}")
        log.info(f"    Fabricated neg.    : 0 (protocol enforced)")
        log.info(f"    NODATA cells       : {nodata_count:,}")
        log.info(f"    TSI class dist.    : {class_counts}")
        log.info("=" * 75)
        return 0


def main():
    return run_validation()


if __name__ == "__main__":
    sys.exit(main())
