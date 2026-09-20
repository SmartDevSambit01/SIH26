"""
derive_hydrology.py
====================
Derives DEM-based hydrological layers from the clipped Copernicus DEM GLO-30
rasters for the two NER Safe pilot districts (Kohima and Aizawl), on the same
UTM Zone 46N 30 m grid used by derive_morphometry.py.

Computed Layers:
  1. Flow direction    — D8 steepest-descent direction (0-7, -1 at outlets)
  2. Flow accumulation — upstream contributing cell count (D8)
  3. Stream network     — boolean mask, contributing area >= STREAM_THRESHOLD_M2
  4. Distance to drainage — Euclidean distance (m) to nearest stream cell
  5. HAND               — Height Above Nearest Drainage (m)

Method:
  - Depression filling: Priority-Flood + epsilon (Barnes, Lehman & Mulla, 2014,
    "Priority-flood: An optimal depression-filling and watershed-labeling
    algorithm for digital elevation models", Computers & Geosciences 62).
    Guarantees every interior cell has a strictly downhill D8 path to the
    raster edge/nodata boundary (treated as the drainage outlet), removing
    the spurious pits that would otherwise trap flow accumulation.
  - Flow accumulation: cells processed in descending filled-elevation order,
    each cell's accumulated count added to its single D8 downstream neighbor
    (standard D8 accumulation, e.g. O'Callaghan & Mark, 1984).
  - HAND: Rennó et al. (2008), "HAND, a new terrain descriptor using SRTM-DEM:
    Mapping terra-firme rainforest environments in Amazonia". Computed via
    pointer-jumping (path compression) over the D8 flow-direction functional
    graph so every cell's nearest-downstream-stream elevation is resolved in
    O(log(max flow-path length)) vectorized rounds instead of a Python loop
    over millions of pixels.

STRICT SCIENTIFIC RESTRICTIONS:
  - This produces STATIC flow-accumulation/HAND evidence only. It is NOT a
    calibrated flood-depth or inundation model (PRD.md Section 24, 33).
  - Stream threshold is a documented, adjustable prototype parameter, not an
    authoritative hydrography source.

Outputs (DEFLATE-compressed rasters to data/terrain/):
  {prefix}_flowdir.tif    int16   (0-7 D8 direction code, -1 = outlet/nodata)
  {prefix}_flowacc.tif    float32 (contributing cell count)
  {prefix}_stream.tif     uint8   (1 = stream cell, 0 = hillslope)
  {prefix}_dist2drain.tif float32 (meters)
  {prefix}_hand.tif       float32 (meters)
"""

import sys
import time
import heapq
from pathlib import Path
import numpy as np

try:
    import rasterio
    from scipy.ndimage import distance_transform_edt
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("        pip install rasterio scipy")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
TERRAIN_DIR = BASE_DIR / "data" / "terrain"
NODATA = -9999.0

# Contributing area threshold for a cell to be classified as a stream, per
# PRD.md Section 32/33 guidance that this is a prototype, documented parameter.
STREAM_THRESHOLD_M2 = 500_000.0  # 0.5 km^2

DISTRICTS = [
    {"name": "kohima", "dem": TERRAIN_DIR / "kohima_dem.tif"},
    {"name": "aizawl", "dem": TERRAIN_DIR / "aizawl_dem.tif"},
]

# D8 neighbor offsets: index -> (drow, dcol), matching a fixed direction code.
D8_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def priority_flood_fill(dem: np.ndarray, nodata_mask: np.ndarray) -> np.ndarray:
    """Barnes et al. (2014) Priority-Flood + epsilon depression filling.

    Cells on the raster edge, or adjacent to a nodata cell, are seeded as
    drainage outlets. Every other cell is guaranteed a strictly downhill
    (by at least EPS) D8 path to an outlet after filling.
    """
    rows, cols = dem.shape
    filled = dem.astype(np.float64).copy()
    closed = nodata_mask.copy()
    heap = []
    counter = 0
    EPS = 1e-6

    valid = ~nodata_mask
    # Seed: valid cells on the raster edge or bordering a nodata cell.
    edge_mask = np.zeros((rows, cols), dtype=bool)
    edge_mask[0, :] = True
    edge_mask[-1, :] = True
    edge_mask[:, 0] = True
    edge_mask[:, -1] = True

    nodata_adjacent = np.zeros((rows, cols), dtype=bool)
    padded = np.pad(nodata_mask, 1, mode="constant", constant_values=True)
    for dr, dc in D8_OFFSETS:
        shifted = padded[1 + dr: 1 + dr + rows, 1 + dc: 1 + dc + cols]
        nodata_adjacent |= shifted

    seed_mask = valid & (edge_mask | nodata_adjacent)
    seed_rows, seed_cols = np.nonzero(seed_mask)
    for i, j in zip(seed_rows.tolist(), seed_cols.tolist()):
        heapq.heappush(heap, (filled[i, j], counter, i, j))
        counter += 1
        closed[i, j] = True

    while heap:
        elev, _, i, j = heapq.heappop(heap)
        for dr, dc in D8_OFFSETS:
            ni, nj = i + dr, j + dc
            if 0 <= ni < rows and 0 <= nj < cols and not closed[ni, nj]:
                closed[ni, nj] = True
                if filled[ni, nj] <= elev:
                    filled[ni, nj] = elev + EPS
                heapq.heappush(heap, (filled[ni, nj], counter, ni, nj))
                counter += 1

    return filled


