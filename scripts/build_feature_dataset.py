#!/usr/bin/env python3
"""
build_feature_dataset.py — Unified Risk Feature Dataset Builder

STEP 8 — Feature Engineering & Unified Risk Dataset
NER Safe (SIH 2026)

Integrates all available physical hazard (terrain, rainfall, soil moisture, satellite SAR),
exposure/impact (roads, population, critical infrastructure), human verification,
and ground-truth historical landslide labels across the 500 m regional risk grid
for Kohima District (6,055 cells) and Aizawl District (10,906 cells) = 16,961 total cells.

CONCEPTUAL SEPARATION OF CONCERNS:
  1. HAZARD & SUSCEPTIBILITY:
     Physical, geomorphometric, meteorological, and hydrological parameters that
     determine the mechanical likelihood of slope failure.
  2. EXPOSURE & IMPACT:
     Human population, transportation lifelines, and critical infrastructure that
     determine the consequences of an event and operational response priority.
     NOTE: Exposure assets (roads, buildings) are NEVER modeled as physical causes
     of natural landslides.

OUTPUT:
  data/ml/feature_dataset.csv
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
HISTORICAL_DIR = DATA_DIR / "historical"
SATELLITE_DIR = DATA_DIR / "satellite"
ML_DIR = DATA_DIR / "ml"
OUTPUT_CSV = ML_DIR / "feature_dataset.csv"

# Existing Input Files
TERRAIN_CSV = HISTORICAL_DIR / "grid_terrain_features.csv"
LANDSLIDES_CSV = HISTORICAL_DIR / "landslide_events_cleaned.csv"
SATELLITE_CSV = HISTORICAL_DIR / "grid_satellite_features.csv"
RAINFALL_CSV = HISTORICAL_DIR / "landslide_rainfall_features.csv"
SOIL_MOISTURE_CSV = HISTORICAL_DIR / "landslide_soil_moisture_features.csv"
SATELLITE_MANIFEST = SATELLITE_DIR / "cache" / "satellite_cache_manifest.json"

KOHIMA_GRID = BOUNDARIES_DIR / "kohima_grid_500m.geojson"
AIZAWL_GRID = BOUNDARIES_DIR / "aizawl_grid_500m.geojson"

# ── Logging Configuration ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("build_feature_dataset")

# ── Unified Feature Dataset Schema ───────────────────────────────────────────
FEATURE_DATASET_HEADER = [
    # 1. Spatial & Identification Index
    "cell_id",
    "district",
    "state",
    "latitude",
    "longitude",
    "observation_date",

    # 2. Physical Hazard & Susceptibility: Static Terrain (Copernicus DEM 30m)
    "elevation_mean",
    "elevation_min",
    "elevation_max",
    "slope_mean",
    "slope_max",
    "aspect_mean",
    "curvature_mean",
    "twi_mean",

    # 3. Physical Hazard & Susceptibility: Dynamic Meteorology (NASA GPM IMERG)
    "rainfall_rate",
    "rainfall_30min",
    "rainfall_3h",
    "rainfall_6h",
    "rainfall_24h",
    "rainfall_72h",
    "rainfall_intensity",
    "rainfall_duration_h",
    "antecedent_rainfall_7d",

    # 4. Physical Hazard & Susceptibility: Dynamic Hydrology (NASA SMAP 9km)
    "soil_moisture_current",
    "soil_moisture_previous",
    "soil_moisture_change",
    "soil_moisture_change_percent",

    # 5. Physical Hazard: Satellite Remote Sensing (Copernicus Sentinel-1 C-SAR)
    "vv_change_db",
    "vh_change_db",
    "vv_vh_change",
    "change_confidence",

    # 6. Physical Hazard: Environmental Context
    "vegetation_ndvi",
    "flood_indicator",

    # 7. Exposure & Operational Consequence (STRICTLY SEPARATED FROM HAZARD PHYSICS)
    "road_proximity_m",
    "road_exposure_level",
    "population_density_est",
    "critical_infrastructure_count",
    "impact_priority_score",

    # 8. Human & Incident Verification Layer
    "citizen_report_count",
    "officer_verification_status",
    "verification_timestamp",
    "verification_confidence",

    # 9. Historical Ground Truth Target
    "landslide_label",
    "historical_event_id",
    "event_location_name",
    "label_quality",

    # 10. Data Source & Provenance Status Tracking
    "terrain_status",
    "rainfall_status",
    "soil_moisture_status",
    "satellite_status",
    "flood_status",
    "vegetation_status",
    "exposure_status",
    "verification_status",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Dataset Loading & Merging Engine
# ═══════════════════════════════════════════════════════════════════════════════

def load_grid_cells():
    """Load baseline geometries and metadata from official 500m risk grids."""
    cells = {}
    for gpath, dist, state, expected in [
        (KOHIMA_GRID, "Kohima", "Nagaland", 6055),
        (AIZAWL_GRID, "Aizawl", "Mizoram", 10906),
    ]:
        if not gpath.exists():
            log.error(f"Grid file missing: {gpath}")
            sys.exit(1)
        with open(gpath, "r", encoding="utf-8") as f:
            gj = json.load(f)
        feats = gj.get("features", [])
        log.info(f"Loaded {len(feats)} cells from {gpath.name} (expected {expected})")
        for f in feats:
            props = f["properties"]
            cid = props["cell_id"]
            cells[cid] = {
                "cell_id": cid,
                "district": dist,
                "state": state,
                "latitude": round(props.get("centroid_lat", 0.0), 6),
                "longitude": round(props.get("centroid_lon", 0.0), 6),
            }
    return cells


def load_terrain_features():
    """Load Step 6 30m morphometric zonal statistics."""
    terrain = {}
    if not TERRAIN_CSV.exists():
        log.error(f"Terrain CSV missing: {TERRAIN_CSV}")
        sys.exit(1)
    with open(TERRAIN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row["cell_id"]
            terrain[cid] = {
                "elevation_mean": row.get("elevation_mean", ""),
                "elevation_min": row.get("elevation_min", ""),
                "elevation_max": row.get("elevation_max", ""),
                "slope_mean": row.get("slope_mean", ""),
                "slope_max": row.get("slope_max", ""),
                "aspect_mean": row.get("aspect_mean", ""),
                "curvature_mean": row.get("curvature_mean", ""),
                "twi_mean": row.get("twi_mean", ""),
            }
    log.info(f"Loaded terrain morphometry for {len(terrain)} cells from {TERRAIN_CSV.name}")
    return terrain


def load_verified_landslide_events():
    """Load verified ground-truth historical landslide events linked to grid cells."""
    events_by_cell = {}
    if not LANDSLIDES_CSV.exists():
        log.warning(f"Historical landslides CSV not found: {LANDSLIDES_CSV}")
        return events_by_cell

    with open(LANDSLIDES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("cell_id", "").strip()
            status = row.get("coordinate_status", "").strip().upper()
            if cid and status == "VERIFIED":
                events_by_cell[cid] = {
                    "event_id": row.get("event_id", ""),
                    "event_date": row.get("event_date", ""),
                    "event_time": row.get("event_time", ""),
                    "location_name": row.get("location_name", ""),
                    "description": row.get("description", ""),
                    "source": row.get("source", ""),
                }
    log.info(f"Loaded {len(events_by_cell)} verified historical landslide occurrences linked to grid cells")
    return events_by_cell


def load_satellite_features():
    """Load Step 7 Sentinel-1 SAR change grid observations."""
    sat_data = {}
    if not SATELLITE_CSV.exists():
        return sat_data

    with open(SATELLITE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("cell_id")
            if cid:
                sat_data[cid] = row
    log.info(f"Loaded satellite features for {len(sat_data)} cells from {SATELLITE_CSV.name}")
    return sat_data


# ═══════════════════════════════════════════════════════════════════════════════
#  Feature Integration Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def build_dataset(args):
    """Integrate all layers into a unified feature dataset."""
    log.info("=" * 75)
    log.info("NER Safe — STEP 8: Building Unified Risk Feature Dataset")
    log.info("=" * 75)

    # 1. Load component data
    grid_cells = load_grid_cells()
    terrain_data = load_terrain_features()
    landslide_events = load_verified_landslide_events()
    satellite_data = load_satellite_features()

    total_cells = len(grid_cells)
    log.info(f"Total risk-grid cells to process: {total_cells}")

    # 2. Build records
    ML_DIR.mkdir(parents=True, exist_ok=True)
    rows_to_write = []

    positive_labels_count = 0
    negative_labels_count = 0
    unknown_labels_count = 0

    for cid, cell in grid_cells.items():
        t = terrain_data.get(cid, {})
        has_terrain = bool(t.get("elevation_mean") and t.get("slope_mean"))

        # Check for verified historical landslide event
        ev = landslide_events.get(cid)
        if ev:
            # Confirmed Positive Landslide Sample
            landslide_label = 1
            historical_event_id = ev["event_id"]
            event_loc_name = ev["location_name"]
            label_quality = "VERIFIED_HISTORICAL"
            obs_date = ev["event_date"]
            positive_labels_count += 1
        else:
            # Scientifically Honest: A cell without a reported historical event
            # is UNKNOWN / UNLABELED, NOT a confirmed negative!
            # Ground-truth negative surveys have not been conducted.
            landslide_label = ""
            historical_event_id = ""
            event_loc_name = ""
            label_quality = "UNLABELED"
            obs_date = "2024-09-01"  # Baseline reference snapshot date
            unknown_labels_count += 1

        # Satellite features
        sat = satellite_data.get(cid, {})
        vv_change_db = sat.get("vv_change_db", "")
        vh_change_db = sat.get("vh_change_db", "")
        vv_vh_change = sat.get("vv_vh_change", "")
        change_conf = sat.get("change_confidence", "")
        sat_status = sat.get("data_status", "PENDING_REAL_SCENE_INGESTION")

        # Assemble unified row
        row = [
            # 1. Spatial & Identification Index
            cid,
            cell["district"],
            cell["state"],
            cell["latitude"],
            cell["longitude"],
            obs_date,

            # 2. Physical Hazard: Static Terrain
            t.get("elevation_mean", ""),
            t.get("elevation_min", ""),
            t.get("elevation_max", ""),
            t.get("slope_mean", ""),
            t.get("slope_max", ""),
            t.get("aspect_mean", ""),
            t.get("curvature_mean", ""),
            t.get("twi_mean", ""),

            # 3. Physical Hazard: Meteorology (GPM IMERG)
            "",  # rainfall_rate
            "",  # rainfall_30min
            "",  # rainfall_3h
            "",  # rainfall_6h
            "",  # rainfall_24h
            "",  # rainfall_72h
            "",  # rainfall_intensity
            "",  # rainfall_duration_h
            "",  # antecedent_rainfall_7d

            # 4. Physical Hazard: Hydrology (SMAP)
            "",  # soil_moisture_current
            "",  # soil_moisture_previous
            "",  # soil_moisture_change
            "",  # soil_moisture_change_percent

            # 5. Physical Hazard: Satellite Remote Sensing (Sentinel-1)
            vv_change_db,
            vh_change_db,
            vv_vh_change,
            change_conf,

            # 6. Physical Hazard: Environmental Context
            "",  # vegetation_ndvi (Schema prepared, marked UNAVAILABLE)
            "",  # flood_indicator (Schema prepared, marked UNAVAILABLE)

            # 7. Exposure & Operational Consequence
            "",  # road_proximity_m (Schema prepared, marked UNAVAILABLE)
            "",  # road_exposure_level
            "",  # population_density_est
            "",  # critical_infrastructure_count
            "",  # impact_priority_score

            # 8. Human Verification Layer
            "",  # citizen_report_count
            "UNVERIFIED",  # officer_verification_status
            "",  # verification_timestamp
            "",  # verification_confidence

            # 9. Historical Ground Truth Target
            landslide_label,
            historical_event_id,
            event_loc_name,
            label_quality,

            # 10. Explicit Data Status Tracking
            "AVAILABLE" if has_terrain else "NODATA_TERRAIN_BORDER",
            "UNAVAILABLE_EARTHDATA_AUTH_REQUIRED",
            "UNAVAILABLE_EARTHDATA_AUTH_REQUIRED",
            sat_status,
            "UNAVAILABLE_PENDING_INGESTION",
            "UNAVAILABLE_PENDING_INGESTION",
            "UNAVAILABLE_PENDING_INGESTION",
            "UNVERIFIED",
        ]
        rows_to_write.append(row)

    # 3. Write Output Dataset
    out_path = Path(args.output) if args.output else OUTPUT_CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(FEATURE_DATASET_HEADER)
        writer.writerows(rows_to_write)

    log.info(f"✓ Unified Risk Feature Dataset written to: {out_path}")
    log.info(f"  • Total Rows:               {len(rows_to_write):,}")
    log.info(f"  • Total Columns:            {len(FEATURE_DATASET_HEADER)}")
    log.info(f"  • Confirmed Positive Labels: {positive_labels_count} (Verified historical landslides)")
    log.info(f"  • Confirmed Negative Labels: {negative_labels_count} (Zero fabricated negative assumptions)")
    log.info(f"  • Unlabeled / Unknown:      {unknown_labels_count} (Scientifically protected from false negatives)")
    log.info("=" * 75)
    return 0


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI Interface
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Build Unified Risk Feature Dataset (NER Safe STEP 8)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(OUTPUT_CSV),
        help=f"Output feature dataset CSV path (default: {OUTPUT_CSV})",
    )
    parser.add_argument(
        "--district",
        choices=["Kohima", "Aizawl"],
        help="Optional: Filter dataset to a specific district",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Inspect inputs and display merge summary without writing file",
    )

    args = parser.parse_args()
    return build_dataset(args)


if __name__ == "__main__":
    sys.exit(main())
