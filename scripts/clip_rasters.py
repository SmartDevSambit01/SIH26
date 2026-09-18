"""
clip_rasters.py
===============
Merges and clips raw Copernicus DEM GLO-30 elevation rasters to the official
boundaries of the two NER Safe pilot districts:
  1. Kohima District, Nagaland
  2. Aizawl District, Mizoram

Processing steps:
  1. Identifies and mosaics intersecting 1° x 1° Copernicus DEM GLO-30 tiles.
  2. Reprojects to the regional metric standard: UTM Zone 46N (EPSG:32646)
     with 30m x 30m pixel resolution using bilinear resampling.
  3. Masks and clips strictly to the official district boundary GeoJSON polygon.
  4. Preserves NoData (-9999.0) and geospatial metadata.
  5. Saves compressed GeoTIFFs (Float32 with DEFLATE compression) to:
     - data/terrain/kohima_dem.tif
     - data/terrain/aizawl_dem.tif
"""

import json
import os
import sys
import time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import shape
import pyproj
from shapely.ops import transform

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
TERRAIN_DIR = DATA_DIR / "terrain"
RAW_DIR = TERRAIN_DIR / "raw"

TARGET_CRS = "EPSG:32646"  # UTM Zone 46N
TARGET_RESOLUTION = 30.0   # 30 meters
NODATA_VALUE = -9999.0

DISTRICTS = [
    {
        "name": "Kohima",
        "state": "Nagaland",
        "boundary_file": BOUNDARIES_DIR / "kohima_district.geojson",
        "output_file": TERRAIN_DIR / "kohima_dem.tif",
        "tile_prefixes": [
            "Copernicus_DSM_COG_10_N25_00_E093_00_DEM",
            "Copernicus_DSM_COG_10_N25_00_E094_00_DEM",
            "Copernicus_DSM_COG_10_N26_00_E093_00_DEM",
            "Copernicus_DSM_COG_10_N26_00_E094_00_DEM",
        ],
    },
    {
        "name": "Aizawl",
        "state": "Mizoram",
        "boundary_file": BOUNDARIES_DIR / "aizawl_district.geojson",
        "output_file": TERRAIN_DIR / "aizawl_dem.tif",
        "tile_prefixes": [
            "Copernicus_DSM_COG_10_N23_00_E092_00_DEM",
            "Copernicus_DSM_COG_10_N23_00_E093_00_DEM",
            "Copernicus_DSM_COG_10_N24_00_E092_00_DEM",
            "Copernicus_DSM_COG_10_N24_00_E093_00_DEM",
        ],
    },
]

# Coordinate transformation WGS84 -> UTM Zone 46N for Shapely geometries
wgs84_to_utm46n = pyproj.Transformer.from_crs("EPSG:4326", TARGET_CRS, always_xy=True).transform


