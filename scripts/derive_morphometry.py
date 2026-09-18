"""
derive_morphometry.py
=====================
Derives morphometric terrain layers from clipped Copernicus DEM GLO-30
rasters for the two NER Safe pilot districts (Kohima and Aizawl).

Computed Layers (all on the UTM Zone 46N metric grid at 30 m):
  1. Slope         — degrees (0° – 90°), Horn (1981) 3×3 finite difference
  2. Aspect        — degrees (0° – 360° clockwise from north; -1 for flat)
  3. Curvature     — total curvature (100 × m⁻¹), Zevenbergen & Thorne (1987)
  4. TWI           — Topographic Wetness Index: ln(a / tan β)

References:
  - Horn, B.K.P. (1981). Hill shading and the reflectance map.
    Proceedings of the IEEE, 69(1), 14–47.
  - Zevenbergen, L.W. & Thorne, C.R. (1987). Quantitative analysis of
    land surface topography. Earth Surface Processes and Landforms, 12, 47–56.
  - Beven, K.J. & Kirkby, M.J. (1979). A physically based, variable
    contributing area model of basin hydrology. Hydrological Sciences
    Bulletin, 24, 43–69.

Outputs are written as DEFLATE-compressed Float32 GeoTIFFs to data/terrain/.
"""

import sys
import time
from pathlib import Path
import numpy as np
import rasterio

BASE_DIR = Path(__file__).resolve().parent.parent
TERRAIN_DIR = BASE_DIR / "data" / "terrain"
NODATA = -9999.0

DISTRICTS = [
    {"name": "kohima",  "dem": TERRAIN_DIR / "kohima_dem.tif"},
    {"name": "aizawl",  "dem": TERRAIN_DIR / "aizawl_dem.tif"},
]


# ---------------------------------------------------------------------------
#  Horn (1981) 3×3 slope & aspect
# ---------------------------------------------------------------------------

def compute_slope_aspect(elevation: np.ndarray, cell_size: float):
    """
    Compute slope (degrees) and aspect (degrees clockwise from north)
    using Horn's (1981) 3×3 finite-difference method.

    Parameters
    ----------
    elevation : np.ndarray (2-D, float)
        Elevation grid in metres. NoData cells must be NaN.
    cell_size : float
        Pixel size in metres (assumes square pixels).

    Returns
    -------
    slope : np.ndarray   — degrees, 0–90
    aspect : np.ndarray  — degrees, 0–360 clockwise from N; -1 for flat
    """
    # Pad edges with reflect so derivatives exist at boundary pixels
    z = np.pad(elevation, 1, mode="reflect")

    # Horn weights for dz/dx and dz/dy
    #   a b c       +1 0 -1        +1 +2 +1
    #   d e f  dx = +2 0 -2   dy = 0   0  0
    #   g h i       +1 0 -1       -1 -2 -1
    a = z[:-2, :-2]; b = z[:-2, 1:-1]; c = z[:-2, 2:]
    d = z[1:-1, :-2];                   f = z[1:-1, 2:]
    g = z[2:, :-2];  h = z[2:, 1:-1];  i = z[2:, 2:]

    dz_dx = ((c + 2*f + i) - (a + 2*d + g)) / (8.0 * cell_size)
    dz_dy = ((g + 2*h + i) - (a + 2*b + c)) / (8.0 * cell_size)

    # Slope in degrees
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)

    # Aspect in degrees clockwise from north
    aspect_rad = np.arctan2(-dz_dy, dz_dx)       # math convention
    aspect_deg = np.degrees(aspect_rad)
    # Convert from math-convention (east=0, CCW+) to compass (north=0, CW+)
    aspect_deg = (90.0 - aspect_deg) % 360.0

    # Mark flat pixels (slope ≈ 0) with -1
    flat_mask = slope_deg < 0.001
    aspect_deg[flat_mask] = -1.0

    return slope_deg, aspect_deg


# ---------------------------------------------------------------------------
#  Zevenbergen & Thorne (1987) curvature
# ---------------------------------------------------------------------------

