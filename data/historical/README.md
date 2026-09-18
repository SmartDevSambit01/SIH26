# Historical Landslide Inventory (`data/historical/`)

## 1. Purpose
This folder is dedicated to historical landslide event data within **Kohima District (Nagaland)** and **Aizawl District (Mizoram)**. These inventory points/polygons serve as the ground truth for training and validating susceptibility models.

## 2. Expected Data Schema
Files placed here should be vector formats (GeoJSON, ESRI Shapefile, or CSV with coordinates) containing:
- `event_id`: Unique identifier
- `latitude` / `longitude`: Spatial coordinates (WGS 84, EPSG:4326)
- `event_date`: Date or year of occurrence (where known)
- `district`: Kohima or Aizawl
- `landslide_type`: Debris flow, rockfall, rotational slide, translational slide, creep
- `trigger`: Heavy rainfall, slope toe-cutting, road construction, seismic activity
- `confidence`: High, Medium, Low (based on field verification vs. remote sensing)
- `source`: Reporting agency

## 3. Approved Sources
- **Geological Survey of India (GSI)**: National Landslide Susceptibility Mapping (NLSM) and Bhukosh Portal.
- **State Authorities**:
  - Nagaland State Disaster Management Authority (NSDMA).
  - Mizoram State Disaster Management Authority (MSDMA) / Disaster Management & Rehabilitation Department.
- **National Disaster Management Authority (NDMA)** published incident reports.

## 4. Current Status
- No data has been loaded yet. Awaiting verified inventory extraction for Kohima and Aizawl. No synthetic points are allowed.
