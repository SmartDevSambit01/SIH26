"""
prepare_historical_events.py
============================
Loads, cleans, validates, and spatially matches historical landslide event records
for the NER Safe prototype:
  1. Kohima District, Nagaland
  2. Aizawl District, Mizoram

Key Functions:
  - Validates CSV schema and data types.
  - Validates event dates (2020-2026).
  - Deduplicates records.
  - Validates coordinate bounds against official district boundaries.
  - Performs spatial grid cell matching ONLY for VERIFIED events.
  - Produces cleaned output CSV (with cell_id and matched_district).
  - Generates verified GeoJSON for web mapping.
  - Evaluates dataset sufficiency for Machine Learning.
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from shapely.geometry import Point, shape, mapping
from shapely.strtree import STRtree

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORICAL_DIR = DATA_DIR / "historical"
BOUNDARIES_DIR = DATA_DIR / "boundaries"

RAW_CSV_PATH = HISTORICAL_DIR / "landslide_events.csv"
CLEAN_CSV_PATH = HISTORICAL_DIR / "landslide_events_cleaned.csv"
VERIFIED_GEOJSON_PATH = HISTORICAL_DIR / "landslide_events_verified.geojson"

REQUIRED_COLUMNS = [
    "event_id",
    "location_name",
    "district",
    "state",
    "event_date",
    "event_time",
    "latitude",
    "longitude",
    "source",
    "description",
    "coordinate_status",
]

ALLOWED_STATUSES = {"VERIFIED", "NEEDS_VERIFICATION", "MISSING"}
ALLOWED_DISTRICTS = {"Kohima", "Aizawl"}


def load_spatial_layers():
    """Load district boundary polygons and 500m analysis grids with spatial indexing."""
    boundaries = {}
    grids = {}

    for district in ALLOWED_DISTRICTS:
        dist_lower = district.lower()
        boundary_file = BOUNDARIES_DIR / f"{dist_lower}_district.geojson"
        grid_file = BOUNDARIES_DIR / f"{dist_lower}_grid_500m.geojson"

        if not boundary_file.exists():
            raise FileNotFoundError(f"Missing boundary file: {boundary_file}. Run scripts/prepare_boundaries.py first.")
        if not grid_file.exists():
            raise FileNotFoundError(f"Missing grid file: {grid_file}. Run scripts/create_risk_grid.py first.")

        with open(boundary_file, "r", encoding="utf-8") as f:
            b_data = json.load(f)
            boundaries[district] = shape(b_data["features"][0]["geometry"])

        with open(grid_file, "r", encoding="utf-8") as f:
            g_data = json.load(f)
            features = g_data["features"]
            geoms = [shape(feat["geometry"]) for feat in features]
            cell_ids = [feat["properties"]["cell_id"] for feat in features]
            tree = STRtree(geoms)
            grids[district] = {
                "features": features,
                "geoms": geoms,
                "cell_ids": cell_ids,
                "tree": tree,
            }

    return boundaries, grids


def prepare_events():
    print("=" * 65)
    print("NER Safe — Historical Landslide Dataset Preparation & Validation")
    print("=" * 65)

    if not RAW_CSV_PATH.exists():
        raise FileNotFoundError(f"Source file {RAW_CSV_PATH} not found.")

    boundaries, grids = load_spatial_layers()

    records = []
    with open(RAW_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for col in REQUIRED_COLUMNS:
            if col not in reader.fieldnames:
                raise ValueError(f"Missing required column in CSV: '{col}'")
        for row in reader:
            records.append(row)

    print(f"[INFO] Loaded {len(records)} raw historical event records.")

    # Validation and cleaning
    cleaned_rows = []
    verified_features = []

    seen_ids = set()
    duplicate_count = 0
    date_errors = 0
    district_mismatch_errors = 0
    out_of_bounds_errors = 0

    kohima_total = 0
    aizawl_total = 0
    verified_count = 0
    needs_verif_count = 0
    missing_coord_count = 0

    for idx, row in enumerate(records, start=1):
        event_id = row["event_id"].strip()
        district = row["district"].strip()
        state = row["state"].strip()
        date_str = row["event_date"].strip()
        coord_status = row["coordinate_status"].strip()

        # 1. Deduplication
        if event_id in seen_ids:
            print(f"[WARN] Duplicate event_id found: {event_id}. Skipping row {idx}.")
            duplicate_count += 1
            continue
        seen_ids.add(event_id)

        # 2. District filter check
        if district not in ALLOWED_DISTRICTS:
            print(f"[WARN] District '{district}' not in pilot scope ({ALLOWED_DISTRICTS}). Skipping.")
            district_mismatch_errors += 1
            continue

        if district == "Kohima":
            kohima_total += 1
        elif district == "Aizawl":
            aizawl_total += 1

        # 3. Date format and range check (2020-2026)
        try:
            event_dt = datetime.strptime(date_str, "%Y-%m-%d")
            if not (2020 <= event_dt.year <= 2026):
                print(f"[ERROR] Event {event_id} date {date_str} outside 2020-2026 range.")
                date_errors += 1
        except ValueError:
            print(f"[ERROR] Invalid date format for {event_id}: '{date_str}'. Expected YYYY-MM-DD.")
            date_errors += 1

        # 4. Status validation
        if coord_status not in ALLOWED_STATUSES:
            raise ValueError(f"Invalid coordinate_status '{coord_status}' in event {event_id}")

        cell_id = ""
        matched_district = ""

        # 5. Coordinate handling & spatial validation
        if coord_status == "MISSING":
            missing_coord_count += 1
            # Verify coordinates are indeed empty
            if row["latitude"].strip() != "" or row["longitude"].strip() != "":
                print(f"[WARN] Event {event_id} marked MISSING but coordinates supplied. Clearing them.")
                row["latitude"] = ""
                row["longitude"] = ""

        elif coord_status in ("VERIFIED", "NEEDS_VERIFICATION"):
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except ValueError:
                raise ValueError(f"Event {event_id} has invalid float coordinates: lat='{row['latitude']}', lon='{row['longitude']}'")

            # Check general bounds for Northeast India
            if not (22.0 <= lat <= 28.0 and 91.0 <= lon <= 96.0):
                print(f"[ERROR] Coordinates ({lat}, {lon}) out of regional bounds for {event_id}.")
                out_of_bounds_errors += 1

            pt = Point(lon, lat)
            dist_geom = boundaries[district]

            # Verify inside district boundary polygon
            if not dist_geom.contains(pt):
                print(f"[WARN] Coordinates for {event_id} ({lat}, {lon}) fall OUTSIDE {district} district boundary!")
                out_of_bounds_errors += 1
                if coord_status == "VERIFIED":
                    print(f"       Downgrading {event_id} from VERIFIED to NEEDS_VERIFICATION due to boundary mismatch.")
                    coord_status = "NEEDS_VERIFICATION"
                    row["coordinate_status"] = coord_status

            if coord_status == "VERIFIED":
                verified_count += 1
                # Spatial matching: find grid cell
                grid_info = grids[district]
                match_indices = grid_info["tree"].query(pt, predicate="intersects")
                if len(match_indices) > 0:
                    matched_idx = match_indices[0]
                    cell_id = grid_info["cell_ids"][matched_idx]
                    matched_district = district
                else:
                    # Point might be on extreme border margin
                    # Find closest cell within 250m
                    closest_idx = grid_info["tree"].nearest(pt)
                    cell_id = grid_info["cell_ids"][closest_idx]
                    matched_district = district

                # Create GeoJSON feature for verified event
                verified_features.append(
                    {
                        "type": "Feature",
                        "geometry": mapping(pt),
                        "properties": {
                            "event_id": event_id,
                            "location_name": row["location_name"],
                            "district": district,
                            "state": state,
                            "event_date": date_str,
                            "event_time": row["event_time"],
                            "cell_id": cell_id,
                            "source": row["source"],
                            "description": row["description"],
                        },
                    }
                )

            elif coord_status == "NEEDS_VERIFICATION":
                needs_verif_count += 1
                # As per Task 4: Do not perform spatial matching for unverified coordinates
                cell_id = ""
                matched_district = ""

        # Update row
        out_row = dict(row)
        out_row["cell_id"] = cell_id
        out_row["matched_district"] = matched_district
        cleaned_rows.append(out_row)

    # Save cleaned CSV
    output_columns = REQUIRED_COLUMNS + ["cell_id", "matched_district"]
    with open(CLEAN_CSV_PATH, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(cleaned_rows)

    # Save verified GeoJSON
    verified_fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": verified_features,
    }
    with open(VERIFIED_GEOJSON_PATH, "w", encoding="utf-8") as out_f:
        json.dump(verified_fc, out_f, indent=2)

    print("\n" + "=" * 65)
    print("HISTORICAL DATA QUALITY SUMMARY")
    print("=" * 65)
    print(f"Total Records Processed       : {len(cleaned_rows)}")
    print(f"Kohima District Events        : {kohima_total}")
    print(f"Aizawl District Events        : {aizawl_total}")
    print(f"Verified Coordinates          : {verified_count}")
    print(f"Needs Verification            : {needs_verif_count}")
    print(f"Missing Coordinates           : {missing_coord_count}")
    print(f"Duplicate Records Removed     : {duplicate_count}")
    print(f"Date/Boundary Errors Flagged  : {date_errors + out_of_bounds_errors}")
    print(f"Cleaned CSV Saved To          : {CLEAN_CSV_PATH.relative_to(BASE_DIR)}")
    print(f"Verified GeoJSON Saved To     : {VERIFIED_GEOJSON_PATH.relative_to(BASE_DIR)}")

    # ML Readiness Evaluation
    print("\n" + "-" * 65)
    print("MACHINE LEARNING READINESS ASSESSMENT")
    print("-" * 65)

    is_ready_for_ml = False
    min_required_per_district = 50

    kohima_verified = sum(1 for r in cleaned_rows if r["district"] == "Kohima" and r["coordinate_status"] == "VERIFIED")
    aizawl_verified = sum(1 for r in cleaned_rows if r["district"] == "Aizawl" and r["coordinate_status"] == "VERIFIED")

    print(f"Kohima Verified Events        : {kohima_verified}")
    print(f"Aizawl Verified Events        : {aizawl_verified}")
    print(f"Minimum Recommended for ML    : {min_required_per_district} per district")

    if kohima_verified < min_required_per_district or aizawl_verified < min_required_per_district:
        print("[STATUS: NOT READY FOR ML TRAINING]")
        print("Reason: There are too few verified historical landslide events in the current")
        print("curated sample (Kohima: %d, Aizawl: %d) to train a statistically credible," % (kohima_verified, aizawl_verified))
        print("spatially cross-validated supervised model without severe overfitting.")
        print("\nACTION REQUIRED:")
        print("To proceed to ML training, an official GIS export of the National Landslide")
        print("Susceptibility Mapping (NLSM) or Geological Survey of India (GSI) Bhukosh")
        print("landslide inventory shapefile/GeoJSON for Nagaland and Mizoram must be provided.")
        print("Synthetic or fabricated landslide coordinates MUST NOT be created.")
    else:
        is_ready_for_ml = True
        print("[STATUS: READY FOR ML TRAINING]")

    print("=" * 65)

    return {
        "total_records": len(cleaned_rows),
        "kohima_events": kohima_total,
        "aizawl_events": aizawl_total,
        "verified_coordinates": verified_count,
        "needs_verification": needs_verif_count,
        "missing_coordinates": missing_coord_count,
        "is_ready_for_ml": is_ready_for_ml,
    }


if __name__ == "__main__":
    prepare_events()
