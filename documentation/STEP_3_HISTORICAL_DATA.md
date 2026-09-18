# Step 3: Historical Landslide Dataset Report

> **Project:** NER Safe (SIH 2026)  
> **Pilot Focus:** Kohima District (Nagaland) & Aizawl District (Mizoram)  
> **Temporal Range:** 2020 – 2026  
> **Status:** Compiled, Validated & Quality-Assessed

---

## 1. Executive Summary

This report documents the compilation, cleaning, spatial matching, and quality evaluation of the historical landslide event dataset for the **NER Safe** prototype.

Adhering to our core principle of **truthful data engineering**, no coordinates, dates, or incident occurrences were fabricated. Every event in this dataset represents an officially documented slope instability incident sourced from public disaster management authorities, post-disaster field assessments, or official press bulletins.

---

## 2. Dataset Overview & Key Metrics

| Metric | Total Dataset | Kohima District (Nagaland) | Aizawl District (Mizoram) |
| :--- | :--- | :--- | :--- |
| **Total Curated Records** | **19** | **9** | **10** |
| **Verified Coordinates (`VERIFIED`)** | **11** (57.9%) | **5** (55.6%) | **6** (60.0%) |
| **Needs Verification (`NEEDS_VERIFICATION`)** | **4** (21.1%) | **2** (22.2%) | **2** (20.0%) |
| **Missing Coordinates (`MISSING`)** | **4** (21.1%) | **2** (22.2%) | **2** (20.0%) |
| **Date Range** | **2020-07-11 to 2024-08-18** | 2020-08-15 to 2024-08-18 | 2020-07-11 to 2024-05-29 |
| **Exact Duplicate Records** | **0** | 0 | 0 |
| **Out-of-District Coordinates** | **0** | 0 | 0 |

---

## 3. Data Sources & Provenance

All records were gathered from published government disaster bulletins, field inspection briefs, and authoritative incident releases:

1. **Kohima District (Nagaland)**:
   - **NSDMA (Nagaland State Disaster Management Authority)**: Monsoonal incident reports, travel advisories, and disaster situation bulletins.
   - **District Disaster Management Authority (DDMA) Kohima**: Road blockage notifications and urban landslide logs.
   - **Geological Survey of India (GSI) / Nagaland Department of Geology & Mining (DGM)**: Post-disaster inspection reports (e.g., Tarliedzü sector, Phesama recurrent slide corridor).
   - **Press Information Bureau (PIB)**: National highway emergency restoration updates for NH-29 (Dzüdza bridge collapse, August 2024).

2. **Aizawl District (Mizoram)**:
   - **MSDMA (Mizoram State Disaster Management Authority)**: Monsoon disaster bulletins and Cyclone Remal incident logs (May 2024).
   - **National Disaster Response Force (NDRF) / PIB**: Search and rescue situation reports for the Melthum stone quarry catastrophe (May 28, 2024).
   - **Aizawl Municipal Corporation (AMC)**: Urban slope failure records (Ramhlun Vengthlang, Bawngkawn, Salem Veng).
   - **Public Works Department (PWD) Mizoram**: Highway infrastructure damage reports on Durtlang ridge and northern approach corridors (Sihphir).

---

## 4. Coordinate Status Definitions

To guarantee data integrity and prevent false spatial associations:
- **`VERIFIED`**: Exact GPS point location verified from surveyed field reports, mapped disaster sites, or geo-referenced infrastructure markers. Verified to lie strictly inside the district boundary.
- **`NEEDS_VERIFICATION`**: Known village, road junction, or neighborhood name where an approximate locality center is known, but exact slide scar/crown coordinates require field GPS ground-truthing.
- **`MISSING`**: Incident officially recorded in district disaster logs, but no spatial coordinates were provided. Latitude and longitude are kept strictly empty (`""`) to prevent hallucinated coordinates.

---

## 5. Spatial Grid Matching (500m Cells)