def compute_flow_direction(filled: np.ndarray, nodata_mask: np.ndarray, pixel_size: float) -> np.ndarray:
    """D8 steepest-descent direction. -1 marks nodata cells or local outlets
    (edge cells / cells with no lower neighbor after filling)."""
    rows, cols = filled.shape
    flow_dir = np.full((rows, cols), -1, dtype=np.int16)

    padded = np.pad(filled, 1, mode="constant", constant_values=np.inf)
    padded_nodata = np.pad(nodata_mask, 1, mode="constant", constant_values=True)

    best_drop = np.zeros((rows, cols), dtype=np.float64)
    for code, (dr, dc) in enumerate(D8_OFFSETS):
        dist = pixel_size * (np.sqrt(2.0) if dr != 0 and dc != 0 else 1.0)
        neighbor = padded[1 + dr: 1 + dr + rows, 1 + dc: 1 + dc + cols]
        neighbor_nodata = padded_nodata[1 + dr: 1 + dr + rows, 1 + dc: 1 + dc + cols]
        drop = np.where(neighbor_nodata, -np.inf, (filled - neighbor) / dist)
        better = drop > best_drop  # best_drop starts at 0, so code 0 requires drop > 0 too
        mask = better & ~nodata_mask
        flow_dir[mask] = code
        best_drop = np.where(mask, drop, best_drop)

    flow_dir[nodata_mask] = -1
    return flow_dir


def compute_flow_accumulation(filled: np.ndarray, flow_dir: np.ndarray, nodata_mask: np.ndarray) -> np.ndarray:
    """D8 flow accumulation via descending-elevation processing order
    (O'Callaghan & Mark, 1984)."""
    rows, cols = filled.shape
    n = rows * cols
    acc = np.ones((rows, cols), dtype=np.float64)
    acc[nodata_mask] = 0.0

    flat_filled = filled.ravel()
    order = np.argsort(-flat_filled)  # descending elevation

    downstream_flat = np.full(n, -1, dtype=np.int64)
    rows_idx, cols_idx = np.divmod(np.arange(n), cols)
    for code, (dr, dc) in enumerate(D8_OFFSETS):
        code_mask = (flow_dir.ravel() == code)
        ni = rows_idx[code_mask] + dr
        nj = cols_idx[code_mask] + dc
        valid = (ni >= 0) & (ni < rows) & (nj >= 0) & (nj < cols)
        src_idx = np.nonzero(code_mask)[0][valid]
        downstream_flat[src_idx] = ni[valid] * cols + nj[valid]

    flat_acc = acc.ravel()
    flat_nodata = nodata_mask.ravel()
    for idx in order.tolist():
        if flat_nodata[idx]:
            continue
        d = downstream_flat[idx]
        if d != -1 and not flat_nodata[d]:
            flat_acc[d] += flat_acc[idx]

    return flat_acc.reshape(rows, cols)


def compute_hand(filled: np.ndarray, flow_dir: np.ndarray, stream_mask: np.ndarray, nodata_mask: np.ndarray) -> np.ndarray:
    """HAND via pointer-jumping over the D8 flow-direction functional graph.

    Every cell's `next` pointer is its D8 downstream neighbor (or itself if
    it is a stream cell or has no downstream neighbor, i.e. a terminal).
    Repeated path-doubling resolves each cell's nearest-downstream stream
    elevation in O(log(max path length)) vectorized rounds.
    """
    rows, cols = filled.shape
    n = rows * cols
    idx_grid = np.arange(n).reshape(rows, cols)
    rows_idx, cols_idx = np.divmod(np.arange(n), cols)

    nxt = idx_grid.ravel().copy()
    flow_dir_flat = flow_dir.ravel()
    for code, (dr, dc) in enumerate(D8_OFFSETS):
        code_mask = (flow_dir_flat == code)
        ni = rows_idx[code_mask] + dr
        nj = cols_idx[code_mask] + dc
        valid = (ni >= 0) & (ni < rows) & (nj >= 0) & (nj < cols)
        src_idx = np.nonzero(code_mask)[0][valid]
        nxt[src_idx] = ni[valid] * cols + nj[valid]

    is_terminal = stream_mask | (flow_dir == -1)
    nxt_flat = nxt
    terminal_flat = is_terminal.ravel()
    # Every terminal cell points to itself — it IS the reference elevation.
    self_idx = idx_grid.ravel()
    nxt_flat[terminal_flat] = self_idx[terminal_flat]

    ref_elev = filled.ravel().copy()
    ptr = nxt_flat.copy()
    max_path = rows + cols
    iterations = max(1, int(np.ceil(np.log2(max(max_path, 2)))) + 2)
    for _ in range(iterations):
        ref_elev = np.where(terminal_flat, ref_elev, ref_elev[ptr])
        ptr = ptr[ptr]

    hand = filled.ravel() - ref_elev
    hand = hand.reshape(rows, cols)
    hand[nodata_mask] = np.nan
    hand[hand < 0] = 0.0  # numerical noise guard; HAND is non-negative by definition
    return hand


