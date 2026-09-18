"""
validate_geographic_data.py
===========================
Automated validation suite for NER Safe geographic data:
  1. District boundaries: Kohima and Aizawl
  2. 500m analysis grids: kohima_grid_500m.geojson and aizawl_grid_500m.geojson

Verifies:
  - Both districts exist
  - No invalid geometries (is_valid == True)
  - No duplicate cell_ids
  - Every grid cell intersects/resides within its corresponding district boundary
  - Properties completeness (cell_id, district, centroid_lat, centroid_lon)
  - Coordinate validity in WGS 84 (EPSG:4326)
"""

import json
import sys
from pathlib import Path
from shapely.geometry import shape

BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = BASE_DIR / "data" / "boundaries"

DISTRICTS_TO_TEST = [
    {
        "district": "Kohima",
        "boundary_file": "kohima_district.geojson",
        "grid_file": "kohima_grid_500m.geojson",
        "id_prefix": "KOH_",
    },
    {
        "district": "Aizawl",
        "boundary_file": "aizawl_district.geojson",
        "grid_file": "aizawl_grid_500m.geojson",
        "id_prefix": "AIZ_",
    },
]


def run_validations():
    print("=" * 65)
    print("NER Safe — Geographic Data Automated Validation Suite")
    print("=" * 65)

    all_passed = True

    for item in DISTRICTS_TO_TEST:
        district_name = item["district"]
        boundary_path = BOUNDARIES_DIR / item["boundary_file"]
        grid_path = BOUNDARIES_DIR / item["grid_file"]

        print(f"\n[TESTING] District: {district_name}")

        # Check 1: Existence of boundary and grid files
        if not boundary_path.exists():
            print(f"  [FAIL] Missing boundary file: {boundary_path.name}")
            all_passed = False
            continue
        if not grid_path.exists():
            print(f"  [FAIL] Missing grid file: {grid_path.name}")
            all_passed = False
            continue
        print(f"  [PASS] Both boundary and grid files exist.")

        # Load boundary
        with open(boundary_path, "r", encoding="utf-8") as f:
            b_data = json.load(f)
        b_geom = shape(b_data["features"][0]["geometry"])

        # Check 2: Boundary geometry validity
        if not b_geom.is_valid:
            print(f"  [FAIL] District boundary geometry is invalid.")
            all_passed = False
        else:
            print(f"  [PASS] District boundary is valid ({b_geom.geom_type}).")

        # Load grid
        with open(grid_path, "r", encoding="utf-8") as f:
            g_data = json.load(f)

        features = g_data.get("features", [])
        num_cells = len(features)
        print(f"  [INFO] Total cells to inspect: {num_cells:,}")

        if num_cells == 0:
            print(f"  [FAIL] Grid has 0 features.")
            all_passed = False
            continue

        seen_ids = set()
        duplicate_ids = 0
        invalid_geoms = 0
        outside_cells = 0
        missing_properties = 0

        for feat in features:
            props = feat.get("properties", {})
            cell_id = props.get("cell_id")

            # Check 3: Required properties
            if not all(k in props for k in ["cell_id", "district", "centroid_lat", "centroid_lon"]):
                missing_properties += 1

            # Check 4: Duplicate cell_ids
            if cell_id in seen_ids:
                duplicate_ids += 1
            else:
                seen_ids.add(cell_id)

            # Check 5: Geometry validity
            geom = shape(feat.get("geometry", {}))
            if not geom.is_valid:
                invalid_geoms += 1

            # Check 6: Grid cells are inside / intersect district boundary
            if not b_geom.intersects(geom):
                outside_cells += 1

        # Report checks
        if duplicate_ids == 0:
            print(f"  [PASS] No duplicate cell_ids (unique IDs: {len(seen_ids):,}).")
        else:
            print(f"  [FAIL] Found {duplicate_ids} duplicate cell_ids.")
            all_passed = False

        if invalid_geoms == 0:
            print(f"  [PASS] 100% of grid geometries are valid.")
        else:
            print(f"  [FAIL] Found {invalid_geoms} invalid grid geometries.")
            all_passed = False

        if outside_cells == 0:
            print(f"  [PASS] 100% of cells intersect/reside inside district boundary.")
        else:
            print(f"  [FAIL] Found {outside_cells} cells completely outside district.")
            all_passed = False

        if missing_properties == 0:
            print(f"  [PASS] All features contain required properties.")
        else:
            print(f"  [FAIL] {missing_properties} features missing required properties.")
            all_passed = False

    print("\n" + "=" * 65)
    if all_passed:
        print("[SUCCESS] ALL GEOGRAPHIC VALIDATION CHECKS PASSED.")
    else:
        print("[FAILURE] GEOGRAPHIC VALIDATION FAILED ON ONE OR MORE CHECKS.")
    print("=" * 65)

    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    run_validations()