def compute_curvature(elevation: np.ndarray, cell_size: float):
    """
    Compute total (mean) curvature using the Zevenbergen & Thorne (1987)
    quadratic surface fit.

    total_curvature = -2 * (D + E) * 100   (units: 100 × m⁻¹)

    where
        D = ((z4 + z6) / 2 - z5) / L²
        E = ((z2 + z8) / 2 - z5) / L²

    Positive curvature = convex upward (ridge-like)
    Negative curvature = concave upward (valley-like)

    Parameters
    ----------
    elevation : np.ndarray (2-D)
    cell_size : float

    Returns
    -------
    curvature : np.ndarray
    """
    z = np.pad(elevation, 1, mode="reflect")
    L2 = cell_size * cell_size

    z2 = z[:-2, 1:-1]   # north
    z4 = z[1:-1, :-2]   # west
    z5 = z[1:-1, 1:-1]  # centre
    z6 = z[1:-1, 2:]    # east
    z8 = z[2:, 1:-1]    # south

    D = ((z4 + z6) / 2.0 - z5) / L2
    E = ((z2 + z8) / 2.0 - z5) / L2
    curvature = -2.0 * (D + E) * 100.0   # scale to 100 × m⁻¹

    return curvature


# ---------------------------------------------------------------------------
#  TWI — Topographic Wetness Index (D-infinity approximation)
# ---------------------------------------------------------------------------

def compute_twi(elevation: np.ndarray, slope_deg: np.ndarray, cell_size: float):
    """
    Compute the Topographic Wetness Index:

        TWI = ln(SCA / tan β)

    where SCA is the specific catchment area (m² per unit contour length)
    estimated via a single-flow-direction (D8) flow-accumulation algorithm,
    and β is the local slope angle.

    A minimum slope of 0.001 radians (~0.06°) is enforced to avoid ln(0).

    Parameters
    ----------
    elevation : np.ndarray (2-D)
    slope_deg : np.ndarray (2-D)
    cell_size : float

    Returns
    -------
    twi : np.ndarray
    """
    rows, cols = elevation.shape
    slope_rad = np.radians(slope_deg)

    # D8 flow accumulation --------------------------------------------------
    # Sort cells by descending elevation for single-pass accumulation
    elev_flat = elevation.copy().ravel()
    # Replace NaN with a very low value so they are processed last
    nan_mask = np.isnan(elev_flat)
    elev_flat[nan_mask] = -1e10
    sorted_indices = np.argsort(-elev_flat)  # highest first

    accumulation = np.ones((rows, cols), dtype=np.float64)  # count self
    flat_elev = elevation.ravel()

    # 8-connected neighbour offsets: (row_offset, col_offset)
    offsets = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),          (0, 1),
               (1, -1),  (1, 0), (1, 1)]
    # Distance weights for diagonal vs cardinal neighbours
    dist_weights = [1.414, 1.0, 1.414,
                    1.0,        1.0,
                    1.414, 1.0, 1.414]

    for idx in sorted_indices:
        r, c = divmod(int(idx), cols)
        if np.isnan(elevation[r, c]):
            continue

        # Find steepest downslope neighbour
        max_drop = 0.0
        target_r, target_c = -1, -1
        for (dr, dc), dw in zip(offsets, dist_weights):
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and not np.isnan(elevation[nr, nc]):
                drop = (elevation[r, c] - elevation[nr, nc]) / (dw * cell_size)
                if drop > max_drop:
                    max_drop = drop
                    target_r, target_c = nr, nc

        if target_r >= 0:
            accumulation[target_r, target_c] += accumulation[r, c]

    # Specific Catchment Area: SCA = accumulation * cell_size  (m² per m)
    sca = accumulation * cell_size

    # Enforce minimum slope to avoid ln(0 / inf)
    tan_beta = np.tan(np.clip(slope_rad, 0.001, None))

    twi = np.log(sca / tan_beta)

    return twi


# ---------------------------------------------------------------------------
#  Write a derivative raster with the same georeference as the source DEM
# ---------------------------------------------------------------------------

def write_raster(data: np.ndarray, reference_profile: dict,
                 output_path: Path, nan_to_nodata: bool = True):
    """Write a single-band Float32 GeoTIFF with DEFLATE compression."""
    profile = reference_profile.copy()
    profile.update({
        "dtype": "float32",
        "count": 1,
        "nodata": NODATA,
        "compress": "deflate",
    })
    out = data.astype(np.float32).copy()
    if nan_to_nodata:
        out[np.isnan(out)] = NODATA
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(out[np.newaxis, :, :])
    print(f"       Written: {output_path.relative_to(BASE_DIR)}  "
          f"({output_path.stat().st_size / 1e6:.2f} MB)")


# ---------------------------------------------------------------------------
#  Main per-district processing
# ---------------------------------------------------------------------------

