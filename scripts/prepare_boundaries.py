"""
prepare_boundaries.py
=====================
Loads, validates, projects, and saves the official administrative boundaries
for the two NER Safe pilot districts:
  1. Kohima District, Nagaland
  2. Aizawl District, Mizoram

Data Source:
  Local Government Directory (LGD), Government of India / geoBoundaries ADM2 (India)
  License: Open Data Commons Open Database License (ODbL) 1.0

Outputs:
  - data/boundaries/kohima_district.geojson
  - data/boundaries/aizawl_district.geojson
  - data/boundaries/pilot_districts.geojson
"""

import json
import os
import sys
from pathlib import Path
import pyproj
from shapely.geometry import shape, mapping
from shapely.ops import transform
from shapely.validation import make_valid

# Define directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
RAW_DIR = BOUNDARIES_DIR / "raw"

# Official source URL
GEOBOUNDARIES_IND_ADM2_URL = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2.geojson"
)

# Projected coordinate system for accurate metric calculation: UTM Zone 46N (covers 90°E - 96°E)
wgs84_to_utm46n = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32646", always_xy=True).transform

TARGET_DISTRICTS = {
    "Kohima": {
        "state": "Nagaland",
        "output_filename": "kohima_district.geojson",
        "iso": "IN-NL",
    },
    "Aizawl": {
        "state": "Mizoram",
        "output_filename": "aizawl_district.geojson",
        "iso": "IN-MZ",
    },
}


def download_raw_if_missing(raw_path: Path):
    """Download the authoritative IND ADM2 geojson if not already present."""
    if raw_path.exists():
        print(f"[INFO] Using existing raw boundaries file: {raw_path}")
        return

    import requests

    print(f"[INFO] Downloading authoritative India ADM2 boundaries from {GEOBOUNDARIES_IND_ADM2_URL}...")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(GEOBOUNDARIES_IND_ADM2_URL, stream=True, timeout=60)
    resp.raise_for_status()

    with open(raw_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(f"[SUCCESS] Download complete ({raw_path.stat().st_size / 1e6:.2f} MB).")


def process_boundaries():
    BOUNDARIES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Check for raw cache
    temp_cache = BASE_DIR / "india_adm2_temp.geojson"
    raw_path = RAW_DIR / "geoBoundaries-IND-ADM2.geojson"

    if temp_cache.exists() and not raw_path.exists():
        temp_cache.replace(raw_path)
    elif not raw_path.exists():
        download_raw_if_missing(raw_path)

    print(f"[INFO] Loading {raw_path}...")
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    extracted_features = {}

    for feat in data.get("features", []):
        props = feat.get("properties", {})
        shape_name = props.get("shapeName", "").strip()

        for district_name, info in TARGET_DISTRICTS.items():
            if shape_name.lower() == district_name.lower():
                extracted_features[district_name] = feat
                break

    # Verification: Both districts must exist
    missing = set(TARGET_DISTRICTS.keys()) - set(extracted_features.keys())
    if missing:
        raise ValueError(f"[ERROR] Could not find authoritative boundaries for: {missing}")

    all_pilot_features = []

    print("\n" + "=" * 60)
    print("NER Safe — District Boundary Preparation & Validation")
    print("=" * 60)

    for district_name, feat in extracted_features.items():
        meta = TARGET_DISTRICTS[district_name]
        raw_geom = shape(feat["geometry"])

        # Geometry validation
        if not raw_geom.is_valid:
            print(f"[WARN] Geometry for {district_name} is invalid. Applying make_valid...")
            geom = make_valid(raw_geom)
        else:
            geom = raw_geom

        assert geom.is_valid, f"Failed to produce a valid geometry for {district_name}"

        # Bounding box in EPSG:4326 (min_lon, min_lat, max_lon, max_lat)
        min_lon, min_lat, max_lon, max_lat = geom.bounds

        # Reproject to UTM Zone 46N (EPSG:32646) for planar area and perimeter calculations
        geom_utm = transform(wgs84_to_utm46n, geom)
        area_sqkm = round(geom_utm.area / 1e6, 2)
        perimeter_km = round(geom_utm.length / 1e3, 2)

        # Centroid coordinates
        centroid_lon = round(geom.centroid.x, 6)
        centroid_lat = round(geom.centroid.y, 6)

        clean_properties = {
            "district": district_name,
            "state": meta["state"],
            "country": "India",
            "state_iso": meta["iso"],
            "area_sqkm": area_sqkm,
            "perimeter_km": perimeter_km,
            "centroid_lon": centroid_lon,
            "centroid_lat": centroid_lat,
            "bbox": [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)],
            "crs": "EPSG:4326",
            "source": "LGD / geoBoundaries IND-ADM2 (Open Data Commons ODbL 1.0)",
        }

        feature_geojson = {
            "type": "Feature",
            "properties": clean_properties,
            "geometry": mapping(geom),
        }

        output_path = BOUNDARIES_DIR / meta["output_filename"]
        fc = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}, "features": [feature_geojson]}

        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(fc, out_f, indent=2)

        all_pilot_features.append(feature_geojson)

        print(f"\n[OK] District: {district_name} ({meta['state']})")
        print(f"     Geometry Type : {geom.geom_type}")
        print(f"     Valid         : {geom.is_valid}")
        print(f"     Area          : {area_sqkm:,.2f} sq km")
        print(f"     Perimeter     : {perimeter_km:,.2f} km")
        print(f"     Centroid      : ({centroid_lat}, {centroid_lon})")
        print(f"     Bounding Box  : [{min_lon:.5f}, {min_lat:.5f}, {max_lon:.5f}, {max_lat:.5f}]")
        print(f"     Saved to      : {output_path.relative_to(BASE_DIR)}")

    # Also save combined pilot boundaries file
    combined_path = BOUNDARIES_DIR / "pilot_districts.geojson"
    combined_fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": all_pilot_features,
    }
    with open(combined_path, "w", encoding="utf-8") as out_f:
        json.dump(combined_fc, out_f, indent=2)
    print(f"\n[OK] Combined pilot boundaries saved to: {combined_path.relative_to(BASE_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    process_boundaries()
