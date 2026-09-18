# STEP 12 — AI/ML LANDSLIDE RISK MODEL + SCIENTIFIC VALIDATION & CALIBRATION

## Executive Summary
Task 12 establishes a scientifically defensible, two-stage AI/ML landslide hazard and risk model pipeline for the pilot districts of **Kohima (Nagaland)** and **Aizawl (Mizoram)** across 16,961 analysis cells (500m × 500m).

---

## 1. Why Conventional Supervised ML Is Limited
- **Ground Truth Sample Size**: 11 verified positive historical landslide cells (5 in Kohima, 6 in Aizawl).
- **Verified Negative Labels**: 0 cells.
- **Unlabeled Cells**: 16,950 cells.
- **Scientific Integrity Constraint**: Non-landslide cells cannot be randomly labeled `0`. Training a conventional binary classifier on unlabelled data creates false negative bias and unscientific accuracy claims.

---

## 2. Model Strategy & Architecture
The system implements a **Two-Stage Architecture**:
1. **Stage A — Static Terrain Susceptibility**:
   - Terrain Susceptibility Index (TSI) derived from Copernicus/SRTM 30m DEM (slope, elevation, curvature, TWI, aspect).
   - Positive-Unlabeled (PU) terrain similarity distance metric.
2. **Stage B — Dynamic Trigger Evidence**:
   - Evaluates multi-sensor physical triggers (GPM rainfall rate & accumulations, SMAP soil moisture saturation, Sentinel-1 SAR backscatter change, flood inundation, officer field verification).
3. **Automated Readiness Gating**:
   - Overall Readiness Status: `LIMITED_DATA`
   - Calibration Status: `NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS`

---

## 3. Scientific Parameter Evidence Base
Peer-reviewed thresholds from **GSI**, **IMD**, **ISRO**, **NASA**, and **ESA** are compiled in [data/research/landslide_parameter_evidence.csv](file:///c:/Users/sambi/Downloads/SIH%2026/data/research/landslide_parameter_evidence.csv):
- **Kohima Slope Prone Range**: 25° – 45° (Disang Shales).
- **Aizawl Slope Prone Range**: 30° – 50° (Bhuban Sandstone/Siltstone).
- **Hourly Rainfall Trigger**: 15 – 25 mm/h (Kohima), 20 – 30 mm/h (Aizawl).
- **24h Rainfall Trigger**: 80 – 120 mm (Kohima), 100 – 135 mm (Aizawl).
- **Soil Moisture Saturation**: 0.38 – 0.48 m³/m³ (NASA Landslide Program).

---

## 4. Probability Calibration Gate
- **Minimum Required Verified Positives**: 100 cells.
- **Current Verified Positives**: 11 cells.
- **Operational Policy**: Uncalibrated percentages (e.g. "87% chance") are **NEVER** displayed. Hazard probability is reported as `null` with probability status `UNAVAILABLE_NOT_CALIBRATED`.

---

## 5. API Endpoints
- `GET /api/model/status`: Returns model readiness status and calibration gate.
- `GET /api/model/features`: Returns feature registry.
- `GET /api/model/validation`: Returns spatial block cross-validation metrics.
- `GET /api/model/predictions/{cell_id}`: Returns cell prediction object.
- `GET /api/model/explanation/{cell_id}`: Returns top contributing factors & parameter evidence range comparison.
