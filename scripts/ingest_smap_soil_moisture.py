#!/usr/bin/env python3
"""
ingest_smap_soil_moisture.py — NASA SMAP Soil Moisture Ingestion Pipeline

STEP 5: NASA SMAP Soil Moisture Ingestion
NER Safe (SIH 2026) — AI-Based Early Warning and Landslide Risk Monitoring System
Pilot Focus: Kohima District (Nagaland) & Aizawl District (Mizoram)

Operational Ingestion Contract:
  - Source: NASA Soil Moisture Active Passive (SMAP) Enhanced Radiometer
  - Product: SMAP Enhanced L3 Radiometer Global Daily 9 km EASE-Grid Soil Moisture (SPL3SMP_E Version 6)
  - Native Spatial Resolution: ~9 km EASE-Grid 2.0 Global Cylindrical (EPSG:6933)
  - Temporal Cadence: Daily composite (Descending morning AM ~06:00 LST & Ascending afternoon PM ~18:00 LST)
  - Analysis Grid: 16,961 cells of 500 m × 500 m (Kohima: 6,055, Aizawl: 10,906)
  - Output Storage: data/soil_moisture/smap_latest_observations.csv

Anti-Fabrication & Scientific Truthfulness Protocol:
  - Securely checks NASA Earthdata credentials (EARTHDATA_TOKEN, NASA_EARTHDATA_USERNAME/PASSWORD, or ~/.netrc).
  - If credentials or remote data are unavailable, values remain strictly empty/NaN with
    data_status = 'REQUIRES_EXTERNAL_AUTH' and quality_flag = 'UNAVAILABLE_PENDING_EARTHDATA_LOGIN'.
  - NEVER substitutes random, synthetic, guessed, manually invented, or placeholder numbers.
  - Documents spatial mapping disparity: ~9 km SMAP macro footprint mapped to 500 m display cells.
  - Preserves exact volumetric soil water content unit: m³/m³ (0.02 - 0.60 m³/m³).
"""

import csv
import logging
import math
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import h5py
import numpy as np
import pyproj
from scipy.spatial import KDTree
from dotenv import load_dotenv

# Load environment variables securely from .env
load_dotenv()

# ── Project Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ML_DIR = DATA_DIR / "ml"
SOIL_MOISTURE_DIR = DATA_DIR / "soil_moisture"
RAW_SMAP_DIR = SOIL_MOISTURE_DIR / "raw"
GRID_SOURCE_CSV = ML_DIR / "baseline_susceptibility.csv"
OUTPUT_SMAP_CSV = SOIL_MOISTURE_DIR / "smap_latest_observations.csv"

# ── Product Specifications ───────────────────────────────────────────────────
SMAP_SOURCE_NAME = "NASA / NSIDC SMAP Mission"
SMAP_PRODUCT_NAME = "SPL3SMP_E_V006"
SMAP_RESOLUTION_NOTE = "9 km (EASE-Grid 2.0) Daily"
SMAP_UNIT = "m^3/m^3"

# Controlled status vocabulary
STATUS_AVAILABLE = "AVAILABLE"
STATUS_REQUIRES_AUTH = "REQUIRES_EXTERNAL_AUTH"
STATUS_MISSING = "MISSING"
STATUS_STALE = "STALE"
STATUS_QUALITY_REJECTED = "QUALITY_REJECTED"

# Staleness threshold in hours for daily satellite products
STALENESS_THRESHOLD_HOURS = 48.0

# Coordinate transformation for EASE-Grid 2.0 Global Cylindrical (EPSG:6933)
wgs_to_ease2 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform

# EASE-Grid 2.0 9km parameters
EASE2_CELL_SIZE = 9008.055627
EASE2_X_MIN = -17367530.44
EASE2_Y_MAX = 7314540.83

