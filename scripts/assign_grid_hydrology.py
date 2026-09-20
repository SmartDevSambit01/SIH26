"""
assign_grid_hydrology.py
=========================
Maps 30 m DEM-derived hydrology rasters (derive_hydrology.py output) to the
500 m NER Safe risk grid via zonal statistics, mirroring the pattern used by
assign_grid_terrain.py.

For each grid cell polygon the script extracts:
  - flow_accumulation_max  (peak D8 contributing cell count within the cell)
  - drainage_density       (fraction of 30 m sub-pixels classified as stream,
                             i.e. stream-pixel-count / total-pixel-count — a
                             standard raster-based drainage-density proxy)
  - distance_to_drainage_m (mean distance to nearest stream cell, meters)
  - hand_mean, hand_min    (Height Above Nearest Drainage, meters)

Output:
  data/ml/grid_hydrology_features.csv

The CSV contains one row per grid cell with columns:
  cell_id, district, flow_accumulation_max, drainage_density,
  distance_to_drainage_m, hand_mean, hand_min
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
    from shapely.ops import transform as shapely_transform
    from pyproj import Transformer
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("        pip install rasterio shapely pyproj")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
TERRAIN_DIR = DATA_DIR / "terrain"
ML_DIR = DATA_DIR / "ml"
OUTPUT_CSV = ML_DIR / "grid_hydrology_features.csv"

NODATA = -9999.0

DISTRICTS = [
    {"name": "Kohima", "prefix": "kohima", "grid_file": BOUNDARIES_DIR / "kohima_grid_500m.geojson"},
    {"name": "Aizawl", "prefix": "aizawl", "grid_file": BOUNDARIES_DIR / "aizawl_grid_500m.geojson"},
]

LAYERS = ["flowacc", "stream", "dist2drain", "hand"]

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)


def zonal_stats_for_cell(geom, raster_datasets: dict) -> dict:
    stats = {}
    for layer_name, src in raster_datasets.items():
        try:
            # Use each raster's own nodata value (the stream mask is uint8/255,
            # not the float -9999 used by the other float32 layers) — passing
            # the wrong dtype's nodata into rasterio_mask silently corrupts it.
            src_nodata = src.nodata
            out_image, _ = rasterio_mask(src, [geom], crop=True, filled=True, nodata=src_nodata)
            data = out_image[0]
            valid = data[(data != src_nodata) & ~np.isnan(data.astype(np.float64))]
        except Exception:
            valid = np.array([])

        if layer_name == "flowacc":
            stats["flow_accumulation_max"] = float(np.max(valid)) if valid.size else np.nan
        elif layer_name == "stream":
            # stream raster is 0/1 (255 = nodata, excluded above); mean == pixel fraction
            stats["drainage_density"] = float(np.mean(valid)) if valid.size else np.nan
        elif layer_name == "dist2drain":
            stats["distance_to_drainage_m"] = float(np.mean(valid)) if valid.size else np.nan
        elif layer_name == "hand":
            stats["hand_mean"] = float(np.mean(valid)) if valid.size else np.nan
            stats["hand_min"] = float(np.min(valid)) if valid.size else np.nan
    return stats


def process_district(dist_cfg: dict) -> list:
    name = dist_cfg["name"]
    prefix = dist_cfg["prefix"]
    grid_path = dist_cfg["grid_file"]

    print(f"\n{'='*65}")
    print(f"  Processing zonal hydrology statistics for {name} district")
    print(f"{'='*65}")
    t0 = time.time()

    if not grid_path.exists():
        print(f"[ERROR] Grid file not found: {grid_path}")
        sys.exit(1)

    with open(grid_path, "r", encoding="utf-8") as f:
        grid_data = json.load(f)
    features = grid_data["features"]
    print(f"  Loaded {len(features)} grid cells from {grid_path.name}")

    raster_paths = {}
    for layer in LAYERS:
        rpath = TERRAIN_DIR / f"{prefix}_{layer}.tif"
        if not rpath.exists():
            print(f"[ERROR] Raster not found: {rpath}")
            print(f"        Run scripts/derive_hydrology.py first.")
            sys.exit(1)
        raster_paths[layer] = rpath

    raster_datasets = {layer: rasterio.open(path) for layer, path in raster_paths.items()}

    try:
        rows = []
        report_interval = max(1, len(features) // 10)
        for i, feat in enumerate(features):
            props = feat["properties"]
            cell_id = props.get("cell_id", f"{prefix}_{i}")

            geom_shape = shape(feat["geometry"])
            geom_utm = shapely_transform(TRANSFORMER.transform, geom_shape)

            stats = zonal_stats_for_cell(geom_utm.__geo_interface__, raster_datasets)
            rows.append({"cell_id": cell_id, "district": name, **stats})

            if (i + 1) % report_interval == 0:
                print(f"       Processed {i + 1}/{len(features)} cells...")
    finally:
        for src in raster_datasets.values():
            src.close()

    elapsed = time.time() - t0
    print(f"  [OK] {name}: {len(rows)} cells processed in {elapsed:.1f}s")
    return rows


def main():
    print("NER Safe — 500 m Grid Hydrology Zonal Statistics")
    print(f"Output: {OUTPUT_CSV.relative_to(BASE_DIR)}\n")

    all_rows = []
    for dist_cfg in DISTRICTS:
        all_rows.extend(process_district(dist_cfg))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    columns = ["cell_id", "district", "flow_accumulation_max", "drainage_density",
               "distance_to_drainage_m", "hand_mean", "hand_min"]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(columns) + "\n")
        for row in all_rows:
            values = []
            for col in columns:
                val = row.get(col, "")
                if isinstance(val, float):
                    values.append("" if np.isnan(val) else f"{val:.6f}")
                else:
                    values.append(str(val))
            f.write(",".join(values) + "\n")

    print(f"\n{'='*65}")
    print(f"[SUCCESS] Grid hydrology features written to {OUTPUT_CSV.relative_to(BASE_DIR)}")
    print(f"          Total cells: {len(all_rows)}")

    nan_counts = {}
    for col in columns[2:]:
        n_nan = sum(1 for r in all_rows if isinstance(r.get(col), float) and np.isnan(r.get(col, 0.0)))
        if n_nan > 0:
            nan_counts[col] = n_nan
    if nan_counts:
        print(f"          NaN counts by column: {nan_counts}")
    else:
        print(f"          No NaN values — full coverage achieved.")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
