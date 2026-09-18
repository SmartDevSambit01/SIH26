# Automation & Processing Scripts (`scripts/`)

## 1. Overview
The `scripts/` directory contains standalone, reproducible Python and shell utilities used for data ingestion, raster clipping, spatial preprocessing, and database setup for **Kohima** and **Aizawl**.

## 2. Core Principles
- **Idempotency**: Scripts should be safe to run multiple times without duplicating data or corrupting state.
- **Deterministic Processing**: Given the same raw rasters and boundary shapes, preprocessing scripts must produce identical outputs.
- **No Over-Engineering**: Simple CLI scripts with standard `argparse` or basic parameters rather than complex orchestration frameworks.

## 3. Planned Scripts

| Script | Responsibility | Dependencies |
| :--- | :--- | :--- |
| `clip_rasters.py` | Clips raw regional DEM/rainfall rasters to Kohima and Aizawl district boundaries | Rasterio, Shapely |
| `derive_morphometry.py` | Computes slope, aspect, and curvature from DEM | GDAL, Rasterio, RichDEM |
| `init_db.py` | Connects to PostgreSQL, enables PostGIS extension, and builds database tables | SQLAlchemy, psycopg2 / asyncpg |
| `seed_boundaries.py` | Imports boundary GeoJSONs into the PostGIS database | GeoPandas, GeoAlchemy2 |
| `fetch_imd_rainfall.py` | Fetches or parses IMD gridded rainfall for Kohima and Aizawl coordinates | Requests, Pandas |

## 4. Usage Example (Preview)
```bash
# Example: Clipping a regional DEM to Kohima boundary
python scripts/clip_rasters.py --input data/terrain/raw/regional_dem.tif --boundary data/boundaries/kohima_district.geojson --output data/terrain/kohima_dem.tif
```
