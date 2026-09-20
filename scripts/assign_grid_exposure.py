"""
assign_grid_exposure.py
========================
Maps real OpenStreetMap roads/hospitals/schools (fetch_osm_exposure.py output)
onto the 500 m NER Safe risk grid, mirroring the zonal-join pattern used by
assign_grid_terrain.py / assign_grid_hydrology.py.

PRD.md Sections 27, 39-41: roads/settlements/infrastructure are EXPOSURE
variables, never physical landslide causes.

For each grid cell the script computes (all distances in meters, UTM 46N):
  - nearest_road_distance_m, nearest_road_class
  - road_length_in_cell_m   (total OSM road length intersecting the cell)
  - nearest_hospital_distance_m, nearest_hospital_name
  - nearest_school_distance_m, nearest_school_name

Uses a shapely STRtree spatial index per feature layer so nearest-neighbor
and intersection queries stay fast even with thousands of OSM features
across 16,961 grid cells (naive O(cells x features) would not scale).

Anti-Fabrication Protocol:
  - If fetch_osm_exposure.py has not produced data for a district (Overpass
    unreachable), that district's cells are written with
    exposure_status = UNAVAILABLE and all distance/name fields empty —
    never a fabricated distance or "no infrastructure nearby" claim.

Output:
  data/ml/grid_exposure_features.csv
"""

import json
import sys
import time
from pathlib import Path

try:
    from shapely.geometry import shape
    from shapely.ops import transform as shapely_transform
    from shapely.strtree import STRtree
    from pyproj import Transformer
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("        pip install shapely pyproj")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = BASE_DIR / "data" / "boundaries"
EXPOSURE_RAW_DIR = BASE_DIR / "data" / "exposure" / "raw"
ML_DIR = BASE_DIR / "data" / "ml"
OUTPUT_CSV = ML_DIR / "grid_exposure_features.csv"

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True)

DISTRICTS = [
    {"name": "Kohima", "prefix": "kohima", "grid_file": BOUNDARIES_DIR / "kohima_grid_500m.geojson"},
    {"name": "Aizawl", "prefix": "aizawl", "grid_file": BOUNDARIES_DIR / "aizawl_grid_500m.geojson"},
]

ROAD_CLASS_PRIORITY = {"motorway": 0, "trunk": 1, "primary": 2, "secondary": 3, "tertiary": 4, "residential": 5, "track": 6}