def clip_district_dem(dist_cfg: dict) -> Path:
    name = dist_cfg["name"]
    output_path = dist_cfg["output_file"]
    boundary_path = dist_cfg["boundary_file"]

    print(f"\n[INFO] Processing DEM for {name} District ({dist_cfg['state']})...")
    start_time = time.time()

    if not boundary_path.exists():
        raise FileNotFoundError(f"Boundary file not found: {boundary_path}")

    # Load district boundary geometry in WGS 84
    with open(boundary_path, "r", encoding="utf-8") as f:
        b_data = json.load(f)
    district_geom_wgs84 = shape(b_data["features"][0]["geometry"])

    # Transform boundary to UTM Zone 46N
    district_geom_utm = transform(wgs84_to_utm46n, district_geom_wgs84)

    # 1. Locate required raw tiles
    tile_files = []
    for prefix in dist_cfg["tile_prefixes"]:
        tile_path = RAW_DIR / f"{prefix}.tif"
        if not tile_path.exists():
            raise FileNotFoundError(
                f"Missing raw DEM tile: {tile_path.name}. "
                f"Please run 'python scripts/download_dem.py' first."
            )
        tile_files.append(tile_path)

    print(f"       Mosaicing {len(tile_files)} Copernicus DEM tiles...")
    opened_srcs = [rasterio.open(p) for p in tile_files]

    try:
        # Merge tiles in their native CRS (EPSG:4326)
        mosaic_arr, mosaic_transform = merge(opened_srcs, nodata=NODATA_VALUE)
        mosaic_crs = opened_srcs[0].crs
    finally:
        for s in opened_srcs:
            s.close()

    print(f"       Native mosaic dimensions: {mosaic_arr.shape[2]} cols x {mosaic_arr.shape[1]} rows")

    # 2. Reproject to UTM Zone 46N (EPSG:32646) at 30m resolution
    print(f"       Reprojecting mosaic to {TARGET_CRS} at {TARGET_RESOLUTION}m resolution...")
    src_height, src_width = mosaic_arr.shape[1], mosaic_arr.shape[2]
    from rasterio.transform import array_bounds
    mosaic_bounds = array_bounds(src_height, src_width, mosaic_transform)

    dst_transform, dst_width, dst_height = calculate_default_transform(
        mosaic_crs,
        TARGET_CRS,
        src_width,
        src_height,
        *mosaic_bounds,
        resolution=(TARGET_RESOLUTION, TARGET_RESOLUTION),
    )

    reprojected_arr = np.full((1, dst_height, dst_width), NODATA_VALUE, dtype=np.float32)

    reproject(
        source=mosaic_arr,
        destination=reprojected_arr,
        src_transform=mosaic_transform,
        src_crs=mosaic_crs,
        dst_transform=dst_transform,
        dst_crs=TARGET_CRS,
        resampling=Resampling.bilinear,
        src_nodata=NODATA_VALUE,
        dst_nodata=NODATA_VALUE,
    )

    # 3. Clip reprojected raster with the district boundary in UTM Zone 46N
    print(f"       Clipping precisely to official {name} district polygon...")

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": NODATA_VALUE,
        "width": dst_width,
        "height": dst_height,
        "count": 1,
        "crs": TARGET_CRS,
        "transform": dst_transform,
        "compress": "deflate",
    }

    from rasterio.io import MemoryFile
    with MemoryFile() as memfile:
        with memfile.open(**profile) as mem_dst:
            mem_dst.write(reprojected_arr)
        with memfile.open() as src:
            clipped_data, clipped_transform = mask(
                src,
                [district_geom_utm],
                crop=True,
                filled=True,
                nodata=NODATA_VALUE,
            )
            clipped_profile = src.profile.copy()
            clipped_profile.update(
                {
                    "height": clipped_data.shape[1],
                    "width": clipped_data.shape[2],
                    "transform": clipped_transform,
                    "compress": "deflate",
                }
            )

    # Write final clipped DEM GeoTIFF
    with rasterio.open(output_path, "w", **clipped_profile) as dst:
        dst.write(clipped_data)

    # 4. Statistics & Validation
    valid_mask = (clipped_data[0] != NODATA_VALUE) & ~np.isnan(clipped_data[0])
    valid_elevations = clipped_data[0][valid_mask]
    total_pixels = clipped_data[0].size
    valid_count = valid_elevations.size
    nodata_count = total_pixels - valid_count

    min_elev = float(np.min(valid_elevations)) if valid_count > 0 else 0.0
    max_elev = float(np.max(valid_elevations)) if valid_count > 0 else 0.0
    mean_elev = float(np.mean(valid_elevations)) if valid_count > 0 else 0.0
    file_size_mb = output_path.stat().st_size / 1e6
    elapsed = time.time() - start_time

    print(f"[OK] Completed {name} DEM:")
    print(f"     Output File      : {output_path.relative_to(BASE_DIR)}")
    print(f"     Dimensions       : {clipped_data.shape[2]} x {clipped_data.shape[1]} pixels")
    print(f"     CRS              : {TARGET_CRS} (UTM Zone 46N)")
    print(f"     Resolution       : {TARGET_RESOLUTION}m x {TARGET_RESOLUTION}m")
    print(f"     Total Pixels     : {total_pixels:,}")
    print(f"     Valid Pixels     : {valid_count:,} ({valid_count / total_pixels * 100:.1f}%)")
    print(f"     NoData Pixels    : {nodata_count:,} ({nodata_count / total_pixels * 100:.1f}%)")
    print(f"     Elevation Min    : {min_elev:.1f} m ASL")
    print(f"     Elevation Max    : {max_elev:.1f} m ASL")
    print(f"     Elevation Mean   : {mean_elev:.1f} m ASL")
    print(f"     File Size        : {file_size_mb:.2f} MB")
    print(f"     Processing Time  : {elapsed:.1f}s")

    return output_path


def main():
    TERRAIN_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("NER Safe — Real DEM Clipping Pipeline")
    print(f"Source: Copernicus DEM GLO-30 (ESA / Airbus)")
    print(f"Target CRS: {TARGET_CRS} | Target Pixel Size: {TARGET_RESOLUTION}m")
    print("=" * 65)

    for dist_cfg in DISTRICTS:
        clip_district_dem(dist_cfg)

    print("\n" + "=" * 65)
    print("[SUCCESS] District DEM clipping completed successfully.")
    print("=" * 65)


if __name__ == "__main__":
    main()
