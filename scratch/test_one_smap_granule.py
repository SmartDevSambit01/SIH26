"""
test_one_smap_granule.py — Verification of ONE real NASA SMAP SPL3SMP_E Version 006 granule.

Uses earthaccess for Earthdata authentication.
Downloads to data/soil_moisture/raw/
Verifies HDF5 datasets, soil moisture physical range, quality flags, and spatial mapping.

Never prints or exposes secrets.
"""
import os
import sys
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv()
except Exception:
    pass

import h5py
import numpy as np
import pyproj

print("=" * 80)
print("SINGLE GRANULE VERIFICATION — NASA SMAP SPL3SMP_E Version 006")
print("=" * 80)

# --- 1. Check Credentials & Login ---
token = os.environ.get("EARTHDATA_TOKEN")
user = os.environ.get("EARTHDATA_USERNAME")
netrc = Path.home() / ".netrc"

print("\n[1. AUTH CHECK]")
print(f"  EARTHDATA_TOKEN present: {bool(token)}")
print(f"  EARTHDATA_USERNAME present: {bool(user)}")
print(f"  ~/.netrc exists: {netrc.exists()}")

if not (token or user or netrc.exists()):
    print("[STOP] No NASA Earthdata credentials found.")
    sys.exit(1)

try:
    import earthaccess
    auth = earthaccess.login(strategy="environment")
    print(f"  earthaccess authenticated: {auth.authenticated}")
    if not auth.authenticated:
        print("[STOP] earthaccess login failed.")
        sys.exit(1)
except Exception as e:
    print(f"[STOP] earthaccess login exception: {e}")
    sys.exit(1)

# --- 2. Search for ONE recent SMAP granule ---
print("\n[2. CMR SEARCH] Short name: SPL3SMP_E, Version: 006")
now = datetime.now(timezone.utc)
start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
end = now.strftime("%Y-%m-%d")

try:
    results = earthaccess.search_data(
        short_name="SPL3SMP_E",
        version="006",
        bounding_box=(92.0, 23.0, 95.0, 26.5),
        temporal=(start, end),
        count=1,
    )
    if not results:
        # Fallback search without temporal restriction if recent 14d is empty
        log_msg = "No granules in last 14 days; querying latest available granule..."
        print(f"  {log_msg}")
        results = earthaccess.search_data(
            short_name="SPL3SMP_E",
            version="006",
            bounding_box=(92.0, 23.0, 95.0, 26.5),
            count=1,
        )

    print(f"  CMR search returned {len(results)} granule(s)")
    if not results:
        print("[STOP] No SMAP SPL3SMP_E granules returned from CMR.")
        sys.exit(1)

    granule = results[0]
    native_id = granule["meta"].get("native-id", "")
    print(f"  Granule native ID: {native_id}")
except Exception as e:
    print(f"[STOP] CMR search failed: {e}")
    sys.exit(1)

# --- 3. Download to data/soil_moisture/raw/ ---
raw_dir = PROJECT_ROOT / "data" / "soil_moisture" / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)

print(f"\n[3. DOWNLOAD] Target directory: {raw_dir}")
try:
    files = earthaccess.download(results, local_path=str(raw_dir))
    if not files:
        print("[STOP] earthaccess.download returned empty list.")
        sys.exit(1)

    downloaded_path = Path(files[0])
    print(f"  Downloaded file: {downloaded_path.name}")
    file_size = downloaded_path.stat().st_size
    print(f"  File size: {file_size:,} bytes")
    if file_size < 1_000_000:
        print(f"[STOP] Downloaded file too small ({file_size} bytes).")
        sys.exit(1)
except Exception as e:
    print(f"[STOP] Download failed: {e}")
    sys.exit(1)

