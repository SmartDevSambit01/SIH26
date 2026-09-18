"""
create_risk_grid.py
===================
Generates a regular 500-meter geographic analysis grid for the NER Safe pilot districts:
  1. Kohima District, Nagaland
  2. Aizawl District, Mizoram

The grid is constructed in a metric projected coordinate system (UTM Zone 46N, EPSG:32646),
clipped to the precise district boundary, and converted to WGS 84 (EPSG:4326) for web mapping.

Each grid feature contains:
  - cell_id (e.g., 'KOH_00001', 'AIZ_00001')
  - district ('Kohima' or 'Aizawl')
  - centroid_lat (WGS84 latitude, 6 decimals)
  - centroid_lon (WGS84 longitude, 6 decimals)
  - area_sqm (cell area in square meters)
  - geometry (Polygon or MultiPolygon clipped to district boundary)

Validation checks included:
  - No invalid geometries (Shapely is_valid)
  - No duplicate cell_ids
  - Confirms cells intersect and reside within the district boundary
  - Verifies both target districts are processed successfully
"""

import json
import os
import sys
import time
from pathlib import Path
import pyproj
from shapely.geometry import shape, box, mapping, Polygon, MultiPolygon
from shapely.ops import transform
from shapely.validation import make_valid

BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = BASE_DIR / "data" / "boundaries"

GRID_CELL_SIZE_METERS = 500.0  # 500 meters

DISTRICT_CONFIGS = [
    {
        "district": "Kohima",
        "state": "Nagaland",
        "boundary_file": "kohima_district.geojson",
        "output_grid_file": "kohima_grid_500m.geojson",
        "prefix": "KOH",
    },
    {
        "district": "Aizawl",
        "state": "Mizoram",
        "boundary_file": "aizawl_district.geojson",
        "output_grid_file": "aizawl_grid_500m.geojson",
        "prefix": "AIZ",
    },
]

# Coordinate transformation: WGS84 (EPSG:4326) <-> UTM Zone 46N (EPSG:32646)
wgs84_to_utm46n = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True).transform
utm46n_to_wgs84 = pyproj.Transformer.from_crs("EPSG:32646", "EPSG:4326", always_xy=True).transform


def clean_polygon_geometry(geom):
    """
    Extracts valid 2D polygonal geometry from intersection results,
    filtering out degenerate line or point slivers.
    """
    if geom is None or geom.is_empty:
        return None

    if not geom.is_valid:
        geom = make_valid(geom)

    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    elif geom.geom_type == "GeometryCollection":
        polygons = []
        for part in geom.geoms:
            if part.geom_type == "Polygon":
                polygons.append(part)
            elif part.geom_type == "MultiPolygon":
                polygons.extend(part.geoms)
        if not polygons:
            return None
        return MultiPolygon(polygons) if len(polygons) > 1 else polygons[0]
    return None