def load_osm_layer(path: Path):
    """Loads an OSM GeoJSON layer and reprojects to UTM 46N. Returns [] if missing."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        gj = json.load(f)
    items = []
    for feat in gj.get("features", []):
        geom = shape(feat["geometry"])
        if geom.is_empty:
            continue
        geom_utm = shapely_transform(TRANSFORMER.transform, geom)
        items.append((geom_utm, feat.get("properties", {})))
    return items


def build_index(items):
    if not items:
        return None, {}
    geoms = [g for g, _ in items]
    tree = STRtree(geoms)
    props_by_id = {id(g): p for g, p in items}
    return tree, props_by_id


def nearest_feature(tree, props_by_id, point_geom):
    if tree is None:
        return None, None
    idx = tree.nearest(point_geom)
    geom = tree.geometries[idx]
    props = props_by_id.get(id(geom))
    distance = point_geom.distance(geom)
    return distance, props


def process_district(dist_cfg: dict) -> list:
    name = dist_cfg["name"]
    prefix = dist_cfg["prefix"]
    grid_path = dist_cfg["grid_file"]

    print(f"\n{'='*65}")
    print(f"  Processing zonal exposure statistics for {name} district")
    print(f"{'='*65}")
    t0 = time.time()

    roads = load_osm_layer(EXPOSURE_RAW_DIR / f"{prefix}_roads.geojson")
    hospitals = load_osm_layer(EXPOSURE_RAW_DIR / f"{prefix}_hospitals.geojson")
    schools = load_osm_layer(EXPOSURE_RAW_DIR / f"{prefix}_schools.geojson")

    exposure_available = bool(roads or hospitals or schools)
    print(f"  OSM features loaded: {len(roads)} roads, {len(hospitals)} hospitals, {len(schools)} schools "
          f"({'AVAILABLE' if exposure_available else 'UNAVAILABLE — Overpass fetch has not succeeded yet'})")

    road_tree, road_props = build_index(roads)
    hospital_tree, hospital_props = build_index(hospitals)
    school_tree, school_props = build_index(schools)

    with open(grid_path, "r", encoding="utf-8") as f:
        grid_data = json.load(f)
    features = grid_data["features"]
    print(f"  Loaded {len(features)} grid cells from {grid_path.name}")

    rows = []
    report_interval = max(1, len(features) // 10)
    for i, feat in enumerate(features):
        cell_id = feat["properties"].get("cell_id", f"{prefix}_{i}")
        cell_geom_utm = shapely_transform(TRANSFORMER.transform, shape(feat["geometry"]))
        centroid = cell_geom_utm.centroid

        if not exposure_available:
            rows.append({"cell_id": cell_id, "district": name, "exposure_status": "UNAVAILABLE"})
            continue

        road_dist, road_p = nearest_feature(road_tree, road_props, centroid)
        road_length_in_cell = 0.0
        if road_tree is not None:
            for idx in road_tree.query(cell_geom_utm):
                geom = road_tree.geometries[idx]
                if geom.intersects(cell_geom_utm):
                    road_length_in_cell += geom.intersection(cell_geom_utm).length

        hosp_dist, hosp_p = nearest_feature(hospital_tree, hospital_props, centroid)
        school_dist, school_p = nearest_feature(school_tree, school_props, centroid)

        rows.append({
            "cell_id": cell_id, "district": name, "exposure_status": "AVAILABLE",
            "nearest_road_distance_m": round(road_dist, 1) if road_dist is not None else "",
            "nearest_road_class": (road_p or {}).get("highway", "") if road_p else "",
            "road_length_in_cell_m": round(road_length_in_cell, 1),
            "nearest_hospital_distance_m": round(hosp_dist, 1) if hosp_dist is not None else "",
            "nearest_hospital_name": (hosp_p or {}).get("name", "") if hosp_p else "",
            "nearest_school_distance_m": round(school_dist, 1) if school_dist is not None else "",
            "nearest_school_name": (school_p or {}).get("name", "") if school_p else "",
        })

        if (i + 1) % report_interval == 0:
            print(f"       Processed {i + 1}/{len(features)} cells...")

    elapsed = time.time() - t0
    print(f"  [OK] {name}: {len(rows)} cells processed in {elapsed:.1f}s")
    return rows


def main():
    print("NER Safe — 500 m Grid Exposure Zonal Statistics (Real OSM Roads/Hospitals/Schools)")
    print(f"Output: {OUTPUT_CSV.relative_to(BASE_DIR)}\n")

    all_rows = []
    for dist_cfg in DISTRICTS:
        all_rows.extend(process_district(dist_cfg))

    ML_DIR.mkdir(parents=True, exist_ok=True)
    columns = ["cell_id", "district", "exposure_status", "nearest_road_distance_m", "nearest_road_class",
               "road_length_in_cell_m", "nearest_hospital_distance_m", "nearest_hospital_name",
               "nearest_school_distance_m", "nearest_school_name"]

    with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(columns) + "\n")
        for row in all_rows:
            values = [str(row.get(col, "")).replace(",", ";") for col in columns]
            f.write(",".join(values) + "\n")

    available = sum(1 for r in all_rows if r.get("exposure_status") == "AVAILABLE")
    print(f"\n{'='*65}")
    print(f"[SUCCESS] Grid exposure features written to {OUTPUT_CSV.relative_to(BASE_DIR)}")
    print(f"          Total cells: {len(all_rows)} | AVAILABLE: {available} | UNAVAILABLE: {len(all_rows) - available}")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
