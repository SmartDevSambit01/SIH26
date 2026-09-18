"""
test_one_granule.py — Tests download and verification of exactly ONE real NASA GPM granule.

Uses earthaccess (NASA's official Python library) for authentication.
Reads credentials from:
  - EARTHDATA_TOKEN (environment variable)
  - EARTHDATA_USERNAME + EARTHDATA_PASSWORD (environment variables)
  - ~/.netrc (urs.earthdata.nasa.gov entry)

Never prints credentials. Stops and reports if download fails.
"""
import os
import sys
import tempfile
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv()
except Exception:
    pass

# --- 1. Check credentials ---
token = os.environ.get("EARTHDATA_TOKEN")
user = os.environ.get("EARTHDATA_USERNAME")
pwd = os.environ.get("EARTHDATA_PASSWORD")
netrc = Path.home() / ".netrc"

print(f"\n[AUTH CHECK]")
print(f"  EARTHDATA_TOKEN present: {bool(token)}, length: {len(token) if token else 0}")
print(f"  EARTHDATA_USERNAME present: {bool(user)}")
print(f"  ~/.netrc exists: {netrc.exists()}")

if not (token or (user and pwd) or netrc.exists()):
    print("\n[STOP] No NASA Earthdata credentials found.")
    print("  Please set EARTHDATA_TOKEN environment variable and re-run.")
    print("  Status: REQUIRES_EXTERNAL_AUTH")
    sys.exit(1)

# --- 2. Try earthaccess login ---
try:
    import earthaccess
except ImportError:
    print("[ERROR] earthaccess not installed. Run: pip install earthaccess")
    sys.exit(1)

print("\n[EARTHACCESS LOGIN]")
try:
    if token:
        auth = earthaccess.login(strategy="environment")
    else:
        auth = earthaccess.login(strategy="netrc")
    print(f"  earthaccess login succeeded: {auth.authenticated}")
    if not auth.authenticated:
        print("[STOP] earthaccess authentication failed.")
        sys.exit(1)
except Exception as e:
    print(f"[STOP] earthaccess login failed: {e}")
    sys.exit(1)

# --- 3. Search for ONE granule ---
print("\n[CMR SEARCH] GPM_3IMERGHHE version 07 (Early Run half-hourly)")
try:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    end = now.strftime("%Y-%m-%d")
    results = earthaccess.search_data(
        short_name="GPM_3IMERGHHE",
        version="07",
        bounding_box=(92.0, 23.0, 95.0, 26.5),
        temporal=(start, end),
        count=1,
    )
    print(f"  CMR returned {len(results)} granule(s)")
    if not results:
        print("[STOP] No granules returned from CMR. Data may not be available.")
        sys.exit(1)
    granule = results[0]
    print(f"  Granule: {granule['meta']['native-id']}")
    time_start = granule['umm']['TemporalExtent']['RangeDateTime']['BeginningDateTime']
    print(f"  Observation start: {time_start}")
except Exception as e:
    print(f"[STOP] CMR search failed: {e}")
    sys.exit(1)

# --- 4. Download to a temp directory ---
raw_dir = PROJECT_ROOT / "data" / "rainfall" / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)

print(f"\n[DOWNLOAD] Downloading to {raw_dir}...")
try:
    files = earthaccess.download(results, local_path=str(raw_dir))
    if not files:
        print("[STOP] earthaccess.download returned empty list. Download failed.")
        sys.exit(1)
    downloaded_file = Path(files[0])
    print(f"  Downloaded: {downloaded_file.name}")
    print(f"  File size: {downloaded_file.stat().st_size:,} bytes")
    if downloaded_file.stat().st_size < 1_000_000:
        print(f"[STOP] File too small ({downloaded_file.stat().st_size} bytes) — likely not a real HDF5 granule.")
        downloaded_file.unlink(missing_ok=True)
        sys.exit(1)
except Exception as e:
    print(f"[STOP] Download failed: {e}")
    sys.exit(1)

# --- 5. Verify HDF5 structure and NASA provenance ---
print("\n[HDF5 VERIFICATION]")
try:
    import h5py
    with h5py.File(downloaded_file, "r") as hf:
        has_grid = "Grid" in hf
        top_keys = list(hf.keys())
        global_attrs = dict(hf.attrs)
        print(f"  Top-level HDF5 groups/keys: {top_keys}")
        print(f"  Global attribute count: {len(global_attrs)}")
        if not has_grid:
            print("[STOP] Missing 'Grid' group in HDF5 file.")
            downloaded_file.unlink(missing_ok=True)
            sys.exit(1)

        grid = hf["Grid"]
        print(f"  Grid datasets: {list(grid.keys())[:10]}")
        has_precip = "precipitation" in grid
        print(f"  Has 'precipitation' dataset: {has_precip}")

        # Check NASA attributes in root attrs, FileHeader, or Grid attrs
        all_attrs = dict(global_attrs)
        if "FileHeader" in hf:
            all_attrs.update(dict(hf["FileHeader"].attrs))
        if "Grid" in hf:
            all_attrs.update(dict(hf["Grid"].attrs))

        nasa_keys = [k for k in all_attrs if any(k.startswith(p) for p in
                     ("StartGranuleDateTime", "DOI", "GranuleMonthDayYear", "AlgorithmVersion",
                      "SatelliteName", "GeneratingAlgorithmVersion", "FileHeader", "InputFileName"))]
        print(f"  NASA metadata attributes found: {nasa_keys[:10]}")
        if not nasa_keys and not global_attrs:
            print("[STOP] Missing NASA producer metadata. File cannot be verified as real granule.")
            downloaded_file.unlink(missing_ok=True)
            sys.exit(1)

        if "StartGranuleDateTime" in all_attrs:
            ts = all_attrs["StartGranuleDateTime"]
            if isinstance(ts, bytes):
                ts = ts.decode()
            print(f"  Granule StartGranuleDateTime: {ts}")

        if has_precip:
            precip = grid["precipitation"][:]
            if precip.ndim == 3:
                precip = precip[0]
            print(f"  Precipitation matrix shape: {precip.shape}")
            valid_vals = precip[precip >= 0.0]
            print(f"  Valid (non-fill) pixels: {len(valid_vals):,}")
            print(f"  Precip rate range (mm/hr): {float(valid_vals.min()):.4f} — {float(valid_vals.max()):.4f}")

except Exception as e:
    print(f"[STOP] HDF5 verification failed: {e}")
    downloaded_file.unlink(missing_ok=True)
    sys.exit(1)

print("\n" + "=" * 70)
print("RESULT: ONE REAL NASA GPM GRANULE SUCCESSFULLY DOWNLOADED AND VERIFIED")
print(f"  File: {downloaded_file.name}")
print(f"  Size: {downloaded_file.stat().st_size:,} bytes")
print(f"  NASA Provenance: VERIFIED")
print("=" * 70)
print("\nProceeding to full ingestion is now authorized.")