def write_raster(path: Path, data: np.ndarray, profile: dict, dtype: str, nodata_value):
    out_profile = profile.copy()
    out_profile.update(dtype=dtype, nodata=nodata_value, compress="DEFLATE", predictor=2 if "float" in dtype else 1)
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(data.astype(dtype), 1)


def process_district(dist_cfg: dict):
    name = dist_cfg["name"]
    dem_path = dist_cfg["dem"]

    print(f"\n{'='*65}")
    print(f"  Deriving hydrology for {name} district")
    print(f"{'='*65}")
    t0 = time.time()

    if not dem_path.exists():
        print(f"[ERROR] DEM not found: {dem_path}")
        sys.exit(1)

    with rasterio.open(dem_path) as src:
        dem = src.read(1).astype(np.float64)
        profile = src.profile
        pixel_size = abs(src.res[0])

    nodata_mask = (dem == NODATA) | np.isnan(dem)
    pixel_area = pixel_size * pixel_size

    print(f"  Grid: {dem.shape[1]}x{dem.shape[0]} @ {pixel_size:.0f} m, "
          f"{np.count_nonzero(~nodata_mask):,} valid cells")

    t1 = time.time()
    filled = priority_flood_fill(dem, nodata_mask)
    print(f"  [1/4] Depression filling complete ({time.time()-t1:.1f}s)")

    t1 = time.time()
    flow_dir = compute_flow_direction(filled, nodata_mask, pixel_size)
    print(f"  [2/4] Flow direction complete ({time.time()-t1:.1f}s)")

    t1 = time.time()
    flow_acc = compute_flow_accumulation(filled, flow_dir, nodata_mask)
    print(f"  [3/4] Flow accumulation complete ({time.time()-t1:.1f}s)")

    stream_threshold_cells = STREAM_THRESHOLD_M2 / pixel_area
    stream_mask = (flow_acc >= stream_threshold_cells) & ~nodata_mask
    n_stream = int(np.count_nonzero(stream_mask))
    print(f"        Stream cells: {n_stream:,} "
          f"(threshold {STREAM_THRESHOLD_M2/1e6:.2f} km^2 = {stream_threshold_cells:.0f} cells)")

    if n_stream == 0:
        print(f"[WARN] No stream cells found for {name} — HAND/distance will be all-NaN. "
              f"Consider lowering STREAM_THRESHOLD_M2.")

    dist2drain = distance_transform_edt(~stream_mask, sampling=(pixel_size, pixel_size)).astype(np.float32)
    dist2drain[nodata_mask] = np.nan

    t1 = time.time()
    hand = compute_hand(filled, flow_dir, stream_mask, nodata_mask)
    print(f"  [4/4] HAND complete ({time.time()-t1:.1f}s)")

    flow_acc_out = flow_acc.astype(np.float32)
    flow_acc_out[nodata_mask] = NODATA

    write_raster(TERRAIN_DIR / f"{name}_flowdir.tif", flow_dir, profile, "int16", -1)
    write_raster(TERRAIN_DIR / f"{name}_flowacc.tif", flow_acc_out, profile, "float32", NODATA)
    write_raster(TERRAIN_DIR / f"{name}_stream.tif", stream_mask.astype(np.uint8), profile, "uint8", 255)
    write_raster(TERRAIN_DIR / f"{name}_dist2drain.tif", np.nan_to_num(dist2drain, nan=NODATA), profile, "float32", NODATA)
    write_raster(TERRAIN_DIR / f"{name}_hand.tif", np.nan_to_num(hand, nan=NODATA), profile, "float32", NODATA)

    elapsed = time.time() - t0
    print(f"  [OK] {name}: hydrology derived in {elapsed:.1f}s")
    print(f"       HAND range (valid cells): "
          f"{np.nanmin(hand[~nodata_mask]):.1f} - {np.nanmax(hand[~nodata_mask]):.1f} m")


def main():
    print("NER Safe — DEM-Based Hydrology Derivation (flow direction/accumulation, streams, HAND)")
    for dist_cfg in DISTRICTS:
        process_district(dist_cfg)
    print(f"\n{'='*65}")
    print("[SUCCESS] Hydrology rasters written to data/terrain/")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()
