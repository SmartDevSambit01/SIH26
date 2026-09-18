"""
Configuration settings for the SIH 2026 Landslide Risk FastAPI backend.
Uses pathlib for safe dynamic project-relative paths.
No credentials or secrets are stored here.
"""

from pathlib import Path
from typing import List

# Locate project root dynamically (backend/app/config.py -> backend/app -> backend -> project_root)
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
BOUNDARIES_DIR = DATA_DIR / "boundaries"
ML_DIR = DATA_DIR / "ml"
RAINFALL_DIR = DATA_DIR / "rainfall"
SOIL_MOISTURE_DIR = DATA_DIR / "soil_moisture"
SATELLITE_DIR = DATA_DIR / "satellite"
HISTORICAL_DIR = DATA_DIR / "historical"
FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "public" / "data"

# Specific dataset file paths
KOHIMA_GRID_GEOJSON = BOUNDARIES_DIR / "kohima_grid_500m.geojson"
AIZAWL_GRID_GEOJSON = BOUNDARIES_DIR / "aizawl_grid_500m.geojson"

KOHIMA_BOUNDARY_GEOJSON = BOUNDARIES_DIR / "kohima_district.geojson"
AIZAWL_BOUNDARY_GEOJSON = BOUNDARIES_DIR / "aizawl_district.geojson"

BASELINE_SUSCEPTIBILITY_CSV = ML_DIR / "baseline_susceptibility.csv"
FEATURE_DATASET_CSV = ML_DIR / "feature_dataset.csv"

GPM_OBSERVATIONS_CSV = RAINFALL_DIR / "gpm_latest_observations.csv"
SMAP_OBSERVATIONS_CSV = SOIL_MOISTURE_DIR / "smap_latest_observations.csv"
SENTINEL_SAR_OBSERVATIONS_CSV = SATELLITE_DIR / "sentinel_sar_latest_observations.csv"
HISTORICAL_LANDSLIDES_CSV = HISTORICAL_DIR / "landslide_events_cleaned.csv"
LOCALITIES_DIR = DATA_DIR / "localities"
KOHIMA_LOCALITY_CSV = LOCALITIES_DIR / "kohima_locality_index.csv"
AIZAWL_LOCALITY_CSV = LOCALITIES_DIR / "aizawl_locality_index.csv"
LOCALITY_MAPPING_CSV = LOCALITIES_DIR / "locality_cell_mapping.csv"
VERIFIED_LANDSLIDES_GEOJSON = FRONTEND_DATA_DIR / "verified_landslides.geojson"
SYSTEM_STATUS_JSON = FRONTEND_DATA_DIR / "system_status.json"

# Pilot Districts Metadata
DISTRICTS_META = {
    "Kohima": {
        "name": "Kohima",
        "state": "Nagaland",
        "cell_count": 6055,
        "grid_resolution_m": 500,
        "center": [94.06, 25.67],
        "grid_file": KOHIMA_GRID_GEOJSON,
        "boundary_file": KOHIMA_BOUNDARY_GEOJSON,
    },
    "Aizawl": {
        "name": "Aizawl",
        "state": "Mizoram",
        "cell_count": 10906,
        "grid_resolution_m": 500,
        "center": [92.73, 23.75],
        "grid_file": AIZAWL_GRID_GEOJSON,
        "boundary_file": AIZAWL_BOUNDARY_GEOJSON,
    }
}

# Total cells across pilot districts
TOTAL_CELL_COUNT = 16961

# CORS settings for local development
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://localhost:4173",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]