def generate_district_grid(config: dict) -> dict:
    district_name = config["district"]
    boundary_path = BOUNDARIES_DIR / config["boundary_file"]
    output_path = BOUNDARIES_DIR / config["output_grid_file"]
    prefix = config["prefix"]

    if not boundary_path.exists():
        raise FileNotFoundError(
            f"[ERROR] Boundary file not found at {boundary_path}. "
            f"Please run 'python scripts/prepare_boundaries.py' first."
        )

    print(f"\n[INFO] Generating {GRID_CELL_SIZE_METERS}m grid for {district_name} ({config['state']})...")
    start_time = time.time()

    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_geojson = json.load(f)

    district_feature = boundary_geojson["features"][0]
    district_geom_wgs84 = shape(district_feature["geometry"])

    # Transform boundary to UTM Zone 46N for metric 500m grid generation
    district_geom_utm = transform(wgs84_to_utm46n, district_geom_wgs84)
    if not district_geom_utm.is_valid:
        district_geom_utm = make_valid(district_geom_utm)

    min_x, min_y, max_x, max_y = district_geom_utm.bounds
    cols = int((max_x - min_x) / GRID_CELL_SIZE_METERS) + 1
    rows = int((max_y - min_y) / GRID_CELL_SIZE_METERS) + 1
    total_candidate_cells = cols * rows

    print(f"       Grid Extent (UTM): X=[{min_x:.1f}, {max_x:.1f}], Y=[{min_y:.1f}, {max_y:.1f}]")
    print(f"       Bounding matrix: {cols} columns x {rows} rows ({total_candidate_cells:,} candidate cells)")

    grid_features = []
    seen_cell_ids = set()
    invalid_geoms = 0
    boundary_intersections = 0
    fully_inside_cells = 0

    cell_index = 1
    x = min_x
    while x < max_x:
        y = min_y
        while y < max_y:
            cell_box = box(x, y, x + GRID_CELL_SIZE_METERS, y + GRID_CELL_SIZE_METERS)

            # Spatial pre-filtering: does the cell intersect the district?
            if district_geom_utm.intersects(cell_box):
                # Clip cell precisely to the district boundary
                clipped_utm = cell_box.intersection(district_geom_utm)
                clean_utm = clean_polygon_geometry(clipped_utm)

                # Skip null, empty, or micro-slivers (< 1.0 sq. meter)
                if clean_utm is not None and not clean_utm.is_empty and clean_utm.area >= 1.0:
                    area_sqm = round(clean_utm.area, 2)

                    # Track boundary vs internal cell
                    if abs(area_sqm - (GRID_CELL_SIZE_METERS * GRID_CELL_SIZE_METERS)) < 1.0:
                        fully_inside_cells += 1
                    else:
                        boundary_intersections += 1

                    # Project back to WGS 84 (EPSG:4326) for GeoJSON export
                    cell_geom_wgs84 = transform(utm46n_to_wgs84, clean_utm)

                    # Validation: geometry validity check
                    if not cell_geom_wgs84.is_valid:
                        cell_geom_wgs84 = make_valid(cell_geom_wgs84)
                        if not cell_geom_wgs84.is_valid:
                            invalid_geoms += 1
                            y += GRID_CELL_SIZE_METERS
                            continue

                    # Validation: Confirm intersection with district boundary
                    if not district_geom_wgs84.intersects(cell_geom_wgs84):
                        y += GRID_CELL_SIZE_METERS
                        continue

                    # Centroid coordinates in WGS 84
                    centroid_lon = round(cell_geom_wgs84.centroid.x, 6)
                    centroid_lat = round(cell_geom_wgs84.centroid.y, 6)

                    cell_id = f"{prefix}_{cell_index:05d}"
                    if cell_id in seen_cell_ids:
                        raise ValueError(f"Duplicate cell_id detected: {cell_id}")
                    seen_cell_ids.add(cell_id)

                    cell_properties = {
                        "cell_id": cell_id,
                        "district": district_name,
                        "state": config["state"],
                        "centroid_lat": centroid_lat,
                        "centroid_lon": centroid_lon,
                        "area_sqm": area_sqm,
                        "grid_size_m": GRID_CELL_SIZE_METERS,
                    }

                    grid_features.append(
                        {
                            "type": "Feature",
                            "properties": cell_properties,
                            "geometry": mapping(cell_geom_wgs84),
                        }
                    )
                    cell_index += 1

            y += GRID_CELL_SIZE_METERS
        x += GRID_CELL_SIZE_METERS

    # Validation Checks
    assert len(seen_cell_ids) == len(grid_features), "Mismatch between seen IDs and features"
    assert invalid_geoms == 0, f"Found {invalid_geoms} invalid geometries"
    assert len(grid_features) > 0, f"No grid cells were generated for {district_name}"

    feature_collection = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": grid_features,
    }

    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(feature_collection, out_f)

    elapsed = time.time() - start_time
    file_size_mb = output_path.stat().st_size / 1e6

    print(f"[OK] Completed {district_name}:")
    print(f"     Total Grid Cells Generated : {len(grid_features):,}")
    print(f"     Full 500m Interior Cells   : {fully_inside_cells:,}")
    print(f"     Clipped Border Cells       : {boundary_intersections:,}")
    print(f"     Invalid Geometries Discarded: {invalid_geoms}")
    print(f"     File Size                  : {file_size_mb:.2f} MB")
    print(f"     Elapsed Time               : {elapsed:.2f}s")
    print(f"     Saved To                   : {output_path.relative_to(BASE_DIR)}")

    return {
        "district": district_name,
        "cells_count": len(grid_features),
        "file_size_mb": round(file_size_mb, 2),
        "output_path": str(output_path.relative_to(BASE_DIR)),
        "fully_inside_cells": fully_inside_cells,
        "clipped_border_cells": boundary_intersections,
    }


def main():
    print("=" * 60)
    print("NER Safe — 500m Geographic Analysis Grid Generation")
    print(f"Cell Resolution: {GRID_CELL_SIZE_METERS}m x {GRID_CELL_SIZE_METERS}m")
    print("CRS Standards: UTM Zone 46N (EPSG:32646) for metrics, WGS84 for GeoJSON")
    print("=" * 60)

    summary_results = []
    for config in DISTRICT_CONFIGS:
        res = generate_district_grid(config)
        summary_results.append(res)

    print("\n" + "=" * 60)
    print("Summary of Generated Analysis Grids:")
    print("=" * 60)
    for r in summary_results:
        print(f"District: {r['district']:<10} | Cells: {r['cells_count']:>6,} | File: {r['output_path']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
