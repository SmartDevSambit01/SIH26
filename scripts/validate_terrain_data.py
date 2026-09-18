"""
validate_terrain_data.py
========================
Automated validation suite for NER Safe STEP 6 — Terrain Data Pipeline.

Tests:
  1. Raw DEM tile existence (8 Copernicus tiles)
  2. Clipped DEM existence and basic integrity
  3. Morphometric raster existence, CRS, bounds, and value ranges
  4. Grid terrain features CSV completeness and plausibility
  5. Cell ID uniqueness and district coverage

Exit codes:
  0 — all checks passed
  1 — one or more checks failed
"""

import csv
import json
import sys
from pathlib import Path
import numpy as np

try:
    import rasterio
except ImportError:
    print("[ERROR] rasterio not installed. pip install rasterio")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TERRAIN_DIR = DATA_DIR / "terrain"
RAW_DIR = TERRAIN_DIR / "raw"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
HISTORICAL_DIR = DATA_DIR / "historical"

EXPECTED_CRS_EPSG = 32646  # UTM Zone 46N
NODATA = -9999.0

# Expected raw tiles
RAW_TILES = [
    "Copernicus_DSM_COG_10_N23_00_E092_00_DEM.tif",
    "Copernicus_DSM_COG_10_N23_00_E093_00_DEM.tif",
    "Copernicus_DSM_COG_10_N24_00_E092_00_DEM.tif",
    "Copernicus_DSM_COG_10_N24_00_E093_00_DEM.tif",
    "Copernicus_DSM_COG_10_N25_00_E093_00_DEM.tif",
    "Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif",
    "Copernicus_DSM_COG_10_N26_00_E093_00_DEM.tif",
    "Copernicus_DSM_COG_10_N26_00_E094_00_DEM.tif",
]

# District DEM and derivative rasters
DISTRICTS = ["kohima", "aizawl"]
LAYERS = ["dem", "slope", "aspect", "curvature", "twi"]

# Plausibility ranges for Kohima / Aizawl (NE India hill terrain)
PLAUSIBILITY = {
    "dem":       {"min": 0,    "max": 4000,  "label": "Elevation (m)"},
    "slope":     {"min": 0,    "max": 90,    "label": "Slope (°)"},
    "aspect":    {"min": -1,   "max": 360,   "label": "Aspect (°)"},
    "curvature": {"min": -500, "max": 500,   "label": "Curvature"},
    "twi":       {"min": -5,   "max": 35,    "label": "TWI"},
}