def process_district(name: str, dem_path: Path):
    """Derive all morphometric layers for one district DEM."""
    print(f"\n{'='*65}")
    print(f"  Processing morphometry for {name.upper()} district")
    print(f"{'='*65}")
    t0 = time.time()

    # Read clipped DEM
    with rasterio.open(dem_path) as src:
        elev = src.read(1).astype(np.float64)
        profile = src.profile
        transform = src.transform
        nodata_val = src.nodata

    # Pixel size from the affine transform (should be 30 m)
    cell_size = abs(transform.a)
    print(f"  DEM loaded — {elev.shape[1]}×{elev.shape[0]} pixels, "
          f"cell size = {cell_size:.1f} m")

    # Replace NoData with NaN for computation
    if nodata_val is not None:
        elev[elev == nodata_val] = np.nan

    valid_mask = ~np.isnan(elev)
    n_valid = int(valid_mask.sum())
    n_total = elev.size
    print(f"  Valid pixels: {n_valid:,} / {n_total:,} "
          f"({n_valid / n_total * 100:.1f}%)")

    # 1. Slope & Aspect
    print("\n  [1/4] Computing slope & aspect (Horn 1981)...")
    slope, aspect = compute_slope_aspect(elev, cell_size)
    slope[~valid_mask] = np.nan
    aspect[~valid_mask] = np.nan

    v_slope = slope[valid_mask]
    print(f"       Slope  — min: {np.nanmin(v_slope):.2f}°  "
          f"max: {np.nanmax(v_slope):.2f}°  mean: {np.nanmean(v_slope):.2f}°")

    # 2. Curvature
    print("  [2/4] Computing curvature (Zevenbergen & Thorne 1987)...")
    curvature = compute_curvature(elev, cell_size)
    curvature[~valid_mask] = np.nan

    v_curv = curvature[valid_mask]
    print(f"       Curvature — min: {np.nanmin(v_curv):.4f}  "
          f"max: {np.nanmax(v_curv):.4f}  mean: {np.nanmean(v_curv):.4f}")

    # 3. TWI
    print("  [3/4] Computing TWI (D8 flow accumulation)...")
    twi = compute_twi(elev, slope, cell_size)
    twi[~valid_mask] = np.nan

    v_twi = twi[valid_mask]
    print(f"       TWI — min: {np.nanmin(v_twi):.2f}  "
          f"max: {np.nanmax(v_twi):.2f}  mean: {np.nanmean(v_twi):.2f}")

    # 4. Write outputs
    print("  [4/4] Writing output rasters...")
    prefix = name.lower()
    write_raster(slope,     profile, TERRAIN_DIR / f"{prefix}_slope.tif")
    write_raster(aspect,    profile, TERRAIN_DIR / f"{prefix}_aspect.tif")
    write_raster(curvature, profile, TERRAIN_DIR / f"{prefix}_curvature.tif")
    write_raster(twi,       profile, TERRAIN_DIR / f"{prefix}_twi.tif")

    elapsed = time.time() - t0
    print(f"\n  [OK] {name.upper()} morphometry completed in {elapsed:.1f}s")
    print(f"{'='*65}")

    return {
        "district": name,
        "valid_pixels": n_valid,
        "slope_min": float(np.nanmin(v_slope)),
        "slope_max": float(np.nanmax(v_slope)),
        "slope_mean": float(np.nanmean(v_slope)),
        "curvature_min": float(np.nanmin(v_curv)),
        "curvature_max": float(np.nanmax(v_curv)),
        "twi_min": float(np.nanmin(v_twi)),
        "twi_max": float(np.nanmax(v_twi)),
        "twi_mean": float(np.nanmean(v_twi)),
        "elapsed_s": elapsed,
    }


def main():
    print("NER Safe — Morphometric Terrain Feature Derivation")
    print(f"Source: Copernicus DEM GLO-30 (clipped, UTM 46N @ 30 m)")
    print(f"Outputs: data/terrain/<district>_<layer>.tif\n")

    results = []
    for dist in DISTRICTS:
        if not dist["dem"].exists():
            print(f"[ERROR] DEM not found: {dist['dem']}")
            print("        Run scripts/clip_rasters.py first.")
            sys.exit(1)
        results.append(process_district(dist["name"], dist["dem"]))

    # Summary table
    print(f"\n{'='*65}")
    print("SUMMARY")
    print(f"{'='*65}")
    for r in results:
        print(f"  {r['district'].upper()}:")
        print(f"    Slope  : {r['slope_min']:.2f}° – {r['slope_max']:.2f}° "
              f"(mean {r['slope_mean']:.2f}°)")
        print(f"    Curvature: {r['curvature_min']:.4f} – {r['curvature_max']:.4f}")
        print(f"    TWI    : {r['twi_min']:.2f} – {r['twi_max']:.2f} "
              f"(mean {r['twi_mean']:.2f})")
        print(f"    Time   : {r['elapsed_s']:.1f}s")
    print(f"{'='*65}")
    print("[SUCCESS] All morphometric layers derived successfully.")


if __name__ == "__main__":
    main()
