# STEP 11 — AREA / LOCALITY-BASED RISK SEARCH & INTELLIGENCE

## Overview
Task 11 expands the SIH 2026 Landslide Early Warning and Monitoring System from isolated 500m analysis cells to recognizable administrative and geographical **Areas / Localities** in Kohima (Nagaland) and Aizawl (Mizoram).

Rather than restricting the user interface to village-level names only, Task 11 allows users to search for recognizable places (e.g. **Durtlang**, **Khonoma**, **Merima**, **Kohima**, **Aizawl**) or district names, map them to member 500m cells, and view aggregated Baseline Susceptibility (TSI) information in a dedicated **Area Risk Dashboard**.

---

## Data Source & Provenance
- **Data Source**: OpenStreetMap (OSM) Overpass API (`https://overpass-api.de/api/interpreter`)
- **Query Methodology**: Spatial bounding box queries filtering OSM features containing `place` tags (nodes, ways, and relations).
- **Source Date**: 2026-09-17
- **Recognized Locality Place Types**:
  - `city`
  - `town`
  - `suburb`
  - `neighbourhood`
  - `village`
  - `hamlet`
  - `locality`
  - `isolated_dwelling`
  - `quarter`

### Locality Index Datasets
- `data/localities/kohima_locality_index.csv` (86 verified localities)
- `data/localities/aizawl_locality_index.csv` (45 verified localities)

---

## Locality-to-Cell Association Methodology
1. **Association Type**: Point-based centroid-to-locality nearest neighbor association.
2. **Maximum Association Radius**: `2500.0` meters (2.5 km).
   - This radius accounts for local neighborhood influence zones in steep mountainous terrain.
   - Cells located further than 2.5 km from any recognized OSM place feature are **not automatically assigned**.
3. **Association Provenance File**: `data/localities/locality_cell_mapping.csv`
4. **Statistics**:
   - **Kohima**: 3,139 / 6,055 cells associated (2,916 unassociated).
   - **Aizawl**: 2,273 / 10,906 cells associated (8,633 unassociated).
   - **Total Associated Cells**: 5,412 cells.
   - **Total Unassociated Cells**: 11,549 cells.

---

## Fallback Naming Rule (Phase 8)
For 500m cells without a reliably associated locality within the 2500m radius:
- **Rule**: DO NOT fabricate or invent names.
- **Format**: `District + Cell ID + coordinates`
- **Example**: `Kohima Cell KOH_00001 (25.6506, 93.8954)`

---

## Area Risk Aggregation Methodology
For each recognized locality/area, the backend aggregates underlying 500m grid cells to compute:
1. **Total Associated Cells Count**: Total cells within association radius.
2. **Highest-Risk Cell ID**: Cell ID exhibiting the maximum Baseline Susceptibility score.
3. **Maximum TSI Score**: Maximum static Terrain Susceptibility Index score across member cells.
4. **Dominant TSI Class**: Most frequent TSI class (e.g. `VERY_HIGH`, `HIGH`, `MODERATE`, `LOW`, `VERY_LOW`).
5. **Class Distribution Percentage**: Percentage distribution of TSI classes across member cells (sums to 100%).
6. **Historical Landslide Evidence**: Presence of GSI verified historical landslide records and associated event IDs (e.g., `LS_AIZ_2023_001`).

### Important Distinction: Baseline Susceptibility vs. Live Prediction
- **Baseline Susceptibility (TSI)** represents static terrain vulnerability derived from 30m Copernicus/SRTM DEM morphometry (slope, curvature, TWI, elevation).
- **TSI is NOT a probability** and is **NOT a live prediction**.
- All dashboards and API responses explicitly label TSI as `"Baseline susceptibility is not a live landslide prediction."`

---

## Backend Services & API Endpoints
- **Service**: `backend/app/services/area_service.py`
- **Schemas**: `backend/app/schemas/area.py`
- **Routes**: `backend/app/routes/areas.py`

### Implemented Endpoints:
- `GET /api/areas?district=Kohima&search=Durtlang&limit=100`: List & search localities.
- `GET /api/areas/{area_id}`: Retrieve area metadata and associated cell IDs.
- `GET /api/areas/{area_id}/risk`: Retrieve aggregated Baseline Susceptibility and dynamic data status.
- `GET /api/areas/{area_id}/cells`: Retrieve member 500m cells with terrain attributes.
- `GET /api/areas/cell/{cell_id}/locality`: Retrieve cell locality mapping or fallback name.

---

## Dynamic Data Availability Status
Because live GPM, SMAP, and Sentinel-1 sensors require external NASA/ESA Earthdata authentication:
- **GPM Rainfall**: `Unavailable — NASA Earthdata authentication required`
- **SMAP Soil Moisture**: `Unavailable — NASA Earthdata authentication required`
- **Sentinel-1 SAR**: `Unavailable — external authentication/download pending`
- **Flood Hydrodynamics**: `Unavailable`

Zero fabricated data is presented.

---

## Frontend Area Search & Dashboard
- **Components Created**:
  - `frontend/src/components/RiskMap/AreaSearchPanel.jsx`: Interactive search modal.
  - `frontend/src/components/RiskMap/AreaRiskDashboard.jsx`: Slide-over dashboard displaying area risk, TSI distribution, historical evidence, cell list, and transparent dynamic sensor status.
- **Map Behavior**:
  - Selecting an area highlights all member 500m cells on the map with a glowing cyan boundary (`#38BDF8`).
  - Map smooth-fits bounds to the area's associated cells.
  - Users can click individual member cells to view 500m terrain details or click `X` to return to district view.

---

## Key Differences Summary
| Concept | Analysis Cell (500m x 500m) | Area / Locality |
| :--- | :--- | :--- |
| **Spatial Unit** | Fixed 500m grid cell (6,055 in Kohima, 10,906 in Aizawl) | Recognized settlement feature from OpenStreetMap |
| **Identification** | System Cell ID (e.g., `KOH_01378`, `AIZ_02318`) | Name & Place Type (e.g. `Durtlang (village)`, `Khonoma`) |
| **Risk Value** | Cell-specific TSI score | Aggregated Max TSI, Dominant Class, & % Distribution |
