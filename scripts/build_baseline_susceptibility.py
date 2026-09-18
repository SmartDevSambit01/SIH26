#!/usr/bin/env python3
"""
build_baseline_susceptibility.py — Terrain Susceptibility Baseline & PU Analysis

STEP 9A — Baseline Landslide Susceptibility Model and Positive-Unlabeled Analysis
NER Safe (SIH 2026)

Implements:
  1. Transparent, reproducible Terrain Susceptibility Index (TSI) based on verified
     geomorphometry (Copernicus DEM 30m: slope, curvature, TWI, relief).
  2. Positive-Unlabeled (PU) / Anomaly Analysis measuring multi-factor terrain
     similarity to the 11 verified historical landslide events.
  3. Spatial Block Partitioning (5 km x 5 km spatial blocks) to safeguard against
     spatial autocorrelation leakage in future ML iterations.
  4. Local terrain feature attribution for model explainability.

STRICT SCIENTIFIC RESTRICTIONS:
  - No conventional supervised binary classifier (XGBoost/RF) is trained.
  - No negative samples are fabricated. Unknown cells remain strictly UNKNOWN.
  - Weights are explicitly declared as heuristic/provisional, not AI-learned.
  - Output represents STATIC TERRAIN SUSCEPTIBILITY, NOT dynamic real-time risk.

Output:
  data/ml/baseline_susceptibility.csv
"""

import argparse
import csv
import json
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HISTORICAL_DIR = DATA_DIR / "historical"
ML_DIR = DATA_DIR / "ml"

TERRAIN_CSV = HISTORICAL_DIR / "grid_terrain_features.csv"
LANDSLIDES_CSV = HISTORICAL_DIR / "landslide_events_cleaned.csv"
FEATURE_DATASET_CSV = ML_DIR / "feature_dataset.csv"
OUTPUT_CSV = ML_DIR / "baseline_susceptibility.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("build_baseline_susceptibility")


# ═══════════════════════════════════════════════════════════════════════════════
#  Spatial Block Generator (5 km x 5 km Spatial Blocks)
# ═══════════════════════════════════════════════════════════════════════════════

def assign_spatial_block(lat, lon, district, block_size_deg=0.045):
    """
    Assign each cell to a discrete 5 km x 5 km spatial block (~0.045 degrees)
    to eliminate spatial autocorrelation leakage during spatial validation.
    """
    # Anchor origins for each district
    origin_lat = 25.0 if district == "Kohima" else 23.0
    origin_lon = 93.0 if district == "Kohima" else 92.0

    block_row = int(math.floor((lat - origin_lat) / block_size_deg))
    block_col = int(math.floor((lon - origin_lon) / block_size_deg))

    prefix = "BLK_KOH" if district == "Kohima" else "BLK_AIZ"
    return f"{prefix}_R{block_row:02d}_C{block_col:02d}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Heuristic Terrain Susceptibility Model (Transparent Multi-Criteria Scoring)
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_terrain_factors(slope_mean, slope_max, twi_mean, curvature_mean, elev_mean, elev_min, elev_max):
    """
    Normalizes raw physical factors into standard [0.0, 1.0] susceptibility contributors.
    Preserves physics:
      - Slope: Primary driving shear stress; non-linear sigmoid steepness response.
      - TWI: Topographic wetness index drives pore-water pressure convergence.
      - Curvature: Negative curvature (concave profile / hollows) accumulates runoff.
      - Relief Range: Local elevation relief (max - min) drives gravitational potential.
    """
    # 1. Slope Factor (0 to 1): Sigmoidal scaling centered around 25° (landscape median)
    s_eff = 0.6 * slope_mean + 0.4 * slope_max
    slope_factor = float(np.clip(s_eff / 45.0, 0.0, 1.0))

    # 2. Hydrological Convergence Factor (TWI)
    # TWI in region spans 4.0 to ~10.0; typical failure hollows have TWI >= 6.0
    twi_factor = float(np.clip((twi_mean - 4.0) / 4.0, 0.0, 1.0))

    # 3. Planform/Profile Concavity (Curvature)
    # Negative curvature = concave convergence (higher pore pressure accumulation)
    # Positive curvature = convex shedding ridge
    curv_factor = float(np.clip(0.5 - (curvature_mean * 1.5), 0.0, 1.0))

    # 4. Local Relief Factor (Elevation Range within 500m cell)
    relief = max(0.0, elev_max - elev_min)
    relief_factor = float(np.clip(relief / 250.0, 0.0, 1.0))

    return slope_factor, twi_factor, curv_factor, relief_factor