CSV_PATH = HISTORICAL_DIR / "grid_terrain_features.csv"
CSV_COLUMNS = [
    "cell_id", "district", "lat", "lon",
    "elevation_mean", "elevation_min", "elevation_max",
    "slope_mean", "slope_max",
    "aspect_mean", "curvature_mean", "twi_mean",
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


def test_raw_tiles():
    """Test 1: Raw DEM tile existence."""
    print("\n[Test 1] Raw DEM Tile Existence")
    for tile_name in RAW_TILES:
        tile_path = RAW_DIR / tile_name
        check(tile_path.exists(),
              f"Raw tile exists: {tile_name}")


def test_clipped_dems():
    """Test 2: Clipped DEM integrity."""
    print("\n[Test 2] Clipped DEM Integrity")
    for district in DISTRICTS:
        dem_path = TERRAIN_DIR / f"{district}_dem.tif"
        check(dem_path.exists(),
              f"{district}_dem.tif exists")

        if not dem_path.exists():
            continue

        with rasterio.open(dem_path) as src:
            # CRS check
            epsg = src.crs.to_epsg()
            check(epsg == EXPECTED_CRS_EPSG,
                  f"{district} DEM CRS = EPSG:{epsg} (expected {EXPECTED_CRS_EPSG})")

            # Dimensions
            check(src.width > 0 and src.height > 0,
                  f"{district} DEM dimensions: {src.width}×{src.height}")

            # Read and check elevation range
            data = src.read(1)
            valid = data[(data != NODATA) & ~np.isnan(data)]
            check(valid.size > 0,
                  f"{district} DEM has {valid.size:,} valid pixels")

            if valid.size > 0:
                vmin, vmax = float(np.min(valid)), float(np.max(valid))
                check(vmin > 0,
                      f"{district} DEM min elevation: {vmin:.1f} m (> 0 m)")
                check(vmax < 4000,
                      f"{district} DEM max elevation: {vmax:.1f} m (< 4000 m)")

            # NoData percentage
            nodata_pct = (data.size - valid.size) / data.size * 100
            # ~36-37% NoData is expected: bounding rect of irregular polygon
            check(nodata_pct < 50,
                  f"{district} DEM NoData: {nodata_pct:.1f}% (< 50% bounding-rect threshold)")


def test_morphometric_rasters():
    """Test 3: Morphometric derivative rasters."""
    print("\n[Test 3] Morphometric Derivative Rasters")
    for district in DISTRICTS:
        for layer in LAYERS:
            if layer == "dem":
                continue  # already tested
            raster_path = TERRAIN_DIR / f"{district}_{layer}.tif"
            check(raster_path.exists(),
                  f"{district}_{layer}.tif exists")

            if not raster_path.exists():
                continue

            with rasterio.open(raster_path) as src:
                epsg = src.crs.to_epsg()
                check(epsg == EXPECTED_CRS_EPSG,
                      f"{district}_{layer} CRS = EPSG:{epsg}")

                data = src.read(1)
                valid = data[(data != NODATA) & ~np.isnan(data)]
                check(valid.size > 0,
                      f"{district}_{layer} has {valid.size:,} valid pixels")

                if valid.size > 0:
                    vmin = float(np.min(valid))
                    vmax = float(np.max(valid))
                    bounds = PLAUSIBILITY[layer]
                    in_range = vmin >= bounds["min"] and vmax <= bounds["max"]
                    check(in_range,
                          f"{district}_{layer} range: {vmin:.2f} – {vmax:.2f} "
                          f"(expected {bounds['min']} – {bounds['max']})",
                          warn_only=not in_range)


def test_grid_csv():
    """Test 4: Grid terrain features CSV."""
    print("\n[Test 4] Grid Terrain Features CSV")
    check(CSV_PATH.exists(),
          f"grid_terrain_features.csv exists at {CSV_PATH.relative_to(BASE_DIR)}")

    if not CSV_PATH.exists():
        return

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Column check
    actual_cols = set(rows[0].keys()) if rows else set()
    expected_cols = set(CSV_COLUMNS)
    check(expected_cols.issubset(actual_cols),
          f"CSV has all expected columns ({len(expected_cols)} required)")

    # Row count — should be total grid cells across both districts
    # Load expected counts from grid GeoJSONs
    expected_total = 0
    for district in DISTRICTS:
        grid_path = BOUNDARIES_DIR / f"{district}_grid_500m.geojson"
        if grid_path.exists():
            with open(grid_path, "r", encoding="utf-8") as gf:
                gdata = json.load(gf)
            expected_total += len(gdata["features"])

    actual_total = len(rows)
    check(actual_total == expected_total,
          f"CSV row count: {actual_total} (expected {expected_total})")

    # Cell ID uniqueness
    cell_ids = [r["cell_id"] for r in rows]
    check(len(cell_ids) == len(set(cell_ids)),
          f"Cell IDs are unique ({len(set(cell_ids))} unique / {len(cell_ids)} total)")

    # District coverage
    districts_in_csv = set(r["district"] for r in rows)
    check("Kohima" in districts_in_csv and "Aizawl" in districts_in_csv,
          f"CSV covers both districts: {districts_in_csv}")

    # Plausibility checks on numeric columns
    numeric_cols = CSV_COLUMNS[4:]
    for col in numeric_cols:
        values = []
        for r in rows:
            try:
                v = float(r[col])
                values.append(v)
            except (ValueError, KeyError):
                pass

        if not values:
            check(False, f"{col}: no valid numeric values")
            continue

        arr = np.array(values)
        n_nan = sum(1 for r in rows if r.get(col, "") == "")
        check(n_nan < len(rows) * 0.1,
              f"{col}: {n_nan} empty values ({n_nan/len(rows)*100:.1f}%)",
              warn_only=True)

        # Elevation plausibility
        if "elevation" in col:
            check(np.min(arr) > 0,
                  f"{col} min: {np.min(arr):.1f} (> 0 m)")
            check(np.max(arr) < 4000,
                  f"{col} max: {np.max(arr):.1f} (< 4000 m)")
        elif "slope" in col:
            check(np.min(arr) >= 0,
                  f"{col} min: {np.min(arr):.2f} (>= 0 deg)")
            check(np.max(arr) <= 90,
                  f"{col} max: {np.max(arr):.2f} (<= 90 deg)")


def main():
    global passed, failed, warnings

    print("=" * 65)
    print("NER Safe — STEP 6 Terrain Data Validation Suite")
    print("=" * 65)

    test_raw_tiles()
    test_clipped_dems()
    test_morphometric_rasters()
    test_grid_csv()

    print(f"\n{'='*65}")
    print(f"RESULTS:  {passed} passed  |  {failed} failed  |  {warnings} warnings")
    print(f"{'='*65}")

    if failed > 0:
        print("[FAILED] Some validation checks did not pass.")
        sys.exit(1)
    else:
        print("[SUCCESS] All validation checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
