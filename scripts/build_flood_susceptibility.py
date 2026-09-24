#!/usr/bin/env python3
"""
build_flood_susceptibility.py — Static Flash-Flood Susceptibility Index (FFSI)

Mirrors the structure and scientific-disclosure conventions of
build_baseline_susceptibility.py, but for flash-flood (not landslide)
static susceptibility, per PRD.md Sections 23, 24, 31-33.

Implements:
  A transparent, reproducible Flash-Flood Susceptibility Index (FFSI) from
  DEM-derived hydrology (HAND, flow accumulation, drainage density — from
  derive_hydrology.py / assign_grid_hydrology.py) combined with existing
  terrain morphometry (slope, TWI — from grid_terrain_features.csv).

Physical rationale (opposite polarity from landslide TSI on slope/HAND):
  - Low HAND (height above nearest drainage)  -> high flood susceptibility.
  - High flow accumulation (large catchment)  -> high flood susceptibility.
  - High TWI (wetness convergence)            -> high flood susceptibility.
  - Low slope (water ponds rather than sheds) -> high flood susceptibility.
  - High local drainage density               -> high flood susceptibility.

STRICT SCIENTIFIC RESTRICTIONS (PRD.md Section 0, 23, 24, 82):
  - This is a STATIC susceptibility index only. It is NOT a flood-depth,
    inundation-extent, or arrival-time model — no hydraulic routing is
    performed. PRD.md Section 24 explicitly forbids claiming flood depth
    without a validated hydraulic/hydrological basis.
  - No supervised classifier is trained; weights are declared heuristic,
    not AI-learned (no verified flood-event inventory exists yet to fit one).
  - Cells with missing hydrology/terrain inputs (DEM coverage gaps at
    district-boundary edges) are reported as INSUFFICIENT_DATA, never
    defaulted to a fabricated score of 0.

Output:
  data/ml/flood_susceptibility.csv
"""

import csv
import logging
import sys
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
HISTORICAL_DIR = DATA_DIR / "historical"
ML_DIR = DATA_DIR / "ml"

TERRAIN_CSV = HISTORICAL_DIR / "grid_terrain_features.csv"
HYDROLOGY_CSV = ML_DIR / "grid_hydrology_features.csv"
OUTPUT_CSV = ML_DIR / "flood_susceptibility.csv"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("build_flood_susceptibility")

# Prototype policy weights (Sum = 1.0). Documented, heuristic — NOT ML-learned.
WEIGHTS = {
    "hand": 0.35,
    "flow_accumulation": 0.25,
    "twi": 0.20,
    "slope": 0.10,
    "drainage_density": 0.10,
}

# Normalization reference constants (documented prototype parameters).
HAND_SATURATION_M = 30.0       # HAND >= this -> flood factor floors to 0
FLOWACC_LOG_SATURATION = 6.0   # log10(flow_accumulation_max+1) >= this -> factor 1.0
TWI_FLOOR, TWI_SATURATION = 4.0, 8.0
SLOPE_SATURATION_DEG = 30.0    # slope >= this -> ponding factor floors to 0
DRAINAGE_DENSITY_SATURATION = 0.30


def normalize_factors(hand_min, flow_acc_max, twi_mean, slope_mean, drainage_density):
    hand_factor = float(np.clip(1.0 - (hand_min / HAND_SATURATION_M), 0.0, 1.0))
    flowacc_factor = float(np.clip(np.log10(flow_acc_max + 1.0) / FLOWACC_LOG_SATURATION, 0.0, 1.0))
    twi_factor = float(np.clip((twi_mean - TWI_FLOOR) / (TWI_SATURATION - TWI_FLOOR), 0.0, 1.0))
    slope_factor = float(np.clip(1.0 - (slope_mean / SLOPE_SATURATION_DEG), 0.0, 1.0))
    dd_factor = float(np.clip(drainage_density / DRAINAGE_DENSITY_SATURATION, 0.0, 1.0))
    return hand_factor, flowacc_factor, twi_factor, slope_factor, dd_factor


