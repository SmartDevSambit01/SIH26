# STEP 12.0 — ML MODEL & DATASET INSPECTION REPORT

## Overview
This report establishes the baseline technical state of the SIH 2026 Landslide Early Warning System prior to executing **Task 12: AI/ML Landslide Risk Model + Scientific Validation & Calibration**.

---

## 1. Dataset Schema & Ingestion Status

### A. Feature Dataset (`data/ml/feature_dataset.csv`)
- **Total Rows (Cells)**: 16,961 (6,055 in Kohima, Nagaland; 10,906 in Aizawl, Mizoram)
- **Total Columns**: 54
- **Key Static Features**:
  - `elevation_mean`, `elevation_min`, `elevation_max` (Copernicus 30m DEM) — **AVAILABLE** (82.93% coverage within district boundaries)
  - `slope_mean`, `slope_max` — **AVAILABLE**
  - `aspect_mean` — **AVAILABLE**
  - `curvature_mean` — **AVAILABLE**
  - `twi_mean` (Topographic Wetness Index) — **AVAILABLE**
- **Dynamic Sensor Fields**:
  - `rainfall_rate`, `rainfall_30min`, `rainfall_3h`, `rainfall_6h`, `rainfall_24h`, `rainfall_72h`, `antecedent_rainfall_7d` — **UNAVAILABLE** (0.0% populated; requires NASA Earthdata authentication)
  - `soil_moisture_current`, `soil_moisture_previous`, `soil_moisture_change`, `soil_moisture_change_percent` — **UNAVAILABLE** (0.0% populated; requires NASA Earthdata authentication)
  - `vv_change_db`, `vh_change_db`, `vv_vh_change`, `change_confidence` — **UNAVAILABLE** (0.0% populated; requires ESA Copernicus Open Access Hub / Alaska Satellite Facility authentication)
  - `flood_indicator` — **UNAVAILABLE** (0.0% populated)
  - `citizen_report_count`, `verification_timestamp`, `verification_confidence` — **UNAVAILABLE** (0.0% populated)
  - `officer_verification_status` — **AVAILABLE** (100% default `UNVERIFIED`)

### B. Baseline Susceptibility Dataset (`data/ml/baseline_susceptibility.csv`)
- **Total Rows**: 16,961
- **Columns**: `cell_id`, `district`, `latitude`, `longitude`, `spatial_block_id`, `slope_mean`, `elevation_mean`, `curvature_mean`, `twi_mean`, `terrain_susceptibility_score`, `terrain_susceptibility_class`, `pu_terrain_similarity`, `pu_similarity_class`, `primary_terrain_contributors`, `label_status`, `historical_event_id`
- **TSI Class Distribution**:
  - `VERY_LOW`: 70.36% (11,934 cells)
  - `LOW`: 12.01% (2,037 cells)
  - `MODERATE`: 0.44% (75 cells)
  - `HIGH`: 0.08% (14 cells)
  - `VERY_HIGH`: 0.04% (6 cells)
  - `UNMAPPED_BOUNDARY`: 17.07% (2,895 boundary padding cells)

### C. Historical Landslide Records (`data/historical/landslide_events_cleaned.csv`)
- **Total Events Cleaned**: 19 records (GSI verified GPS coordinates)
- **Grid Cell Associated Events**: 11 records (5 in Kohima, 6 in Aizawl)
- **Unlabeled / Unknown Cells**: 16,950 cells
- **Verified Negative Labels**: 0 cells

---

## 2. ML Label & Readiness Constraints

1. **Severe Label Imbalance**:
   - Only 11 verified positive landslide cells exist across the entire 16,961 cell grid (0.065% positive rate).
   - Zero verified negative cells exist. Non-landslide cells cannot be assumed to be true negatives without field verification (unlabeled cells).

2. **Supervised Binary Classifier Feasibility**:
   - Conventional binary classification (e.g. Random Forest / XGBoost binary classifier with 0/1 labels) is **NOT FEASIBLE** and scientifically invalid on this dataset.
   - Arbitrarily assigning `0` to unlabelled cells would violate scientific integrity, introduce label noise, and produce false accuracy metrics.

3. **Recommended Model Strategy**:
   - **Two-Stage Architecture**:
     - **Stage A (Static Susceptibility)**: Baseline Terrain Susceptibility Index (TSI) + Positive-Unlabeled (PU) similarity distance metric.
     - **Stage B (Dynamic Trigger Evidence)**: Multi-sensor physical trigger rules (GPM rainfall thresholds, SMAP soil moisture saturation, Sentinel-1 SAR backscatter change).
   - Combined into a **Dynamic Hazard Estimation Engine**.

---

## 3. Sensor Authentication & Data Availability Audit

| Sensor / Data Source | Current Ingestion Status | Authentication Required | Action |
| :--- | :--- | :--- | :--- |
| **SRTM / Copernicus DEM 30m** | AVAILABLE (cached locally) | None | Used for static terrain features & TSI baseline |
| **GPM IMERG Rainfall** | UNAVAILABLE | NASA Earthdata | Transparently reported; scenario simulation supported in DEMO mode |
| **SMAP L3 Soil Moisture** | UNAVAILABLE | NASA Earthdata | Transparently reported; scenario simulation supported in DEMO mode |
| **Sentinel-1 SAR Backscatter** | UNAVAILABLE | ESA / ASF | Transparently reported; scenario simulation supported in DEMO mode |
| **Flood Inundation Model** | UNAVAILABLE | External GIS | Transparently reported |

---

## 4. No Data Fabrication Policy Commitment
- Zero fake values will be substituted for missing dynamic fields in live production mode.
- Missing dynamic fields will evaluate to `null` or explicit `UNAVAILABLE` status.
- Demo / Simulation scenarios will be strictly segregated and prominently labeled as `SCENARIO SIMULATION — NOT LIVE OBSERVATION`.