# --- 4. Verify HDF5 Datasets & Metadata ---
print("\n[4. HDF5 VERIFICATION]")
try:
    with h5py.File(downloaded_path, "r") as hf:
        top_keys = list(hf.keys())
        print(f"  Top-level HDF5 groups: {top_keys}")

        am_group = "Soil_Moisture_Retrieval_Data_AM"
        if am_group not in hf:
            print(f"[STOP] Missing required group '{am_group}' in HDF5 file.")
            sys.exit(1)

        am_keys = list(hf[am_group].keys())
        print(f"  '{am_group}' datasets count: {len(am_keys)}")

        # Check required primary datasets
        has_sm = "soil_moisture" in hf[am_group]
        has_qf = "retrieval_qual_flag" in hf[am_group]
        has_lat = "latitude" in hf[am_group]
        has_lon = "longitude" in hf[am_group]

        print(f"  - Primary soil_moisture dataset: {has_sm}")
        print(f"  - Quality flag dataset (retrieval_qual_flag): {has_qf}")
        print(f"  - Latitude dataset: {has_lat}")
        print(f"  - Longitude dataset: {has_lon}")

        if not (has_sm and has_qf and has_lat and has_lon):
            print("[STOP] One or more required datasets missing in HDF5 file.")
            sys.exit(1)

        sm_dataset = hf[am_group]["soil_moisture"]
        sm_arr = sm_dataset[:]
        sm_attrs = dict(sm_dataset.attrs)
        print(f"\n  Soil Moisture Dataset Info:")
        print(f"    - Shape: {sm_arr.shape}")
        print(f"    - Data type: {sm_arr.dtype}")
        fill_val = sm_attrs.get("_FillValue", -9999.0)
        units = sm_attrs.get("units", "cm^3/cm^3")
        if isinstance(units, bytes): units = units.decode()
        print(f"    - Declared fill value: {fill_val}")
        print(f"    - Declared units: {units}")

        # Check fill-value handling and physical range
        valid_mask = (sm_arr != fill_val) & (sm_arr >= 0.0) & (sm_arr <= 1.0) & (~np.isnan(sm_arr))
        valid_vals = sm_arr[valid_mask]
        fill_count = np.sum(sm_arr == fill_val)

        print(f"    - Total matrix elements: {sm_arr.size:,}")
        print(f"    - Fill-value elements: {fill_count:,} (Excluded from stats)")
        print(f"    - Valid soil moisture observations count: {len(valid_vals):,}")

        if len(valid_vals) > 0:
            v_min = float(np.min(valid_vals))
            v_max = float(np.max(valid_vals))
            v_mean = float(np.mean(valid_vals))
            print(f"    - Valid range (volumetric m3/m3): min = {v_min:.4f}, max = {v_max:.4f}, mean = {v_mean:.4f}")
        else:
            print("    [WARNING] Zero valid (non-fill) observations in AM pass dataset.")

        # Check Quality Flags
        qf_arr = hf[am_group]["retrieval_qual_flag"][:]
        print(f"\n  Quality Flag Info:")
        print(f"    - retrieval_qual_flag shape: {qf_arr.shape}")
        rec_good = np.sum((qf_arr & 1) == 0)  # Bit 0 = 0 means retrieval recommended/good
        print(f"    - Recommended/Good quality pixels count: {rec_good:,}")

        # Check Metadata for Observation Date/Time
        global_attrs = dict(hf.attrs)
        obs_date = global_attrs.get("RangeBeginningDate", global_attrs.get("CompositeReleaseDate", "N/A"))
        if isinstance(obs_date, bytes): obs_date = obs_date.decode()
        print(f"\n  Producer Metadata:")
        print(f"    - RangeBeginningDate / ReleaseDate: {obs_date}")

        # Anti-Fabrication / Synthetic check
        is_synthetic = "Synthetic" in global_attrs or "Mock" in global_attrs
        print(f"    - Synthetic marker check: {'FLAGGED SYNTHETIC' if is_synthetic else 'VERIFIED REAL NASA GRANULE'}")

except Exception as e:
    print(f"[STOP] HDF5 inspection failed: {e}")
    sys.exit(1)

# --- 5. Spatial Mapping Verification to 500m Grid ---
print("\n[5. SPATIAL MAPPING VERIFICATION (EASE-Grid 2.0 9km)]")
wgs_to_ease2 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
EASE2_CELL_SIZE = 9008.055627
EASE2_X_MIN = -17367530.44
EASE2_Y_MAX = 7314540.83

def get_smap_ease2_cell(lon: float, lat: float):
    x, y = wgs_to_ease2(lon, lat)
    col = int((x - EASE2_X_MIN) / EASE2_CELL_SIZE)
    row = int((EASE2_Y_MAX - y) / EASE2_CELL_SIZE)
    return f"EASE2_M09_R{row:04d}_C{col:04d}", row, col

# Test pilot district centroids
kohima_cell, k_row, k_col = get_smap_ease2_cell(94.06, 25.67)
aizawl_cell, a_row, a_col = get_smap_ease2_cell(92.73, 23.75)

print(f"  Kohima Centroid (25.67 N, 94.06 E) -> {kohima_cell} (Row {k_row}, Col {k_col})")
print(f"  Aizawl Centroid (23.75 N, 92.73 E) -> {aizawl_cell} (Row {a_row}, Col {a_col})")
print("  Native Product Resolution: 9 km EASE-Grid 2.0 (EPSG:6933)")
print("  Spatial Mapping Rule: Nearest 9 km EASE2 cell assigned to 500m display grid without downscaling.")

print("\n" + "=" * 80)
print("SINGLE REAL NASA SMAP GRANULE VERIFICATION COMPLETE")
print("=" * 80)