def compute_terrain_susceptibility(slope_factor, twi_factor, curv_factor, relief_factor, config="BALANCED"):
    """
    Compute heuristic Terrain Susceptibility Index (TSI) in [0.0, 100.0].
    Weights are PROVISIONAL and HEURISTIC, explicitly NOT machine-learned.
    """
    if config == "SLOPE_DOMINANT":
        w_slope, w_twi, w_curv, w_relief = 0.60, 0.20, 0.10, 0.10
    elif config == "HYDRO_DOMINANT":
        w_slope, w_twi, w_curv, w_relief = 0.35, 0.40, 0.15, 0.10
    else:  # BALANCED_GEOMORPHIC (Default)
        w_slope, w_twi, w_curv, w_relief = 0.45, 0.25, 0.15, 0.15

    score = 100.0 * (
        w_slope * slope_factor +
        w_twi * twi_factor +
        w_curv * curv_factor +
        w_relief * relief_factor
    )

    # Attribution breakdown for explainability
    contrib_slope = round((w_slope * slope_factor / (score / 100.0 + 1e-6)) * 100)
    contrib_twi = round((w_twi * twi_factor / (score / 100.0 + 1e-6)) * 100)
    contrib_curv = round((w_curv * curv_factor / (score / 100.0 + 1e-6)) * 100)
    contrib_relief = max(0, 100 - contrib_slope - contrib_twi - contrib_curv)

    explanation = f"Slope ({contrib_slope}%), TWI ({contrib_twi}%), Curvature ({contrib_curv}%), Relief ({contrib_relief}%)"

    # Classify into provisional visualization tiers
    if score < 30.0:
        tsi_class = "VERY_LOW"
    elif score < 50.0:
        tsi_class = "LOW"
    elif score < 70.0:
        tsi_class = "MODERATE"
    elif score < 85.0:
        tsi_class = "HIGH"
    else:
        tsi_class = "VERY_HIGH"

    return round(score, 2), tsi_class, explanation


# ═══════════════════════════════════════════════════════════════════════════════
#  Positive-Unlabeled (PU) / Anomaly Analysis Engine
# ═══════════════════════════════════════════════════════════════════════════════

def fit_pu_reference_profile(verified_events, terrain_dict):
    """
    Computes the multivariate empirical profile (mean and standard deviation)
    of the 11 verified positive landslide cells across physical factors.
    """
    pos_data = []
    for ev in verified_events:
        cid = ev["cell_id"]
        t = terrain_dict.get(cid)
        if t and t["slope_mean"] != "":
            pos_data.append([
                float(t["slope_mean"]),
                float(t["slope_max"]),
                float(t["twi_mean"]),
                float(t["curvature_mean"]),
                float(t["elevation_mean"]),
            ])

    pos_matrix = np.array(pos_data, dtype=np.float64)
    mu_pos = np.mean(pos_matrix, axis=0)
    sigma_pos = np.std(pos_matrix, axis=0)
    sigma_pos = np.where(sigma_pos < 1e-3, 1.0, sigma_pos)

    log.info(f"Fitted PU Reference Profile on N={len(pos_matrix)} verified events:")
    log.info(f"  • Mean Slope:     {mu_pos[0]:.2f}° (std: {sigma_pos[0]:.2f}°)")
    log.info(f"  • Mean Slope Max: {mu_pos[1]:.2f}° (std: {sigma_pos[1]:.2f}°)")
    log.info(f"  • Mean TWI:       {mu_pos[2]:.2f} (std: {sigma_pos[2]:.2f})")
    log.info(f"  • Mean Curvature: {mu_pos[3]:.3f} (std: {sigma_pos[3]:.3f})")
    log.info(f"  • Mean Elevation: {mu_pos[4]:.1f} m (std: {sigma_pos[4]:.1f} m)")
    return mu_pos, sigma_pos


def compute_pu_similarity(cell_vector, mu_pos, sigma_pos):
    """
    Compute standardized Euclidean distance and continuous similarity index [0.0, 1.0]
    between an unlabelled cell and the verified positive landslide cluster.
    """
    norm_diff = (cell_vector - mu_pos) / sigma_pos
    dist = float(np.sqrt(np.sum(norm_diff ** 2)))

    # Gaussian similarity kernel: similarity = exp(-0.5 * (d / 2.5)^2)
    similarity = float(np.exp(-0.5 * (dist / 2.5) ** 2))

    if similarity > 0.75:
        sim_class = "HIGH_TERRAIN_SIMILARITY"
    elif similarity > 0.40:
        sim_class = "MODERATE_TERRAIN_SIMILARITY"
    elif similarity > 0.15:
        sim_class = "LOW_TERRAIN_SIMILARITY"
    else:
        sim_class = "DISSIMILAR_TERRAIN"

    return round(similarity, 4), sim_class


