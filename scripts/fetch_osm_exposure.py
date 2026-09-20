#!/usr/bin/env python3
"""
fetch_osm_exposure.py — Real Roads/Hospitals/Schools Ingestion via OSM Overpass API

Fetches real OpenStreetMap exposure features (roads, hospitals, schools) for
the Kohima and Aizawl district boundaries, following the exact same source
(Overpass API) already used successfully for this project's locality index
(data/localities/{kohima,aizawl}_locality_index.csv, source: "OpenStreetMap
Overpass API").

PRD.md Sections 27, 39-41 designate roads/settlements/infrastructure as
EXPOSURE variables (not physical landslide causes) sourced from OSM/
authoritative GIS "where appropriate."

Anti-Fabrication Protocol (matches ingest_gpm_rainfall.py / ingest_smap_soil_moisture.py):
  - No road, hospital, or school is ever invented. If Overpass cannot be
    reached (network block, rate limit, timeout), the script writes an
    honest status file and produces NO output GeoJSON — it does not
    substitute placeholder geometry.
  - Every successful fetch records source, query, and retrieval timestamp
    for provenance.

Outputs (on success):
  data/exposure/raw/{district}_roads.geojson
  data/exposure/raw/{district}_hospitals.geojson
  data/exposure/raw/{district}_schools.geojson
  data/exposure/ingestion_status.json

Status file (always written, success or failure):
  {"status": "AVAILABLE" | "UNAVAILABLE", "reason": ..., "attempted_at": ...,
   "mirrors_tried": [...], "districts": {...}}
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] Missing dependency: requests")
    print("        pip install requests")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
BOUNDARIES_DIR = BASE_DIR / "data" / "boundaries"
EXPOSURE_DIR = BASE_DIR / "data" / "exposure"
RAW_DIR = EXPOSURE_DIR / "raw"
STATUS_FILE = EXPOSURE_DIR / "ingestion_status.json"

# Public Overpass mirrors, tried in order. All are free, unauthenticated,
# community-run infrastructure — no credentials to configure.
OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
]

REQUEST_TIMEOUT_S = 90
OVERPASS_QUERY_TIMEOUT_S = 60

DISTRICTS = [
    {"name": "kohima", "boundary": BOUNDARIES_DIR / "kohima_district.geojson"},
    {"name": "aizawl", "boundary": BOUNDARIES_DIR / "aizawl_district.geojson"},
]

ROAD_HIGHWAY_TYPES = ["motorway", "trunk", "primary", "secondary", "tertiary", "residential", "track"]


def load_boundary_bbox(boundary_path: Path):
    """Returns (south, west, north, east) bbox from a district boundary GeoJSON."""
    with open(boundary_path, "r", encoding="utf-8") as f:
        gj = json.load(f)

    lats, lons = [], []

    def walk(coords):
        if isinstance(coords[0], (float, int)):
            lons.append(coords[0])
            lats.append(coords[1])
        else:
            for c in coords:
                walk(c)

    for feat in gj["features"]:
        walk(feat["geometry"]["coordinates"])

    return min(lats), min(lons), max(lats), max(lons)


def build_overpass_query(bbox, kind: str) -> str:
    south, west, north, east = bbox
    bbox_str = f"{south},{west},{north},{east}"
    if kind == "roads":
        selectors = "\n  ".join(f'way["highway"="{h}"]({bbox_str});' for h in ROAD_HIGHWAY_TYPES)
        return f"[out:json][timeout:{OVERPASS_QUERY_TIMEOUT_S}];\n(\n  {selectors}\n);\nout geom;"
    elif kind == "hospitals":
        return (f'[out:json][timeout:{OVERPASS_QUERY_TIMEOUT_S}];\n'
                f'(\n  node["amenity"="hospital"]({bbox_str});\n'
                f'  way["amenity"="hospital"]({bbox_str});\n);\nout center;')
    elif kind == "schools":
        return (f'[out:json][timeout:{OVERPASS_QUERY_TIMEOUT_S}];\n'
                f'(\n  node["amenity"="school"]({bbox_str});\n'
                f'  way["amenity"="school"]({bbox_str});\n);\nout center;')
    raise ValueError(f"Unknown kind: {kind}")


def query_overpass(query: str, mirrors_tried: list) -> dict:
    """Tries each mirror in turn. Raises the last exception if all fail."""
    last_exc = None
    for mirror in OVERPASS_MIRRORS:
        mirrors_tried.append(mirror)
        try:
            resp = requests.post(mirror, data={"data": query}, timeout=REQUEST_TIMEOUT_S,
                                  headers={"User-Agent": "NER-Safe-SARVAS-research/1.0"})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"  [WARN] Mirror failed ({mirror}): {type(e).__name__}: {e}")
            last_exc = e
            continue
    raise last_exc


def overpass_to_geojson(osm_json: dict, feature_kind: str) -> dict:
    """Converts an Overpass 'out geom'/'out center' JSON response into GeoJSON."""
    features = []
    for el in osm_json.get("elements", []):
        props = {"osm_id": el.get("id"), "osm_type": el.get("type"), **el.get("tags", {})}
        if el["type"] == "node":
            geom = {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
        elif el["type"] == "way" and "geometry" in el:
            coords = [[pt["lon"], pt["lat"]] for pt in el["geometry"]]
            geom = {"type": "LineString", "coordinates": coords} if feature_kind == "roads" else {
                "type": "Point", "coordinates": [el.get("center", {}).get("lon"), el.get("center", {}).get("lat")]
            }
        elif "center" in el:
            geom = {"type": "Point", "coordinates": [el["center"]["lon"], el["center"]["lat"]]}
        else:
            continue
        features.append({"type": "Feature", "geometry": geom, "properties": props})

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "source": "OpenStreetMap Overpass API",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def main():
    print("NER Safe — OSM Exposure Ingestion (roads, hospitals, schools)")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    status = {
        "status": "UNAVAILABLE",
        "reason": None,
        "attempted_at": datetime.now(timezone.utc).isoformat(),
        "mirrors_tried": [],
        "districts": {},
    }

    any_success = False
    for dist_cfg in DISTRICTS:
        name = dist_cfg["name"]
        if not dist_cfg["boundary"].exists():
            print(f"[ERROR] Boundary not found for {name}: {dist_cfg['boundary']}")
            continue

        bbox = load_boundary_bbox(dist_cfg["boundary"])
        print(f"\n{'='*65}\n  Fetching OSM exposure data for {name} (bbox {bbox})\n{'='*65}")

        district_status = {}
        for kind in ("roads", "hospitals", "schools"):
            query = build_overpass_query(bbox, kind)
            print(f"  Querying {kind}...")
            try:
                t0 = time.time()
                osm_json = query_overpass(query, status["mirrors_tried"])
                geojson = overpass_to_geojson(osm_json, kind)
                out_path = RAW_DIR / f"{name}_{kind}.geojson"
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(geojson, f)
                n = len(geojson["features"])
                print(f"  [OK] {kind}: {n} features written to {out_path.relative_to(BASE_DIR)} "
                      f"({time.time()-t0:.1f}s)")
                district_status[kind] = {"status": "AVAILABLE", "feature_count": n}
                any_success = True
            except Exception as e:
                print(f"  [FAIL] {kind}: {type(e).__name__}: {e}")
                district_status[kind] = {"status": "UNAVAILABLE", "reason": f"{type(e).__name__}: {e}"}

        status["districts"][name] = district_status

    if any_success:
        status["status"] = "AVAILABLE" if all(
            all(k["status"] == "AVAILABLE" for k in d.values()) for d in status["districts"].values()
        ) else "PARTIAL"
    else:
        status["reason"] = (
            "All Overpass mirrors unreachable/blocked from this network. No roads/hospitals/schools "
            "data was fabricated. Re-run this script from a network with Overpass access; the "
            "downstream pipeline (assign_grid_exposure.py) will pick up the output automatically."
        )

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2)

    print(f"\n{'='*65}")
    print(f"[{'SUCCESS' if any_success else 'BLOCKED'}] Status written to {STATUS_FILE.relative_to(BASE_DIR)}")
    print(f"{'='*65}")
    sys.exit(0 if any_success else 2)


if __name__ == "__main__":
    main()