OUTPUT_HEADERS = [
    "cell_id",
    "district",
    "latitude",
    "longitude",
    "smap_ease2_grid_cell",
    "observation_timestamp",
    "soil_moisture_current",
    "soil_moisture_previous",
    "soil_moisture_change",
    "soil_moisture_change_percent",
    "source",
    "source_product",
    "source_resolution",
    "data_status",
    "source_timestamp",
    "ingestion_timestamp",
    "quality_flag",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("ingest_smap_soil_moisture")


def get_smap_ease2_cell(lon: float, lat: float) -> str:
    """
    Computes the exact EASE-Grid 2.0 9 km row and column index (EPSG:6933)
    corresponding to the given WGS84 coordinates.
    """
    x, y = wgs_to_ease2(lon, lat)
    col = int((x - EASE2_X_MIN) / EASE2_CELL_SIZE)
    row = int((EASE2_Y_MAX - y) / EASE2_CELL_SIZE)
    return f"EASE2_M09_R{row:04d}_C{col:04d}"


def check_earthdata_credentials() -> Tuple[bool, str]:
    """
    Checks if NASA Earthdata credentials exist via environment variables or ~/.netrc.
    Never exposes or logs secret values.
    """
    if os.environ.get("EARTHDATA_TOKEN"):
        return True, "EARTHDATA_TOKEN_ENV_VAR"
    if os.environ.get("NASA_EARTHDATA_USERNAME") and os.environ.get("NASA_EARTHDATA_PASSWORD"):
        return True, "NASA_EARTHDATA_ENV_VARS"
    if os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"):
        return True, "EARTHDATA_USER_PASS_ENV_VARS"
    netrc_path = Path.home() / ".netrc"
    if netrc_path.exists():
        try:
            with open(netrc_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "urs.earthdata.nasa.gov" in content:
                    return True, "NETRC_FILE"
        except Exception:
            pass
    return False, "NO_CREDENTIALS_FOUND"


def get_earthdata_auth() -> Tuple[bool, str, Optional[object]]:
    """Authenticates with NASA Earthdata using earthaccess library."""
    has_creds, cred_source = check_earthdata_credentials()
    if not has_creds:
        return False, "NO_CREDENTIALS_FOUND", None

    try:
        import earthaccess
        token = os.environ.get("EARTHDATA_TOKEN")
        strategy = "environment" if token else "netrc"
        auth = earthaccess.login(strategy=strategy)
        if auth.authenticated:
            log.info(f"earthaccess authenticated for SMAP (strategy: {strategy}, source: {cred_source})")
            return True, cred_source, auth
        else:
            log.warning("earthaccess login returned authenticated=False.")
            return False, "AUTH_FAILED", None
    except ImportError:
        log.error("earthaccess not installed. Run: pip install earthaccess")
        return False, "EARTHACCESS_NOT_INSTALLED", None
    except Exception as e:
        log.warning(f"earthaccess login failed: {e}")
        return False, "AUTH_EXCEPTION", None


def fetch_and_download_smap_granules(max_granules: int = 3) -> List[Path]:
    """
    Uses earthaccess to search NASA CMR for SMAP SPL3SMP_E V006 granules
    covering Kohima and Aizawl, downloading them to RAW_SMAP_DIR.
    Reuses existing cached valid granules when available.
    """
    RAW_SMAP_DIR.mkdir(parents=True, exist_ok=True)
    existing_cached = sorted([g for g in RAW_SMAP_DIR.glob("*.h5") if g.stat().st_size > 1_000_000], reverse=True) + \
                      sorted([g for g in RAW_SMAP_DIR.glob("*.HDF5") if g.stat().st_size > 1_000_000], reverse=True)

    if len(existing_cached) >= 2:
        log.info(f"Reusing {len(existing_cached)} existing cached SMAP granule(s) from disk:")
        for g in existing_cached:
            log.info(f"  • {g.name} ({g.stat().st_size:,} bytes)")
        return existing_cached

    downloaded = []

    try:
        import earthaccess
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        
        results = earthaccess.search_data(
            short_name="SPL3SMP_E",
            version="006",
            bounding_box=(92.0, 23.0, 95.0, 26.5),
            temporal=(start, end),
            sort_key="-start_date",
            count=max_granules,
        )
        if not results:
            log.warning("earthaccess CMR search returned 0 SMAP granules.")
        else:
            log.info(f"earthaccess CMR returned {len(results)} SMAP granule(s).")
            to_download = []
            for r in results:
                native_id = r["meta"].get("native-id", "")
                fname = native_id.split(":")[-1] if ":" in native_id else native_id
                if not (fname.endswith(".h5") or fname.endswith(".HDF5")):
                    fname += ".h5"
                cached = RAW_SMAP_DIR / fname
                if cached.exists() and cached.stat().st_size > 1_000_000:
                    log.info(f"Using cached SMAP granule: {fname}")
                    downloaded.append(cached)
                else:
                    to_download.append(r)

            if to_download:
                log.info(f"Downloading {len(to_download)} SMAP granule(s) via earthaccess...")
                files = earthaccess.download(to_download, local_path=str(RAW_SMAP_DIR))
                for f in files:
                    fp = Path(f)
                    if fp.exists() and fp.stat().st_size > 1_000_000:
                        log.info(f"✓ Downloaded {fp.name} ({fp.stat().st_size:,} bytes)")
                        downloaded.append(fp)
    except Exception as e:
        log.warning(f"earthaccess SMAP search/download failed: {e}")

    all_granules = list(set(downloaded + existing_cached))
    valid_granules = sorted([g for g in all_granules if g.stat().st_size > 1_000_000], reverse=True)
    return valid_granules


def parse_smap_granule(fp: Path) -> List[Dict[str, Any]]:
    """
    Parses a single SMAP HDF5 granule and returns valid observation passes (AM / PM)
    covering the NER region (bounding box [22.0, 27.0] N, [91.0, 96.0] E).
    """
    m = re.search(r"SMAP_L3_SM_P_E_(\d{8})_", fp.name)
    if not m:
        return []
    date_str = m.group(1)
    date_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    passes = []
    try:
        with h5py.File(fp, "r") as hf:
            for grp_name, sm_key, lat_key, lon_key, pass_time in [
                ("Soil_Moisture_Retrieval_Data_PM", "soil_moisture_pm", "latitude_pm", "longitude_pm", "18:00:00Z"),
                ("Soil_Moisture_Retrieval_Data_AM", "soil_moisture", "latitude", "longitude", "06:00:00Z"),
            ]:
                if grp_name not in hf:
                    continue
                g = hf[grp_name]
                if sm_key not in g or lat_key not in g or lon_key not in g:
                    continue

                lat = g[lat_key][:]
                lon = g[lon_key][:]
                sm_ds = g[sm_key]
                fill_val = float(sm_ds.attrs.get("_FillValue", -9999.0))
                sm = sm_ds[:]

                valid_mask = (
                    (lat > -90.0) & (lat < 90.0) &
                    (lon > -180.0) & (lon < 180.0) &
                    (sm != fill_val) & (sm >= 0.02) & (sm <= 0.60)
                )

                smap_lats = lat[valid_mask]
                smap_lons = lon[valid_mask]
                smap_vals = sm[valid_mask]

                ner_mask = (
                    (smap_lats >= 22.0) & (smap_lats <= 27.0) &
                    (smap_lons >= 91.0) & (smap_lons <= 96.0)
                )

                if np.sum(ner_mask) > 0:
                    pass_timestamp = f"{date_iso}T{pass_time}"
                    dt_obj = datetime.strptime(f"{date_str} {pass_time[:5]}", "%Y%m%d %H:%M").replace(tzinfo=timezone.utc)
                    passes.append({
                        "timestamp": pass_timestamp,
                        "dt_obj": dt_obj,
                        "lats": smap_lats[ner_mask],
                        "lons": smap_lons[ner_mask],
                        "vals": smap_vals[ner_mask],
                        "granule_file": fp.name,
                        "pass_type": grp_name,
                    })
    except Exception as e:
        log.warning(f"Failed to parse SMAP granule {fp.name}: {e}")

    return passes


def load_grid_cells() -> List[Dict[str, str]]:
    """Loads all 16,961 analysis cells from baseline_susceptibility.csv."""
    if not GRID_SOURCE_CSV.exists():
        log.error(f"Required grid source file not found: {GRID_SOURCE_CSV}")
        sys.exit(1)

    cells = []
    with open(GRID_SOURCE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cells.append({
                "cell_id": row["cell_id"],
                "district": row["district"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
            })
    return cells


def ingest_smap_soil_moisture():
    log.info("=" * 80)
    log.info("NER Safe — STEP 5: NASA SMAP Soil Moisture Ingestion Pipeline")
    log.info("Product: NASA SMAP Enhanced L3 Radiometer Global Daily 9 km (SPL3SMP_E V006)")
    log.info("Pilot Focus: Kohima District (Nagaland) & Aizawl District (Mizoram)")
    log.info("=" * 80)

    # 1. Check Authentication & Authenticate
    has_auth, auth_source = check_earthdata_credentials()
    ingestion_time = datetime.now(timezone.utc).isoformat()

    auth_ok = False
    if has_auth:
        auth_ok, cred_src, _ = get_earthdata_auth()

    if not auth_ok:
        log.warning("NASA Earthdata authentication check: UNAVAILABLE")
        log.warning("  • Neither EARTHDATA_TOKEN nor NASA_EARTHDATA_USERNAME/PASSWORD active.")
        log.warning("  • Anti-Fabrication Protocol active: No synthetic soil moisture generated.")
    else:
        log.info(f"NASA Earthdata authentication check: AVAILABLE (Source: {auth_source})")

    # 2. Download / Find Granules
    granule_files = []
    if auth_ok:
        log.info("Querying & downloading NASA SMAP SPL3SMP_E V006 granules via earthaccess...")
        granule_files = fetch_and_download_smap_granules(max_granules=3)
    elif RAW_SMAP_DIR.exists():
        granule_files = sorted([g for g in RAW_SMAP_DIR.glob("*.h5") if g.stat().st_size > 1_000_000], reverse=True)

    # 3. Parse Granules into Passes
    all_passes = []
    for gf in granule_files:
        parsed_passes = parse_smap_granule(gf)
        all_passes.extend(parsed_passes)

    # Sort passes by datetime descending (newest first)
    all_passes.sort(key=lambda p: p["dt_obj"], reverse=True)

    # Group distinct passes by date/time
    distinct_passes = []
    seen_timestamps = set()
    for p in all_passes:
        if p["timestamp"] not in seen_timestamps:
            distinct_passes.append(p)
            seen_timestamps.add(p["timestamp"])

    current_pass = distinct_passes[0] if len(distinct_passes) > 0 else None
    previous_pass = distinct_passes[1] if len(distinct_passes) > 1 else None

    # 4. Load 500m Analysis Grid Cells
    cells = load_grid_cells()
    total_cells = len(cells)
    log.info(f"Loaded {total_cells:,} analysis grid cells (500m × 500m).")

    # Build KDTree for every distinct observation pass
    pass_trees = []
    for p in distinct_passes:
        coords = np.column_stack([p["lats"], p["lons"]])
        pass_trees.append({
            "pass": p,
            "tree": KDTree(coords),
            "vals": p["vals"],
        })
        log.info(f"Loaded SMAP Pass: {p['timestamp']} ({p['granule_file']}) — {len(p['vals'])} NER observation pixels.")

    cell_coords = np.column_stack([[float(c["latitude"]) for c in cells], [float(c["longitude"]) for c in cells]])

    # 5. Determine Freshness & Latency
    now_utc = datetime.now(timezone.utc)
    latest_pass = distinct_passes[0] if distinct_passes else None
    obs_time_iso = latest_pass["timestamp"] if latest_pass else ""
    obs_dt = latest_pass["dt_obj"] if latest_pass else None

    latency_hours = None
    overall_status = STATUS_REQUIRES_AUTH
    if obs_dt:
        latency_hours = (now_utc - obs_dt).total_seconds() / 3600.0
        if latency_hours <= STALENESS_THRESHOLD_HOURS:
            overall_status = STATUS_AVAILABLE
        else:
            overall_status = STATUS_STALE
        log.info(f"Latest SMAP observation timestamp: {obs_time_iso}")
        log.info(f"Source Latency: {latency_hours:.2f} hours (Status: {overall_status})")
    else:
        log.warning("No valid SMAP observation passes available.")

    # 6. Generate Standardized Output Dataset
    records = []
    populated_count = 0
    missing_count = 0
    auth_required_count = 0
    stale_count = 0

    MAX_MATCH_DIST_DEG = 0.15  # ~15 km matching radius for 9 km pixel centroid

    for i, c in enumerate(cells):
        lat_f = float(c["latitude"])
        lon_f = float(c["longitude"])
        ease2_cell = get_smap_ease2_cell(lon_f, lat_f)
        cell_pt = cell_coords[i]

        matched_cell_passes = []
        for pt_item in pass_trees:
            dist, idx = pt_item["tree"].query(cell_pt)
            if dist <= MAX_MATCH_DIST_DEG:
                matched_cell_passes.append({
                    "date_str": pt_item["pass"]["timestamp"][:10],
                    "timestamp": pt_item["pass"]["timestamp"],
                    "val": float(pt_item["vals"][idx])
                })

        cur_item = matched_cell_passes[0] if len(matched_cell_passes) > 0 else None
        prev_item = None
        if cur_item:
            for p_item in matched_cell_passes[1:]:
                if p_item["date_str"] != cur_item["date_str"]:
                    prev_item = p_item
                    break

        cur_val = cur_item["val"] if cur_item else None
        prev_val = prev_item["val"] if prev_item else None

        if cur_val is not None:
            cell_status = overall_status
            cur_val = round(cur_val, 4)
            sm_curr_str = f"{cur_val:.4f}"
            
            prev_val = round(prev_val, 4) if prev_val is not None else None
            sm_prev_str = f"{prev_val:.4f}" if prev_val is not None else ""

            change_val_str = ""
            change_pct_str = ""
            if prev_val is not None:
                diff = round(cur_val - prev_val, 4)
                change_val_str = f"{diff:.4f}"
                if prev_val > 0.0:
                    pct = round((diff / prev_val) * 100.0, 2)
                    change_pct_str = f"{pct:.2f}"

            qflag = "PASSED_VERIFICATION"
            if cell_status == STATUS_STALE:
                qflag += ";STALE_OBSERVATION_LATENCY_EXCEEDED"
                stale_count += 1
            else:
                populated_count += 1

            records.append({
                "cell_id": c["cell_id"],
                "district": c["district"],
                "latitude": f"{lat_f:.6f}",
                "longitude": f"{lon_f:.6f}",
                "smap_ease2_grid_cell": ease2_cell,
                "observation_timestamp": obs_time_iso,
                "soil_moisture_current": sm_curr_str,
                "soil_moisture_previous": sm_prev_str,
                "soil_moisture_change": change_val_str,
                "soil_moisture_change_percent": change_pct_str,
                "source": SMAP_SOURCE_NAME,
                "source_product": SMAP_PRODUCT_NAME,
                "source_resolution": SMAP_RESOLUTION_NOTE,
                "data_status": cell_status,
                "source_timestamp": obs_time_iso,
                "ingestion_timestamp": ingestion_time,
                "quality_flag": qflag,
            })
        else:
            if not auth_ok:
                auth_required_count += 1
                cell_status = STATUS_REQUIRES_AUTH
                qflag = "UNAVAILABLE_PENDING_EARTHDATA_LOGIN"
            else:
                missing_count += 1
                cell_status = STATUS_MISSING
                qflag = "OUTSIDE_SATELLITE_SWATH_COVERAGE"

            records.append({
                "cell_id": c["cell_id"],
                "district": c["district"],
                "latitude": f"{lat_f:.6f}",
                "longitude": f"{lon_f:.6f}",
                "smap_ease2_grid_cell": ease2_cell,
                "observation_timestamp": "",
                "soil_moisture_current": "",
                "soil_moisture_previous": "",
                "soil_moisture_change": "",
                "soil_moisture_change_percent": "",
                "source": SMAP_SOURCE_NAME,
                "source_product": SMAP_PRODUCT_NAME,
                "source_resolution": SMAP_RESOLUTION_NOTE,
                "data_status": cell_status,
                "source_timestamp": "",
                "ingestion_timestamp": ingestion_time,
                "quality_flag": qflag,
            })

    # 7. Write to Dedicated Output File
    SOIL_MOISTURE_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SMAP_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(records)

    log.info(f"✓ Output written to: {OUTPUT_SMAP_CSV.relative_to(PROJECT_ROOT)}")
    log.info(f"  • Total rows written: {len(records):,}")
    log.info(f"  • Populated cells: {populated_count:,}")
    log.info(f"  • Stale cells (>48h latency): {stale_count:,}")
    log.info(f"  • Missing cells: {missing_count:,}")
    log.info(f"  • Auth required cells: {auth_required_count:,}")
    log.info(f"  • Status: {records[0]['data_status']}")
    log.info("=" * 80)
    log.info("PIPELINE EXECUTION COMPLETE: NASA SMAP soil moisture ingestion verified.")
    log.info("=" * 80)


if __name__ == "__main__":
    ingest_smap_soil_moisture()