def compute_ffsi(hand_factor, flowacc_factor, twi_factor, slope_factor, dd_factor):
    score = 100.0 * (
        WEIGHTS["hand"] * hand_factor +
        WEIGHTS["flow_accumulation"] * flowacc_factor +
        WEIGHTS["twi"] * twi_factor +
        WEIGHTS["slope"] * slope_factor +
        WEIGHTS["drainage_density"] * dd_factor
    )

    if score < 30.0:
        ffsi_class = "VERY_LOW"
    elif score < 50.0:
        ffsi_class = "LOW"
    elif score < 70.0:
        ffsi_class = "MODERATE"
    elif score < 85.0:
        ffsi_class = "HIGH"
    else:
        ffsi_class = "VERY_HIGH"

    contributors = {
        "hand": WEIGHTS["hand"] * hand_factor,
        "flow_accumulation": WEIGHTS["flow_accumulation"] * flowacc_factor,
        "twi": WEIGHTS["twi"] * twi_factor,
        "slope": WEIGHTS["slope"] * slope_factor,
        "drainage_density": WEIGHTS["drainage_density"] * dd_factor,
    }
    top_factor = max(contributors, key=contributors.get)
    primary_contributor = {
        "hand": "Low elevation above nearest drainage (HAND)",
        "flow_accumulation": "Large upstream contributing catchment",
        "twi": "High topographic wetness convergence",
        "slope": "Low-gradient terrain favoring water ponding",
        "drainage_density": "High local drainage network density",
    }[top_factor]

    return round(score, 2), ffsi_class, primary_contributor


def main():
    log.info("=" * 75)
    log.info("NER Safe — Static Flash-Flood Susceptibility Index (FFSI)")
    log.info("=" * 75)

    if not TERRAIN_CSV.exists() or not HYDROLOGY_CSV.exists():
        log.error(f"Missing required input CSV(s). Expected:\n  {TERRAIN_CSV}\n  {HYDROLOGY_CSV}")
        log.error("Run scripts/derive_hydrology.py and scripts/assign_grid_hydrology.py first.")
        sys.exit(1)

    terrain = {}
    with open(TERRAIN_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            terrain[r["cell_id"]] = r

    hydrology = {}
    with open(HYDROLOGY_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            hydrology[r["cell_id"]] = r

    log.info(f"Loaded terrain for {len(terrain)} cells, hydrology for {len(hydrology)} cells")

    rows = []
    n_insufficient = 0
    for cell_id, t in terrain.items():
        h = hydrology.get(cell_id)
        district = t["district"]

        required = [t.get("slope_mean"), t.get("twi_mean")]
        if h:
            required += [h.get("hand_min"), h.get("flow_accumulation_max"), h.get("drainage_density")]
        missing = (h is None) or any(v is None or v == "" for v in required)

        if missing:
            n_insufficient += 1
            rows.append({
                "cell_id": cell_id, "district": district,
                "ffsi_score": "", "ffsi_class": "", "primary_contributor": "",
                "status": "INSUFFICIENT_DATA",
            })
            continue

        hand_factor, flowacc_factor, twi_factor, slope_factor, dd_factor = normalize_factors(
            hand_min=float(h["hand_min"]),
            flow_acc_max=float(h["flow_accumulation_max"]),
            twi_mean=float(t["twi_mean"]),
            slope_mean=float(t["slope_mean"]),
            drainage_density=float(h["drainage_density"]),
        )
        score, ffsi_class, primary_contributor = compute_ffsi(
            hand_factor, flowacc_factor, twi_factor, slope_factor, dd_factor
        )
        rows.append({
            "cell_id": cell_id, "district": district,
            "ffsi_score": score, "ffsi_class": ffsi_class,
            "primary_contributor": primary_contributor, "status": "AVAILABLE",
        })

    ML_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["cell_id", "district", "ffsi_score", "ffsi_class", "primary_contributor", "status"]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    log.info(f"[SUCCESS] Flood susceptibility written to {OUTPUT_CSV.relative_to(PROJECT_ROOT)}")
    log.info(f"          Total cells: {len(rows)} | AVAILABLE: {len(rows) - n_insufficient} | "
              f"INSUFFICIENT_DATA: {n_insufficient}")

    class_counts = {}
    for r in rows:
        if r["status"] == "AVAILABLE":
            class_counts[r["ffsi_class"]] = class_counts.get(r["ffsi_class"], 0) + 1
    log.info(f"          Class distribution: {class_counts}")


if __name__ == "__main__":
    main()