Spatial matching was performed using the official 500-meter analysis grids (`kohima_grid_500m.geojson` and `aizawl_grid_500m.geojson`) generated in Step 2:

- **Matching Rule:** Spatial matching is executed **strictly for `VERIFIED` coordinates**. Unverified and missing records are assigned empty values for `cell_id` and `matched_district`.
- **Matched Kohima Cells**:
  - `LS_KOH_2024_001` (Dzudza Bridge, NH-29) $\rightarrow$ Grid Cell **`KOH_01378`**
  - `LS_KOH_2024_002` (Kisama Heritage Village Road) $\rightarrow$ Grid Cell **`KOH_03175`**
  - `LS_KOH_2023_001` (Phesama Sector, NH-29) $\rightarrow$ Grid Cell **`KOH_03071`**
  - `LS_KOH_2022_001` (Sechu Zubza Slope) $\rightarrow$ Grid Cell **`KOH_01187`**
  - `LS_KOH_2021_001` (Tarliedzu Area) $\rightarrow$ Grid Cell **`KOH_02654`**
- **Matched Aizawl Cells**:
  - `LS_AIZ_2024_001` (Melthum Quarry) $\rightarrow$ Grid Cell **`AIZ_01960`**
  - `LS_AIZ_2024_002` (Hlimen Veng Ridge) $\rightarrow$ Grid Cell **`AIZ_02185`**
  - `LS_AIZ_2023_001` (Durtlang Hills Highway) $\rightarrow$ Grid Cell **`AIZ_02321`**
  - `LS_AIZ_2022_001` (Sihphir Approach Road) $\rightarrow$ Grid Cell **`AIZ_02559`**
  - `LS_AIZ_2021_001` (Ramhlun Vengthlang) $\rightarrow$ Grid Cell **`AIZ_02314`**
  - `LS_AIZ_2020_001` (Bawngkawn Chhimveng) $\rightarrow$ Grid Cell **`AIZ_02431`**

---

## 6. Machine Learning Readiness Assessment

> [!WARNING]
> **Current Status: NOT READY FOR MACHINE LEARNING TRAINING**

### Detailed Evaluation
1. **Sample Size Insufficiency**:
   - The verified dataset currently contains **5 verified points in Kohima** and **6 verified points in Aizawl**.
   - Training a supervised machine learning model (e.g., XGBoost, Random Forest) on 11 positive instances against ~17,000 background grid cells would suffer from severe class imbalance ($>1500:1$), extreme statistical overfitting, and zero generalization power.
   - Reliable spatial cross-validation (Spatial K-Fold or spatial block blocking) requires **at least 50 to 100+ verified landslide polygons or points per district**.
2. **Missing Absence / Non-Landslide Sampling**:
   - Supervised classification also requires an authoritative non-landslide sampling strategy (e.g., slope $<5^\circ$, ridge tops, stable forested terrain) which must be derived from verified digital elevation models.
3. **Action Required to Proceed to ML**:
   - Before executing ML training scripts, the project must incorporate an official GIS inventory export from the **Geological Survey of India (GSI) Bhukosh portal** or the **National Landslide Susceptibility Mapping (NLSM)** program.
   - In accordance with project rules, **we will not fabricate synthetic landslide events** to artificially meet sample size thresholds.

---

## 7. Limitations & Data Gaps

1. **Reporting Bias**:
   - Publicly documented events predominantly represent landslides impacting major highways (e.g., NH-29, NH-54) and urban settlements (e.g., Aizawl town, Kohima town). Rural slope failures that do not disrupt transport corridors or cause human casualties often go unrecorded in public bulletins.
2. **Temporal Precision**:
   - Event times are recorded where available, but several entries only specify the calendar date without exact hourly timestamps.
3. **Single Point vs. Polygon Geometry**:
   - Landslides are spatial polygons (source area, transport track, deposition zone). In this initial catalog, single point centroids were recorded. Future integration of GSI NLSM shapefiles should provide polygon extents.
