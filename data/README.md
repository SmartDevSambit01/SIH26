# Data Directory (`data/`)

## 1. Overview
The `data/` directory contains all spatial, environmental, meterological, and historical inventory data required for **NER Safe**.

All data stored here is strictly bounded to the two pilot districts:
1. **Kohima District**, Nagaland
2. **Aizawl District**, Mizoram

## 2. Strict Data Governance Policy
- **Zero Fabrication**: Under no circumstances should fake coordinates, synthetic landslide occurrences, mock sensor feeds, or fictitious rainfall numbers be placed in this folder.
- **Source Transparency**: Every dataset placed in this folder must have documented provenance (source agency, acquisition date, spatial resolution, coordinate reference system).
- **Immutability of Raw Data**: Raw downloaded files must remain unmodified. Preprocessed, reprojected, or clipped files should be saved under designated processed folders.
- **Handling Missing Data**: If data for a specific factor (e.g., real-time soil moisture sensors) is unavailable for a district, that factor is marked as `UNAVAILABLE` in pipeline configs.

## 3. Subdirectories

| Subdirectory | Description | Expected Sources |
| :--- | :--- | :--- |
| `historical/` | Past landslide event locations and dates | Geological Survey of India (Bhukosh), NSDMA, MSDMA |
| `rainfall/` | Daily/hourly precipitation records | India Meteorological Department (IMD), AWS, NASA GPM |
| `soil_moisture/`| Soil saturation & moisture levels | NASA SMAP, ESA CCI, local in-situ stations |
| `terrain/` | DEM, slope, aspect, curvature rasters | CartoDEM (ISRO Bhuvan), SRTM 30m, Copernicus DEM |
| `satellite/` | Optical (NDVI, LULC) & SAR products | Sentinel-2, Landsat-8/9, Sentinel-1 |
| `boundaries/` | District and administrative polygons | Survey of India, Census of India (GeoJSON / Shapefiles) |

## 4. Coordinate Reference System (CRS)
All spatial layers must be standardized to:
- **Geographic CRS**: EPSG:4326 (WGS 84) for GeoJSON / API outputs.
- **Projected CRS**: UTM Zone 46N (EPSG:32646) for distance, slope, and metric calculations in Nagaland and Mizoram.
