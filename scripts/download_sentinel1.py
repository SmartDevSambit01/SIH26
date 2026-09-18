#!/usr/bin/env python3
"""
download_sentinel1.py — Sentinel-1 IW GRD Catalog Search & Download

STEP 7, Phase A — Data Access / Catalog
NER Safe (SIH 2026)

Searches the Alaska Satellite Facility (ASF) DAAC catalog for Sentinel-1
Interferometric Wide (IW) Ground Range Detected High-resolution (GRDH)
scenes covering Kohima and Aizawl districts.

Usage:
    python scripts/download_sentinel1.py --dry-run
    python scripts/download_sentinel1.py --download
    python scripts/download_sentinel1.py --start 2024-06-01 --end 2025-09-01

Authentication:
    Catalog SEARCH does NOT require authentication.
    Scene DOWNLOAD requires a free NASA Earthdata account:
      https://urs.earthdata.nasa.gov/

    Configure credentials via ONE of:
      1. ~/.netrc (or ~/_netrc on Windows):
           machine urs.earthdata.nasa.gov
               login <username>
               password <password>
      2. Environment variables:
           EARTHDATA_USERNAME=<username>
           EARTHDATA_PASSWORD=<password>

Output:
    data/satellite/sentinel1_catalog.json

IMPORTANT:
    - SAR change signals are CORROBORATING ANOMALY EVIDENCE only.
    - They must NEVER be automatically labelled as landslides.
    - No catalog records are fabricated.
    - Catalog entries reflect real ASF DAAC holdings.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required.")
    print("Install via: pip install requests")
    sys.exit(1)

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "satellite"
CATALOG_FILE = DATA_DIR / "sentinel1_catalog.json"
RAW_DIR = DATA_DIR / "raw"

# ── District AOI Bounding Boxes ──────────────────────────────────────
DISTRICTS = {
    "Kohima": {
        "bbox": [93.5, 25.0, 94.5, 26.5],
        "wkt": "POLYGON((93.5 25.0,94.5 25.0,94.5 26.5,93.5 26.5,93.5 25.0))",
        "state": "Nagaland",
    },
    "Aizawl": {
        "bbox": [92.5, 23.0, 93.5, 24.5],
        "wkt": "POLYGON((92.5 23.0,93.5 23.0,93.5 24.5,92.5 24.5,92.5 23.0))",
        "state": "Mizoram",
    },
}

# ── ASF SearchAPI ────────────────────────────────────────────────────
ASF_SEARCH_URL = "https://api.daac.asf.alaska.edu/services/search/param"
ASF_TIMEOUT = 120  # seconds

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("download_sentinel1")


# ═══════════════════════════════════════════════════════════════════════
#  Credential Detection
# ═══════════════════════════════════════════════════════════════════════

def check_earthdata_credentials():
    """
    Check for NASA Earthdata credentials.
    Returns (available: bool, source: str | None).
    """
    # 1. Environment variables
    if os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"):
        return True, "environment variables (EARTHDATA_USERNAME / EARTHDATA_PASSWORD)"

    # 2. ~/.netrc or ~/_netrc (Windows)
    for name in (".netrc", "_netrc"):
        netrc_path = Path.home() / name
        if netrc_path.exists():
            try:
                from netrc import netrc as parse_netrc
                nrc = parse_netrc(str(netrc_path))
                auth = nrc.authenticators("urs.earthdata.nasa.gov")
                if auth and auth[0]:
                    return True, str(netrc_path)
            except Exception as e:
                log.warning(f"Could not parse {netrc_path}: {e}")

    return False, None


# ═══════════════════════════════════════════════════════════════════════
#  ASF Catalog Search (REST API — no extra library needed)
# ═══════════════════════════════════════════════════════════════════════

def search_asf(district_name, wkt, start, end, max_results=250):
    """
    Search ASF DAAC for Sentinel-1 IW GRD scenes intersecting a WKT polygon.

    No authentication is required for search.
    Returns a list of normalized granule dicts, or empty list on failure.
    """
    params = {
        "platform": "Sentinel-1",
        "processingLevel": "GRD_HD",
        "intersectsWith": wkt,
        "start": f"{start}T00:00:00Z",
        "end": f"{end}T23:59:59Z",
        "output": "json",
        "maxResults": max_results,
    }

    log.info(f"Searching ASF for {district_name}: {start} → {end} (max {max_results})")

    try:
        resp = requests.get(ASF_SEARCH_URL, params=params, timeout=ASF_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.ConnectionError:
        log.error(f"Cannot reach ASF API ({ASF_SEARCH_URL}). Check network connectivity.")
        return []
    except requests.exceptions.Timeout:
        log.error(f"ASF API request timed out after {ASF_TIMEOUT}s.")
        return []
    except requests.exceptions.HTTPError as e:
        log.error(f"ASF API HTTP error: {e}")
        return []

    # Parse response
    try:
        data = resp.json()
    except (json.JSONDecodeError, ValueError):
        log.error("ASF API returned non-JSON response.")
        return []

    # ASF JSON format: [[result1, result2, ...]] (nested list)
    results = []
    if isinstance(data, list):
        if len(data) > 0 and isinstance(data[0], list):
            results = data[0]
        elif len(data) > 0 and isinstance(data[0], dict):
            results = data
    elif isinstance(data, dict):
        results = data.get("results", data.get("features", []))

    # Client-side filter: keep only IW beam mode
    # (beamModeType is a response field, not a valid query param)
    results = [
        r for r in results
        if r.get("beamMode", r.get("beamModeType", "IW")).upper() == "IW"
    ]

    log.info(f"  → {len(results)} granules found for {district_name}")

    # Normalize to clean granule dicts
    granules = []
    for r in results:
        try:
            start_time = r.get("startTime", "")
            acq_date = start_time[:10] if len(start_time) >= 10 else ""

            granule = {
                "scene_name": r.get("granuleName", r.get("sceneName", "")),
                "platform": r.get("platform", ""),
                "sensor": r.get("sensor", "C-SAR"),
                "beam_mode": r.get("beamModeType", r.get("beamMode", "IW")),
                "processing_level": r.get("processingLevel", "GRD_HD"),
                "acquisition_date": acq_date,
                "start_time": start_time,
                "stop_time": r.get("stopTime", ""),
                "absolute_orbit": _safe_int(r.get("absoluteOrbit")),
                "relative_orbit": _safe_int(
                    r.get("relativeOrbit", r.get("pathNumber"))
                ),
                "flight_direction": r.get("flightDirection", ""),
                "polarization": r.get("polarization", ""),
                "file_name": r.get("fileName", ""),
                "file_size_mb": _safe_float(r.get("sizeMB")),
                "download_url": r.get("url", r.get("downloadUrl", "")),
                "browse_url": _extract_browse(r),
                "frame_number": _safe_int(r.get("frameNumber")),
                "processing_date": r.get("processingDate", ""),
            }
            granules.append(granule)

        except (ValueError, TypeError, KeyError) as e:
            log.warning(f"Skipping malformed granule record: {e}")
            continue

    # Sort by acquisition date
    granules.sort(key=lambda g: g.get("acquisition_date", ""))
    return granules


def _safe_int(val):
    """Convert to int, defaulting to 0."""
    try:
        return int(val) if val else 0
    except (ValueError, TypeError):
        return 0


def _safe_float(val):
    """Convert to float, defaulting to 0.0."""
    try:
        return round(float(val), 2) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _extract_browse(record):
    """Extract browse/thumbnail URL from a granule record."""
    browse = record.get("browse", record.get("browseUrl", ""))
    if isinstance(browse, list):
        return browse[0] if browse else ""
    return str(browse) if browse else ""


# ═══════════════════════════════════════════════════════════════════════
#  Catalog Assembly
# ═══════════════════════════════════════════════════════════════════════

def build_catalog(start, end, max_results, dry_run):
    """Search all districts and build the unified catalog."""
    creds_available, creds_source = check_earthdata_credentials()

    catalog = {
        "metadata": {
            "project": "NER Safe (SIH 2026)",
            "step": "STEP 7 — Satellite Land-Change / Deformation Data Pipeline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "search_api": "ASF DAAC SearchAPI (NASA Alaska Satellite Facility)",
            "search_url": ASF_SEARCH_URL,
            "search_parameters": {
                "platform": "Sentinel-1",
                "product_type": "IW GRD (GRDH) — Level-1",
                "spatial_resolution_note": (
                    "~10 m pixel spacing (GRDH). When aggregated to the "
                    "500 m analysis grid, this is a zonal statistic, NOT "
                    "500 m measurement resolution."
                ),
                "start_date": start,
                "end_date": end,
                "max_results_per_district": max_results,
            },
            "mode": "DRY-RUN (catalog only)" if dry_run else "SEARCH + DOWNLOAD",
            "credentials_available": creds_available,
            "credentials_source": creds_source,
            "total_granules": 0,
            "total_size_gb": 0.0,
            "scientific_notice": (
                "SAR change signals derived from these scenes are "
                "CORROBORATING ANOMALY EVIDENCE only. They must NEVER "
                "be automatically labelled as landslides. A human/officer "
                "verification layer is required."
            ),
        },
        "districts": {},
    }

    total_granules = 0
    total_size_gb = 0.0

    for name, config in DISTRICTS.items():
        log.info(f"{'━' * 50}")
        log.info(f"District: {name} ({config['state']})")
        log.info(f"{'━' * 50}")

        granules = search_asf(name, config["wkt"], start, end, max_results)

        district_size_gb = sum(g["file_size_mb"] for g in granules) / 1024.0
        dates = [g["acquisition_date"] for g in granules if g["acquisition_date"]]
        orbits = sorted(set(
            g["relative_orbit"] for g in granules if g["relative_orbit"]
        ))
        directions = sorted(set(
            g["flight_direction"] for g in granules if g["flight_direction"]
        ))
        platforms = sorted(set(
            g["platform"] for g in granules if g["platform"]
        ))

        catalog["districts"][name] = {
            "state": config["state"],
            "bbox_wsen": config["bbox"],
            "granule_count": len(granules),
            "date_range": [min(dates), max(dates)] if dates else [],
            "platforms": platforms,
            "relative_orbits": orbits,
            "flight_directions": directions,
            "total_size_gb": round(district_size_gb, 2),
            "granules": granules,
        }

        total_granules += len(granules)
        total_size_gb += district_size_gb

    catalog["metadata"]["total_granules"] = total_granules
    catalog["metadata"]["total_size_gb"] = round(total_size_gb, 2)

    return catalog


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Sentinel-1 IW GRD Catalog Search & Download "
            "(NER Safe STEP 7, Phase A)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True,
        help="Search catalog only, do not download (default: True)",
    )
    parser.add_argument(
        "--download", action="store_true",
        help="Attempt to download scenes (requires NASA Earthdata credentials)",
    )
    parser.add_argument(
        "--start", default="2024-01-01",
        help="Search start date YYYY-MM-DD (default: 2024-01-01)",
    )
    parser.add_argument(
        "--end", default=datetime.now().strftime("%Y-%m-%d"),
        help="Search end date YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--max-results", type=int, default=250,
        help="Max results per district (default: 250)",
    )
    parser.add_argument(
        "--output", type=str, default=str(CATALOG_FILE),
        help=f"Output catalog JSON path (default: {CATALOG_FILE})",
    )

    args = parser.parse_args()
    dry_run = not args.download

    log.info("=" * 70)
    log.info("NER Safe — STEP 7: Sentinel-1 Catalog Search")
    log.info(f"Mode:        {'DRY-RUN (catalog only)' if dry_run else 'SEARCH + DOWNLOAD'}")
    log.info(f"Date range:  {args.start} → {args.end}")
    log.info(f"Max results: {args.max_results} per district")
    log.info("=" * 70)

    # ── Credential Check ─────────────────────────────────────────────
    creds_available, creds_source = check_earthdata_credentials()
    if creds_available:
        log.info(f"✓ NASA Earthdata credentials found: {creds_source}")
    else:
        log.info("✗ No NASA Earthdata credentials detected.")
        log.info("  → Catalog search does NOT require credentials.")
        log.info("  → Download requires a free account at:")
        log.info("    https://urs.earthdata.nasa.gov/")
        if not dry_run:
            log.warning(
                "--download requested but credentials missing. "
                "Falling back to dry-run."
            )
            dry_run = True

    # ── Build Catalog ────────────────────────────────────────────────
    catalog = build_catalog(args.start, args.end, args.max_results, dry_run)

    # ── Save Catalog ─────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    log.info(f"✓ Catalog saved → {output_path}")

    # ── Summary ──────────────────────────────────────────────────────
    log.info("")
    log.info("═══════════════════ CATALOG SUMMARY ═══════════════════")
    log.info(f"Total granules:   {catalog['metadata']['total_granules']}")
    log.info(f"Total volume:     {catalog['metadata']['total_size_gb']:.1f} GB")
    log.info(f"Credentials:      {'Available' if creds_available else 'NOT CONFIGURED'}")
    log.info(f"Download:         {'No (dry-run)' if dry_run else 'Yes'}")
    log.info("")

    for name, district in catalog["districts"].items():
        log.info(f"  {name} ({DISTRICTS[name]['state']}):")
        log.info(f"    Granules:    {district['granule_count']}")
        if district["date_range"]:
            log.info(
                f"    Date range:  {district['date_range'][0]} → "
                f"{district['date_range'][1]}"
            )
        log.info(f"    Platforms:   {district.get('platforms', [])}")
        log.info(f"    Orbits:      {district.get('relative_orbits', [])}")
        log.info(f"    Directions:  {district.get('flight_directions', [])}")
        log.info(f"    Size:        {district['total_size_gb']:.1f} GB")
        log.info("")

    log.info("═" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
