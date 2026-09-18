#!/usr/bin/env python3
"""
ingest_sentinel1_sar.py — Sentinel-1 SAR Observation Table Ingestion

STEP 9B, Task 6 — Sentinel-1 SAR Change Evidence Pipeline
NER Safe (SIH 2026) — AI-Based Early Warning and Landslide Risk Monitoring System

Builds and maintains the per-cell Sentinel-1 SAR observation table:
  data/satellite/sentinel_sar_latest_observations.csv

This table records the LATEST AVAILABLE SAR change observation for each of
the 16,961 analysis grid cells (6,055 Kohima + 10,906 Aizawl).

ARCHITECTURE:

  This script is the final stage of the four-stage SAR pipeline:

    Stage 1 (download_sentinel1.py)     -> Search + catalog ASF DAAC scenes
    Stage 2 (process_sar_change.py)     -> Calibrate + terrain-correct + compute change
    Stage 3 (assign_grid_satellite.py)  -> Zonal-aggregate to 500m grid
    Stage 4 (THIS SCRIPT)               -> Build per-cell latest-observation table

  This per-cell table enables the frontend risk dashboard to display the
  LATEST AVAILABLE satellite SAR change signal for any selected 500m cell,
  analogous to gpm_latest_observations.csv and smap_latest_observations.csv.

ANTI-FABRICATION RULES:
  - SAR change values (vv_change_db, vh_change_db, etc.) MUST remain empty
    when no real processed scenes are available.
  - We do NOT invent, simulate, average, or randomize SAR observations.
  - Missing data is flagged as REQUIRES_EXTERNAL_AUTH or MISSING.
  - Status flags propagate from grid_satellite_features.csv if available.

AUTHENTICATION:
  Stages 1-2 require NASA Earthdata credentials for scene download:
    EARTHDATA_USERNAME and EARTHDATA_PASSWORD environment variables
    OR ~/.netrc with machine urs.earthdata.nasa.gov

IMPORTANT — SCIENTIFIC TERMINOLOGY:
  Sentinel-1 operates on a 12-day repeat orbit cycle.
  Observations reflect LATEST AVAILABLE SAR passes, NOT real-time radar.
  UI must never describe SAR data as "live" or "real-time".
  Correct terminology: "Latest available satellite SAR observation"

Usage:
  python scripts/ingest_sentinel1_sar.py --dry-run
  python scripts/ingest_sentinel1_sar.py --run
  python scripts/ingest_sentinel1_sar.py --run --district Kohima
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# -- Dependency Verification --------------------------------------------------
try:
    import numpy as np
except ImportError:
    print("ERROR: 'numpy' library is required. Install via: pip install numpy")
    sys.exit(1)

# -- Paths --------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
SATELLITE_DIR = DATA_DIR / "satellite"
HISTORICAL_DIR = DATA_DIR / "historical"
CACHE_DIR = SATELLITE_DIR / "cache"

CATALOG_FILE = SATELLITE_DIR / "sentinel1_catalog.json"
TEST_PAIRS_FILE = SATELLITE_DIR / "test_pairs.json"
SAR_FEATURES_CSV = HISTORICAL_DIR / "grid_satellite_features.csv"
OUTPUT_CSV = SATELLITE_DIR / "sentinel_sar_latest_observations.csv"
CACHE_MANIFEST = CACHE_DIR / "satellite_cache_manifest.json"

# -- Logging ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ingest_sentinel1_sar")

# -- District Configuration ---------------------------------------------------
DISTRICTS = [
    {
        "name": "Kohima",
        "state": "Nagaland",
        "prefix": "KOH_",
        "grid_file": BOUNDARIES_DIR / "kohima_grid_500m.geojson",
        "expected_cells": 6055,
    },
    {
        "name": "Aizawl",
        "state": "Mizoram",
        "prefix": "AIZ_",
        "grid_file": BOUNDARIES_DIR / "aizawl_grid_500m.geojson",
        "expected_cells": 10906,
    },
]

# -- Output CSV Column Schema -------------------------------------------------
# Matches the canonical dynamic observation schema (STEP_9B_DYNAMIC_DATA_SCHEMA.md)
# and the project-level SAR change features.
OUTPUT_COLUMNS = [
    "cell_id",               # 500m grid cell identifier (KOH_* / AIZ_*)
    "district",              # Kohima or Aizawl
    "latitude",              # Centroid decimal degrees WGS84
    "longitude",             # Centroid decimal degrees WGS84
    "observation_timestamp", # ISO 8601 UTC of latest SAR pass or empty
    "source",                # Copernicus Sentinel-1 (C-SAR IW GRD)
    "source_product",        # S1A_IW_GRDH / S1C_IW_GRDH / S1D_IW_GRDH
    "source_resolution",     # 10m pixel (IW GRDH); 500m = analysis grid, NOT sensor res.
    "platform",              # Sentinel-1A / Sentinel-1C / Sentinel-1D
    "relative_orbit",        # Relative orbit number (determines coverage geometry)
    "flight_direction",      # ASCENDING or DESCENDING
    "polarization",          # VV+VH (dual-pol)
    "pre_scene_date",        # Acquisition date of pre-event scene (YYYY-MM-DD) or empty
    "post_scene_date",       # Acquisition date of post-event scene (YYYY-MM-DD) or empty
    "repeat_interval_days",  # Days between pre and post acquisitions or empty
    "vv_change_db",          # 10*log10(sigma0_vv_post / sigma0_vv_pre) in dB or empty
    "vh_change_db",          # 10*log10(sigma0_vh_post / sigma0_vh_pre) in dB or empty
    "vv_vh_change",          # Euclidean SAR change signal magnitude sqrt(vv^2+vh^2) or empty
    "change_confidence",     # Normalized anomaly intensity [0.0-1.0] or empty
    "data_status",           # AVAILABLE / REQUIRES_EXTERNAL_AUTH / MISSING / STALE
    "quality_flag",          # Descriptive QC flag
    "source_timestamp",      # When ASF granule was published (post-scene start) or empty
    "ingestion_timestamp",   # When this record was generated (ISO 8601 UTC)
    "scientific_notice",     # Anti-fabrication notice embedded per record
]

SCIENTIFIC_NOTICE = (
    "SAR change is CORROBORATING ANOMALY EVIDENCE only. "
    "It must NEVER be automatically labelled as a landslide. "
    "Possible sources: soil moisture, vegetation, surface roughness, "
    "construction, agriculture, acquisition geometry, or actual ground disturbance. "
    "Human/officer verification is mandatory."
)

SOURCE = "Copernicus Sentinel-1 (C-SAR IW GRD)"
SOURCE_PRODUCT = "S1_IW_GRDH_DUAL_POL"
SOURCE_RESOLUTION = (
    "10m pixel spacing (IW GRDH); "
    "500m = project analysis grid, NOT native sensor resolution"
)


# =============================================================================
#  Authentication Check
# =============================================================================

def check_earthdata_credentials():
    """
    Check for NASA Earthdata credentials (required for scene download).
    Returns (available: bool, source: str | None).
    Credentials are NEVER printed or logged.
    """
    if os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"):
        return True, "environment variables (EARTHDATA_USERNAME / EARTHDATA_PASSWORD)"

    for name in (".netrc", "_netrc"):
        netrc_path = Path.home() / name
        if netrc_path.exists():
            try:
                from netrc import netrc as parse_netrc
                nrc = parse_netrc(str(netrc_path))
                auth = nrc.authenticators("urs.earthdata.nasa.gov")
                if auth and auth[0]:
                    return True, str(netrc_path)
            except Exception as e:
                log.warning(f"Could not parse {netrc_path}: {e}")

    return False, None


# =============================================================================
#  SAR Features Lookup
# =============================================================================

def load_sar_features_index():
    """
    Load grid_satellite_features.csv into an index keyed by cell_id for
    the latest available SAR observations.

    Returns: dict of {cell_id: latest_row_dict} or empty dict.
    Only rows with data_status == AVAILABLE are considered real observations.
    """
    if not SAR_FEATURES_CSV.exists():
        return {}

    index = {}
    try:
        with open(SAR_FEATURES_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("cell_id", "")
                if not cid:
                    continue
                # Keep the LATEST observation per cell (by observation_date, descending)
                if cid not in index:
                    index[cid] = row
                else:
                    existing_date = index[cid].get("observation_date", "")
                    new_date = row.get("observation_date", "")
                    if new_date > existing_date:
                        index[cid] = row
    except Exception as e:
        log.warning(f"Could not read {SAR_FEATURES_CSV}: {e}")
        return {}

    log.info(f"SAR features index loaded: {len(index)} cells with existing observations")
    return index


def load_catalog_metadata():
    """Load sentinel1_catalog.json for scene count and metadata."""
    if not CATALOG_FILE.exists():
        return {}
    try:
        with open(CATALOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not read catalog: {e}")
        return {}


def load_test_pairs():
    """Load test_pairs.json with curated repeat-pass pairs per district."""
    if not TEST_PAIRS_FILE.exists():
        return {}
    try:
        with open(TEST_PAIRS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not read test pairs: {e}")
        return {}


# =============================================================================
#  Per-Cell Record Builder
# =============================================================================

def is_real_numeric(v):
    """
    Return True only if v is a non-empty, non-NaN, non-nodata numeric value.
    Rejects -9999 nodata sentinel, NaN, infinity, empty strings.
    """
    if v == "" or v is None:
        return False
    try:
        fv = float(v)
        if fv == -9999.0:
            return False
        if fv != fv:  # NaN check
            return False
        if abs(fv) == float("inf"):
            return False
        return True
    except (ValueError, TypeError):
        return False


def build_cell_record(
    cell_id: str,
    district: str,
    lat: float,
    lon: float,
    sar_obs=None,
    test_pairs=None,
    now_utc_str: str = "",
) -> dict:
    """
    Build a single per-cell SAR observation record.

    If a real SAR observation exists in sar_obs (from grid_satellite_features.csv)
    with status AVAILABLE and valid numeric VV/VH values, populate SAR fields.
    Otherwise, leave all SAR numeric fields empty with REQUIRES_EXTERNAL_AUTH.

    STRICT ANTI-FABRICATION: SAR numeric fields are NEVER filled with synthetic
    values — no zeros, averages, random numbers, or placeholder constants.
    """
    record = {
        "cell_id": cell_id,
        "district": district,
        "latitude": f"{lat:.6f}",
        "longitude": f"{lon:.6f}",
        "observation_timestamp": "",
        "source": SOURCE,
        "source_product": SOURCE_PRODUCT,
        "source_resolution": SOURCE_RESOLUTION,
        "platform": "",
        "relative_orbit": "",
        "flight_direction": "",
        "polarization": "VV+VH",
        "pre_scene_date": "",
        "post_scene_date": "",
        "repeat_interval_days": "",
        "vv_change_db": "",
        "vh_change_db": "",
        "vv_vh_change": "",
        "change_confidence": "",
        "data_status": "REQUIRES_EXTERNAL_AUTH",
        "quality_flag": "UNAVAILABLE_PENDING_EARTHDATA_LOGIN",
        "source_timestamp": "",
        "ingestion_timestamp": now_utc_str,
        "scientific_notice": SCIENTIFIC_NOTICE,
    }

    # Enrich with curated test pair geometry metadata for the district
    # (This records catalog-level information — NO numeric SAR values here)
    if test_pairs and district in test_pairs:
        pair = test_pairs[district]
        geom = pair.get("geometry", {})
        pre = pair.get("pre_event_scene", {})
        post = pair.get("post_event_scene", {})
        record["platform"] = geom.get("platform", "")
        record["relative_orbit"] = str(geom.get("relative_orbit", ""))
        record["flight_direction"] = geom.get("flight_direction", "")
        record["polarization"] = geom.get("polarization", "VV+VH")
        record["pre_scene_date"] = pre.get("acquisition_date", "")
        record["post_scene_date"] = post.get("acquisition_date", "")
        ri = geom.get("repeat_interval_days")
        record["repeat_interval_days"] = str(ri) if ri else ""
        # Post-scene acquisition time documents when the latest catalog pass occurred
        record["source_timestamp"] = post.get("start_time", "")

    # If a real processed SAR observation is available for this cell, use it
    if sar_obs and sar_obs.get("data_status") == "AVAILABLE":
        vv = sar_obs.get("vv_change_db", "")
        vh = sar_obs.get("vh_change_db", "")
        vvvh = sar_obs.get("vv_vh_change", "")
        conf = sar_obs.get("change_confidence", "")

        if is_real_numeric(vv) and is_real_numeric(vh):
            record["vv_change_db"] = str(vv)
            record["vh_change_db"] = str(vh)
            record["vv_vh_change"] = str(vvvh) if is_real_numeric(vvvh) else ""
            record["change_confidence"] = str(conf) if is_real_numeric(conf) else ""
            record["observation_timestamp"] = sar_obs.get("source_timestamp", "")
            record["data_status"] = "AVAILABLE"
            record["quality_flag"] = "REAL_SAR_CHANGE_OBSERVATION"
            scene_id = sar_obs.get("scene_id", "")
            if scene_id:
                record["source_product"] = scene_id

    return record


# =============================================================================
#  Main Ingestion Pipeline
# =============================================================================

def run_ingestion(args):
    """Execute the Sentinel-1 SAR per-cell observation table ingestion."""
    log.info("=" * 70)
    log.info("NER Safe -- STEP 9B Task 6: Sentinel-1 SAR Observation Table")
    log.info("=" * 70)

    now_utc = datetime.now(timezone.utc)
    now_utc_str = now_utc.isoformat()

    # -- Authentication Status ------------------------------------------------
    creds_available, creds_source = check_earthdata_credentials()
    if creds_available:
        log.info(f"+ NASA Earthdata credentials found: {creds_source}")
        log.info("  -> Scene download is possible (run download_sentinel1.py --download)")
    else:
        log.info("- No NASA Earthdata credentials detected.")
        log.info("  -> SAR change fields will remain empty (REQUIRES_EXTERNAL_AUTH).")
        log.info("  -> To configure credentials:")
        log.info("    Option 1: Set environment variables:")
        log.info("      EARTHDATA_USERNAME=<your_username>")
        log.info("      EARTHDATA_PASSWORD=<your_password>")
        log.info("    Option 2: Create ~/.netrc (or ~/_netrc on Windows):")
        log.info("      machine urs.earthdata.nasa.gov")
        log.info("      login <username>")
        log.info("      password <password>")
        log.info("    Register free: https://urs.earthdata.nasa.gov/")

    log.info("")

    # -- Load Inputs ----------------------------------------------------------
    sar_index = load_sar_features_index()
    test_pairs = load_test_pairs()
    catalog = load_catalog_metadata()

    catalog_total = catalog.get("metadata", {}).get("total_granules", 0)
    log.info(f"Sentinel-1 catalog: {catalog_total} granules indexed")
    log.info(f"Test pairs configured: {list(test_pairs.keys()) if test_pairs else 'None'}")
    log.info(f"Existing SAR grid observations: {len(sar_index)} cells with data")
    log.info("")

    # -- Filter Districts -----------------------------------------------------
    target_districts = DISTRICTS
    if args.district:
        target_districts = [d for d in DISTRICTS if d["name"] == args.district]
        if not target_districts:
            log.error(f"Unknown district: {args.district}")
            return 1

    # -- Load Grid GeoJSON Files ----------------------------------------------
    all_cells = []
    for dcfg in target_districts:
        gfile = dcfg["grid_file"]
        if not gfile.exists():
            log.error(f"Required grid GeoJSON missing: {gfile}")
            return 1

        with open(gfile, "r", encoding="utf-8") as f:
            feat_coll = json.load(f)

        features = feat_coll.get("features", [])
        actual_count = len(features)
        expected_count = dcfg["expected_cells"]

        if actual_count != expected_count:
            log.error(
                f"{dcfg['name']}: Expected {expected_count} cells, "
                f"found {actual_count}. Grid integrity check FAILED."
            )
            return 1

        log.info(
            f"+ {dcfg['name']} ({dcfg['state']}): "
            f"{actual_count} cells loaded (expected {expected_count})"
        )
        for feat in features:
            props = feat.get("properties", {})
            all_cells.append({
                "cell_id": props.get("cell_id", ""),
                "district": dcfg["name"],
                "lat": float(props.get("centroid_lat", 0.0)),
                "lon": float(props.get("centroid_lon", 0.0)),
            })

    log.info(f"Total cells to process: {len(all_cells):,}")
    log.info("")

    if args.dry_run:
        log.info("DRY-RUN MODE: No files will be written.")
        log.info(f"  -> Output would be written to: {OUTPUT_CSV}")
        log.info(f"  -> Would process {len(all_cells):,} cells")
        log.info(f"  -> SAR field availability: "
                 f"{'AVAILABLE via grid_satellite_features.csv' if sar_index else 'REQUIRES_EXTERNAL_AUTH'}")
        log.info("  -> No fabricated SAR values will ever be generated.")
        log.info("DRY-RUN COMPLETE.")
        return 0

    # -- Build Output Table ---------------------------------------------------
    log.info("Building per-cell SAR observation table...")
    SATELLITE_DIR.mkdir(parents=True, exist_ok=True)

    total_available = 0
    total_requires_auth = 0
    total_missing = 0

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for cell in all_cells:
            cell_id = cell["cell_id"]
            district = cell["district"]
            lat = cell["lat"]
            lon = cell["lon"]

            sar_obs = sar_index.get(cell_id)

            record = build_cell_record(
                cell_id=cell_id,
                district=district,
                lat=lat,
                lon=lon,
                sar_obs=sar_obs,
                test_pairs=test_pairs,
                now_utc_str=now_utc_str,
            )

            writer.writerow(record)

            status = record["data_status"]
            if status == "AVAILABLE":
                total_available += 1
            elif status == "REQUIRES_EXTERNAL_AUTH":
                total_requires_auth += 1
            else:
                total_missing += 1

    log.info(f"+ Satellite SAR observation table written -> {OUTPUT_CSV}")
    log.info("")
    log.info("=================== INGESTION SUMMARY ===================")
    log.info(f"Total cells processed:         {len(all_cells):,}")
    log.info(f"  AVAILABLE observations:       {total_available:,}")
    log.info(f"  REQUIRES_EXTERNAL_AUTH:       {total_requires_auth:,}")
    log.info(f"  MISSING:                      {total_missing:,}")
    log.info(f"  Fabricated values:            0 (Anti-fabrication protocol)")
    log.info("")
    if total_available == 0:
        log.info("- No real Sentinel-1 SAR change observations available.")
        log.info("  Pipeline requires:")
        log.info("    1. NASA Earthdata credentials")
        log.info("    2. Scene download: python scripts/download_sentinel1.py --download")
        log.info("    3. Processing:     python scripts/process_sar_change.py --test")
        log.info("    4. Grid assign:    python scripts/assign_grid_satellite.py")
        log.info("    5. Re-run:         python scripts/ingest_sentinel1_sar.py --run")
    else:
        log.info(f"+ {total_available:,} cells have real SAR change observations.")
    log.info("=" * 55)
    return 0


# =============================================================================
#  CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sentinel-1 SAR Per-Cell Observation Table Ingestion "
            "(NER Safe STEP 9B Task 6)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Inspect inputs and report without writing files",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        default=False,
        help="Execute ingestion and write sentinel_sar_latest_observations.csv",
    )
    parser.add_argument(
        "--district",
        choices=["Kohima", "Aizawl"],
        default=None,
        help="Process only one district (default: both)",
    )

    args = parser.parse_args()

    # Default to dry-run if no action specified
    if not args.run:
        args.dry_run = True

    return run_ingestion(args)


if __name__ == "__main__":
    sys.exit(main())
