"""
assign_grid_terrain.py
======================
Maps 30 m morphometric terrain rasters to the 500 m NER Safe risk grid
via zonal statistics.

For each grid cell polygon the script extracts:
  - elevation_mean, elevation_min, elevation_max
  - slope_mean, slope_max
  - aspect_mean (circular mean: atan2(Σ sin θ, Σ cos θ))
  - curvature_mean
  - twi_mean

Output:
  data/historical/grid_terrain_features.csv

The CSV contains one row per grid cell with columns:
  cell_id, district, lat, lon, elevation_mean, elevation_min, elevation_max,
  slope_mean, slope_max, aspect_mean, curvature_mean, twi_mean
"""

import json
import sys
import time
from pathlib import Path
import numpy as np

try:
    import rasterio
    from rasterio.mask import mask as rasterio_mask
    from shapely.geometry import shape
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("        pip install rasterio shapely")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
TERRAIN_DIR = DATA_DIR / "terrain"
OUTPUT_CSV = DATA_DIR / "historical" / "grid_terrain_features.csv"

NODATA = -9999.0

DISTRICTS = [
    {
        "name": "Kohima",
        "prefix": "kohima",
        "grid_file": BOUNDARIES_DIR / "kohima_grid_500m.geojson",
    },
    {
        "name": "Aizawl",
        "prefix": "aizawl",
        "grid_file": BOUNDARIES_DIR / "aizawl_grid_500m.geojson",
    },
]

# Terrain layers to process (relative to TERRAIN_DIR)
LAYERS = ["dem", "slope", "aspect", "curvature", "twi"]


def circular_mean_degrees(angles_deg: np.ndarray) -> float:
    """
    Compute the circular mean of angles in degrees, correctly handling
    the 0°/360° boundary.

    Flat pixels (aspect == -1) are excluded.
    """
    valid = angles_deg[(angles_deg >= 0) & ~np.isnan(angles_deg)]
    if valid.size == 0:
        return -1.0
    rad = np.radians(valid)
    mean_sin = np.mean(np.sin(rad))
    mean_cos = np.mean(np.cos(rad))
    mean_angle = np.degrees(np.arctan2(mean_sin, mean_cos)) % 360.0
    return float(mean_angle)


def zonal_stats_for_cell(geom, raster_datasets: dict) -> dict:
    """
    Extract zonal statistics from pre-opened raster datasets
    for a single grid cell polygon.
    """
    stats = {}

    for layer_name, src in raster_datasets.items():
        try:
            # Mask the raster with the cell polygon
            out_image, _ = rasterio_mask(
                src, [geom], crop=True, filled=True, nodata=NODATA
            )
            data = out_image[0]
            valid = data[(data != NODATA) & ~np.isnan(data)]
        except Exception:
            valid = np.array([])

        if valid.size == 0:
            if layer_name == "dem":
                stats["elevation_mean"] = np.nan
                stats["elevation_min"] = np.nan
                stats["elevation_max"] = np.nan
            elif layer_name == "slope":
                stats["slope_mean"] = np.nan
                stats["slope_max"] = np.nan
            elif layer_name == "aspect":
                stats["aspect_mean"] = np.nan
            elif layer_name == "curvature":
                stats["curvature_mean"] = np.nan
            elif layer_name == "twi":
                stats["twi_mean"] = np.nan
            continue

        if layer_name == "dem":
            stats["elevation_mean"] = float(np.mean(valid))
            stats["elevation_min"] = float(np.min(valid))
            stats["elevation_max"] = float(np.max(valid))
        elif layer_name == "slope":
            stats["slope_mean"] = float(np.mean(valid))
            stats["slope_max"] = float(np.max(valid))
        elif layer_name == "aspect":
            stats["aspect_mean"] = circular_mean_degrees(valid)
        elif layer_name == "curvature":
            stats["curvature_mean"] = float(np.mean(valid))
        elif layer_name == "twi":
            stats["twi_mean"] = float(np.mean(valid))

    return stats


