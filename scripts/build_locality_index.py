import os
import json
import math
import time
import urllib.request
import urllib.parse
import csv
from datetime import datetime

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://interpreter.overpass-api.de/api/interpreter"
]

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
LOCALITIES_DIR = os.path.join(DATA_DIR, "localities")
BOUNDARIES_DIR = os.path.join(DATA_DIR, "boundaries")

# Strict max distance radius for cell-to-locality association (in meters)
MAX_ASSOCIATION_RADIUS_M = 2500.0

PLACE_TYPES = [
    "city", "town", "suburb", "neighbourhood", "neighborhood",
    "village", "hamlet", "locality", "isolated_dwelling", "quarter"
]

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def point_in_polygon(lon, lat, polygon_coords):
    # Ray-casting algorithm for 2D point in polygon
    inside = False
    n = len(polygon_coords)
    p1x, p1y = polygon_coords[0]
    for i in range(n + 1):
        p2x, p2y = polygon_coords[i % n]
        if lat > min(p1y, p2y):
            if lat <= max(p1y, p2y):
                if lon <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or lon <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def point_in_geometry(lon, lat, geometry):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        for ring in coords:
            if point_in_polygon(lon, lat, ring):
                return True
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                if point_in_polygon(lon, lat, ring):
                    return True
    return False

def query_overpass_bbox(min_lat, min_lon, max_lat, max_lon):
    bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    query = f"""[out:json][timeout:30];
(
  node["place"]({bbox_str});
  way["place"]({bbox_str});
  relation["place"]({bbox_str});
);
out center;"""

    for url in OVERPASS_URLS:
        try:
            print(f"Querying Overpass API at {url}...")
            data = urllib.parse.urlencode({"data": query}).encode("utf-8")
            req = urllib.request.Request(
                url, 
                data=data, 
                headers={"User-Agent": "SIH2026LandslideRiskIntelligence/1.0"}
            )
            with urllib.request.urlopen(req, timeout=35) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    elements = payload.get("elements", [])
                    print(f"Successfully retrieved {len(elements)} OSM elements from {url}")
                    return elements, url, query
        except Exception as e:
            print(f"Failed to query {url}: {e}")
            time.sleep(1)
            
    print("WARNING: All Overpass API endpoints failed or timed out.")
    return [], "", query

