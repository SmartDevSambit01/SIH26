"""
download_dem.py
===============
Downloads official Copernicus DEM GLO-30 (30-meter global digital elevation model)
tiles for the NER Safe pilot districts:
  1. Kohima District, Nagaland
  2. Aizawl District, Mizoram

Source:
  Copernicus DEM GLO-30 (Public Registry of Open Data on AWS)
  Host: https://copernicus-dem-30m.s3.amazonaws.com/
  Product: Copernicus_DSM_COG_10 (Cloud Optimized GeoTIFF, 30m resolution, WGS 84, EGM2008 datum)

Target Tiles:
  - Kohima:
      Copernicus_DSM_COG_10_N25_00_E093_00_DEM.tif
      Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif
      Copernicus_DSM_COG_10_N26_00_E093_00_DEM.tif
      Copernicus_DSM_COG_10_N26_00_E094_00_DEM.tif
  - Aizawl:
      Copernicus_DSM_COG_10_N23_00_E092_00_DEM.tif
      Copernicus_DSM_COG_10_N23_00_E093_00_DEM.tif
      Copernicus_DSM_COG_10_N24_00_E092_00_DEM.tif
      Copernicus_DSM_COG_10_N24_00_E093_00_DEM.tif

Outputs:
  data/terrain/raw/<tile_name>.tif
"""

import json
import os
import sys
import time
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TERRAIN_DIR = DATA_DIR / "terrain"
RAW_DIR = TERRAIN_DIR / "raw"

BASE_S3_URL = "https://copernicus-dem-30m.s3.amazonaws.com"

TILES = [
    # Kohima District coverage (25°N - 27°N, 93°E - 95°E)
    "Copernicus_DSM_COG_10_N25_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N25_00_E094_00_DEM",
    "Copernicus_DSM_COG_10_N26_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N26_00_E094_00_DEM",
    # Aizawl District coverage (23°N - 25°N, 92°E - 94°E)
    "Copernicus_DSM_COG_10_N23_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N23_00_E093_00_DEM",
    "Copernicus_DSM_COG_10_N24_00_E092_00_DEM",
    "Copernicus_DSM_COG_10_N24_00_E093_00_DEM",
]


def download_tile(tile_name: str, target_dir: Path) -> Path:
    target_path = target_dir / f"{tile_name}.tif"
    url = f"{BASE_S3_URL}/{tile_name}/{tile_name}.tif"

    if target_path.exists() and target_path.stat().st_size > 1_000_000:
        print(f"[INFO] Using cached tile: {target_path.name} ({target_path.stat().st_size / 1e6:.2f} MB)")
        return target_path

    print(f"[INFO] Downloading {tile_name} from {url}...")
    start_t = time.time()
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    total_size = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(target_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

    elapsed = time.time() - start_t
    print(
        f"[SUCCESS] Downloaded {target_path.name} "
        f"({downloaded / 1e6:.2f} MB in {elapsed:.1f}s, {downloaded / (elapsed * 1e6):.2f} MB/s)"
    )
    return target_path


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("NER Safe — Copernicus DEM GLO-30 Raw Tile Ingestion")
    print("Source: AWS Open Data (copernicus-dem-30m.s3.amazonaws.com)")
    print(f"Target Directory: {RAW_DIR.relative_to(BASE_DIR)}")
    print(f"Total Required Tiles: {len(TILES)}")
    print("=" * 65)

    downloaded_paths = []
    metadata = {
        "dataset_name": "Copernicus DEM GLO-30",
        "provider": "European Space Agency (ESA) / Airbus Defence and Space",
        "hosting": "AWS Open Data Registry (copernicus-dem-30m)",
        "spatial_resolution": "30 meters (1.0 arc second)",
        "vertical_datum": "EGM2008 (Earth Gravitational Model 2008)",
        "horizontal_crs": "EPSG:4326 (WGS 84)",
        "acquisition_date": "2026-09-16",
        "tiles": {},
    }

    for tile in TILES:
        path = download_tile(tile, RAW_DIR)
        downloaded_paths.append(path)
        metadata["tiles"][tile] = {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "size_mb": round(path.stat().st_size / 1e6, 2),
        }

    meta_file = RAW_DIR / "copernicus_dem_metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    total_mb = sum(p.stat().st_size for p in downloaded_paths) / 1e6
    print("\n" + "=" * 65)
    print(f"[SUCCESS] All {len(TILES)} tiles ready ({total_mb:.2f} MB total).")
    print(f"Metadata saved to: {meta_file.relative_to(BASE_DIR)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