# ═══════════════════════════════════════════════════════════════════════════════
#  Pipeline Execution
# ═══════════════════════════════════════════════════════════════════════════════

def run_baseline_pipeline(args):
    log.info("=" * 75)
    log.info("NER Safe — STEP 9A: Baseline Susceptibility & Positive-Unlabeled Model")
    log.info("=" * 75)

    # 1. Load raw terrain features
    terrain_dict = {}
    with open(TERRAIN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            terrain_dict[r["cell_id"]] = r
    log.info(f"Loaded terrain morphometry for {len(terrain_dict)} cells from {TERRAIN_CSV.name}")

    # 2. Load verified historical events
    verified_events = []
    with open(LANDSLIDES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if r.get("cell_id") and r.get("coordinate_status") == "VERIFIED":
                verified_events.append(r)
    log.info(f"Loaded {len(verified_events)} verified historical events with grid associations")

    # 3. Fit Positive-Unlabeled Reference Vector
    mu_pos, sigma_pos = fit_pu_reference_profile(verified_events, terrain_dict)

    event_cell_map = {e["cell_id"]: e["event_id"] for e in verified_events}

    # 4. Generate Baseline Susceptibility Dataset
    output_rows = []
    positive_count = 0
    unknown_count = 0
    class_tallies = {}

    for cid, t in terrain_dict.items():
        dist = t["district"]
        lat = float(t["lat"])
        lon = float(t["lon"])

        # Spatial block identifier (5 km x 5 km)
        block_id = assign_spatial_block(lat, lon, dist)

        # Ground truth label status
        if cid in event_cell_map:
            label_status = "CONFIRMED_POSITIVE"
            hist_event_id = event_cell_map[cid]
            positive_count += 1
        else:
            # Strictly UNKNOWN; no fabricated negatives
            label_status = "UNKNOWN"
            hist_event_id = ""
            unknown_count += 1

        # Check if terrain data is valid
        has_terrain = t.get("slope_mean") != "" and t.get("elevation_mean") != ""
        if has_terrain:
            s_mean = float(t["slope_mean"])
            s_max = float(t["slope_max"])
            e_mean = float(t["elevation_mean"])
            e_min = float(t["elevation_min"])
            e_max = float(t["elevation_max"])
            c_mean = float(t["curvature_mean"])
            tw_mean = float(t["twi_mean"])

            # Factors and score
            sf, tf, cf, rf = normalize_terrain_factors(s_mean, s_max, tw_mean, c_mean, e_mean, e_min, e_max)
            tsi_score, tsi_class, explanation = compute_terrain_susceptibility(sf, tf, cf, rf, config=args.config)

            # PU similarity
            cell_vec = np.array([s_mean, s_max, tw_mean, c_mean, e_mean], dtype=np.float64)
            pu_sim, pu_class = compute_pu_similarity(cell_vec, mu_pos, sigma_pos)
        else:
            # Border / NoData cell
            s_mean = ""
            e_mean = ""
            c_mean = ""
            tw_mean = ""
            tsi_score = ""
            tsi_class = "NODATA_BORDER"
            pu_sim = ""
            pu_class = "NODATA_BORDER"
            explanation = "NoData Terrain Boundary Cell"

        class_tallies[tsi_class] = class_tallies.get(tsi_class, 0) + 1

        output_rows.append([
            cid,
            dist,
            lat,
            lon,
            block_id,
            s_mean,
            e_mean,
            c_mean,
            tw_mean,
            tsi_score,
            tsi_class,
            pu_sim,
            pu_class,
            explanation,
            label_status,
            hist_event_id,
        ])

    # 5. Write Output CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    header = [
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

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(output_rows)

    log.info(f"✓ Saved baseline susceptibility dataset to: {OUTPUT_CSV}")
    log.info(f"  • Total Rows Written:         {len(output_rows):,}")
    log.info(f"  • Confirmed Positive Labels:  {positive_count}")
    log.info(f"  • Confirmed Negative Labels:  0 (Strictly zero fabricated negatives)")
    log.info(f"  • Unknown / Unlabeled Cells:  {unknown_count:,}")
    log.info(f"  • Susceptibility Classes:     {class_tallies}")
    log.info("=" * 75)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Build Baseline Terrain Susceptibility Model (NER Safe STEP 9A)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        choices=["BALANCED", "SLOPE_DOMINANT", "HYDRO_DOMINANT"],
        default="BALANCED",
        help="Heuristic weighting configuration (default: BALANCED)",
    )
    args = parser.parse_args()
    return run_baseline_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