def process_district(dist_cfg: dict) -> list:
    """Process all grid cells for one district."""
    name = dist_cfg["name"]
    prefix = dist_cfg["prefix"]
    grid_path = dist_cfg["grid_file"]

    print(f"\n{'='*65}")
    print(f"  Processing zonal terrain statistics for {name} district")
    print(f"{'='*65}")
    t0 = time.time()

    # Validate grid file
    if not grid_path.exists():
        print(f"[ERROR] Grid file not found: {grid_path}")
        sys.exit(1)

    # Load grid cells
    with open(grid_path, "r", encoding="utf-8") as f:
        grid_data = json.load(f)
    features = grid_data["features"]
    print(f"  Loaded {len(features)} grid cells from {grid_path.name}")

    # Open all raster datasets for this district
    raster_paths = {}
    for layer in LAYERS:
        rpath = TERRAIN_DIR / f"{prefix}_{layer}.tif"
        if not rpath.exists():
            print(f"[ERROR] Raster not found: {rpath}")
            print(f"        Run scripts/derive_morphometry.py first.")
            sys.exit(1)
        raster_paths[layer] = rpath

    raster_datasets = {
        layer: rasterio.open(path) for layer, path in raster_paths.items()
    }

    try:
        rows = []
        report_interval = max(1, len(features) // 10)
        for i, feat in enumerate(features):
            props = feat["properties"]
            cell_id = props.get("cell_id", f"{prefix}_{i}")

            # Get centroid for lat/lon
            geom_shape = shape(feat["geometry"])
            centroid = geom_shape.centroid

            # The grid is in WGS84 but rasters are in UTM 46N
            # We need to reproject the cell geometry to UTM for masking
            from pyproj import Transformer
            from shapely.ops import transform as shapely_transform

            transformer = Transformer.from_crs(
                "EPSG:4326", "EPSG:32646", always_xy=True
            )
            geom_utm = shapely_transform(
                transformer.transform, geom_shape
            )

            stats = zonal_stats_for_cell(
                geom_utm.__geo_interface__, raster_datasets
            )

            row = {
                "cell_id": cell_id,
                "district": name,
                "lat": round(centroid.y, 6),
                "lon": round(centroid.x, 6),
                **stats,
            }
            rows.append(row)

            if (i + 1) % report_interval == 0:
                print(f"       Processed {i + 1}/{len(features)} cells...")

    finally:
        for src in raster_datasets.values():
            src.close()

    elapsed = time.time() - t0
    print(f"  [OK] {name}: {len(rows)} cells processed in {elapsed:.1f}s")

    return rows


def main():
    print("NER Safe — 500 m Grid Terrain Zonal Statistics")
    print(f"Output: {OUTPUT_CSV.relative_to(BASE_DIR)}\n")

    all_rows = []
    for dist_cfg in DISTRICTS:
        all_rows.extend(process_district(dist_cfg))

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "cell_id", "district", "lat", "lon",
        "elevation_mean", "elevation_min", "elevation_max",
        "slope_mean", "slope_max",
        "aspect_mean", "curvature_mean", "twi_mean",
    ]
    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(columns) + "\n")
        for row in all_rows:
            values = []
            for col in columns:
                val = row.get(col, "")
                if isinstance(val, float):
                    if np.isnan(val):
                        values.append("")
                    else:
                        values.append(f"{val:.6f}")
                else:
                    values.append(str(val))
            f.write(",".join(values) + "\n")

    print(f"\n{'='*65}")
    print(f"[SUCCESS] Grid terrain features written to {OUTPUT_CSV.relative_to(BASE_DIR)}")
    print(f"          Total cells: {len(all_rows)}")

    # Quick quality check
    nan_counts = {}
    for col in columns[4:]:
        n_nan = sum(1 for r in all_rows if isinstance(r.get(col), float)
                    and np.isnan(r.get(col, 0.0)))
        if n_nan > 0:
            nan_counts[col] = n_nan
    if nan_counts:
        print(f"          NaN counts by column: {nan_counts}")
    else:
        print(f"          No NaN values — full coverage achieved.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