def process_district(district_name, state_name, grid_filename, boundary_filename, area_id_prefix):
    grid_path = os.path.join(BOUNDARIES_DIR, grid_filename)
    boundary_path = os.path.join(BOUNDARIES_DIR, boundary_filename)
    
    if not os.path.exists(grid_path) or not os.path.exists(boundary_path):
        print(f"Error: Boundary file {grid_path} or {boundary_path} missing.")
        return [], []
        
    with open(grid_path, "r", encoding="utf-8") as f:
        grid_data = json.load(f)
        
    with open(boundary_path, "r", encoding="utf-8") as f:
        boundary_data = json.load(f)
        
    district_geom = boundary_data["features"][0]["geometry"]
    
    # Calculate bounding box of grid
    cells = grid_data.get("features", [])
    if not cells:
        print(f"No grid cells found in {grid_filename}")
        return [], []
        
    lats = [c["properties"]["centroid_lat"] for c in cells]
    lons = [c["properties"]["centroid_lon"] for c in cells]
    min_lat, max_lat = min(lats) - 0.05, max(lats) + 0.05
    min_lon, max_lon = min(lons) - 0.05, max(lons) + 0.05
    
    elements, source_url, query_ref = query_overpass_bbox(min_lat, min_lon, max_lat, max_lon)
    
    localities = []
    seen_names = set()
    idx = 1
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for elem in elements:
        tags = elem.get("tags", {})
        place_type = tags.get("place")
        
        # Check place type
        if place_type not in PLACE_TYPES:
            continue
            
        # Get name (English preferred, fallback to name)
        name = tags.get("name:en") or tags.get("name")
        if not name or not name.strip():
            continue
            name = name.strip()
            
        lat = elem.get("lat") or elem.get("center", {}).get("lat")
        lon = elem.get("lon") or elem.get("center", {}).get("lon")
        
        if lat is None or lon is None:
            continue
            
        # Verify point is inside district geometry or close to cells
        if not point_in_geometry(lon, lat, district_geom):
            # Check minimum distance to any cell centroid in district
            min_dist_to_cells = min(haversine_distance(lat, lon, c["properties"]["centroid_lat"], c["properties"]["centroid_lon"]) for c in cells)
            if min_dist_to_cells > 3000.0:  # Allow small buffer outside administrative line
                continue
                
        # Deduplicate identical names close to each other
        dup = False
        for loc in localities:
            if loc["area_name"].lower() == name.lower():
                dist = haversine_distance(lat, lon, loc["latitude"], loc["longitude"])
                if dist < 1000.0:  # Same place repeated
                    dup = True
                    break
        if dup:
            continue
            
        area_id = f"{area_id_prefix}_LOC_{idx:03d}"
        idx += 1
        
        localities.append({
            "area_id": area_id,
            "area_name": name,
            "place_type": place_type,
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "source": "OpenStreetMap Overpass API",
            "source_url": source_url if source_url else "https://overpass-api.de/api/interpreter",
            "source_date": today_str,
            "state": state_name,
            "district": district_name
        })
        
    print(f"Extracted {len(localities)} verified localities for {district_name}")
    
    # Map cells to nearest locality within MAX_ASSOCIATION_RADIUS_M
    mappings = []
    for cell in cells:
        c_props = cell["properties"]
        c_id = c_props["cell_id"]
        c_lat = c_props["centroid_lat"]
        c_lon = c_props["centroid_lon"]
        
        nearest_loc = None
        min_dist = float("inf")
        
        for loc in localities:
            dist = haversine_distance(c_lat, c_lon, loc["latitude"], loc["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest_loc = loc
                
        if nearest_loc is not None and min_dist <= MAX_ASSOCIATION_RADIUS_M:
            mappings.append({
                "area_id": nearest_loc["area_id"],
                "area_name": nearest_loc["area_name"],
                "cell_id": c_id,
                "distance_to_cell_m": round(min_dist, 2),
                "association_method": f"nearest_centroid_max_{int(MAX_ASSOCIATION_RADIUS_M)}m",
                "source": nearest_loc["source"]
            })
            
    print(f"Mapped {len(mappings)} / {len(cells)} cells to localities in {district_name}")
    return localities, mappings

def main():
    os.makedirs(LOCALITIES_DIR, exist_ok=True)
    
    print("=== Phase 1 & 2: Building Locality Index & Cell Mapping ===")
    kohima_locs, kohima_maps = process_district(
        "Kohima", "Nagaland", "kohima_grid_500m.geojson", "kohima_district.geojson", "KOH"
    )
    
    aizawl_locs, aizawl_maps = process_district(
        "Aizawl", "Mizoram", "aizawl_grid_500m.geojson", "aizawl_district.geojson", "AIZ"
    )
    
    # Save Kohima Locality CSV
    kohima_csv_path = os.path.join(LOCALITIES_DIR, "kohima_locality_index.csv")
    fieldnames = ["area_id", "area_name", "place_type", "latitude", "longitude", "source", "source_url", "source_date", "state", "district"]
    with open(kohima_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kohima_locs)
    print(f"Saved {kohima_csv_path}")
    
    # Save Aizawl Locality CSV
    aizawl_csv_path = os.path.join(LOCALITIES_DIR, "aizawl_locality_index.csv")
    with open(aizawl_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(aizawl_locs)
    print(f"Saved {aizawl_csv_path}")
    
    # Save Combined Cell Mappings CSV
    mapping_csv_path = os.path.join(LOCALITIES_DIR, "locality_cell_mapping.csv")
    map_fieldnames = ["area_id", "area_name", "cell_id", "distance_to_cell_m", "association_method", "source"]
    all_mappings = kohima_maps + aizawl_maps
    with open(mapping_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=map_fieldnames)
        writer.writeheader()
        writer.writerows(all_mappings)
    print(f"Saved {mapping_csv_path}")

if __name__ == "__main__":
    main()
