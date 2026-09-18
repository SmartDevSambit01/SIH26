# STEP 8.5 — Machine Learning Readiness & Ground-Truth Audit

## 1. Executive Summary

This document presents a rigorous, scientific audit of the **NER Safe** data foundation prior to **Step 9: Machine Learning Modeling**. 

Adhering to our strict **Anti-Fabrication & Scientific Truthfulness Protocol**, the system explicitly diagnoses data readiness rather than forcing an artificial training run. Machine learning models trained on fabricated labels, uncalibrated negative assumptions, or synthetic environmental proxies yield dangerous, ungrounded disaster-warning outputs.

> [!WARNING]
> **Definitive ML Readiness Classification: NOT READY FOR CONVENTIONAL SUPERVISED BINARY CLASSIFICATION**
> 
> The current dataset ([`data/ml/feature_dataset.csv`](file:///c:/Users/sambi/Downloads/SIH%2026/data/ml/feature_dataset.csv)) contains:
> - **11 confirmed positive landslide locations** (5 in Kohima, 6 in Aizawl)
> - **0 confirmed negative locations**
> - **16,950 unknown / unlabeled grid cells**
> 
> Conventional supervised binary classifiers (such as XGBoost, Random Forest, or Logistic Regression) require both verified positive and verified negative ground truth. Randomly labeling background cells as "negative" introduces severe false-negative bias. Furthermore, dynamic precipitation, soil moisture, and SAR change features remain unpopulated pending real data downloads.

---

## 2. Current Dataset Statistics & Audit

Programmatically verified via [`scripts/audit_ml_readiness.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/audit_ml_readiness.py) and exported to [`data/ml/ml_readiness_audit.json`](file:///c:/Users/sambi/Downloads/SIH%2026/data/ml/ml_readiness_audit.json):

| Metric | Measured Value | Analysis & Implication |
| :--- | :--- | :--- |
| **Total Rows** | **16,961** | Exactly matches the combined 500 m risk grid. |
| **Total Columns** | **54** | Standardized schema covering hazard, exposure, and verification. |
| **Unique Grid Cells** | **16,961** | 100% spatial cell uniqueness; zero duplicate rows. |
| **Kohima Cells** | **6,055** (35.70%) | Full district coverage across Nagaland pilot sector. |
| **Aizawl Cells** | **10,906** (64.30%) | Full district coverage across Mizoram pilot sector. |
| **Unique Observation Dates** | **11** | 10 distinct historical event dates + 1 baseline reference snapshot (`2024-09-01`). |
| **Duplicate (cell_id, date)** | **0** | Perfect record uniqueness. |
| **Confirmed Positive Labels** | **11** ($0.065\%$) | Officially verified historical disasters (GSI/NSDMA). |
| **Confirmed Negative Labels** | **0** ($0.000\%$) | Zero confirmed negative field surveys exist. |
| **Unknown / Unlabeled Cells** | **16,950** ($99.935\%$) | Background cells protected from false negative assumption. |

---

## 3. Label-Quality Analysis: The Absence Problem

Conventional supervised binary classification optimizes a decision boundary separating class $Y=1$ from class $Y=0$. In landslide modeling, this presents a fundamental challenge:

$$\mathcal{D} = \{(x_i, y_i)\}_{i=1}^N, \quad y_i \in \{0, 1\}$$

In the NER Safe project:
1. **Confirmed Positives ($y=1, N=11$)**:
   - Georeferenced failure scars verified from government post-disaster field investigations.
2. **Confirmed Negatives ($y=0, N=0$)**:
   - **Zero authoritative non-landslide survey points exist.** No government geological authority publishes a polygon map declaring specific slopes permanently immune to failure.
3. **Unknown Background ($y = \text{NULL}, N=16,950$)**:
   - These cells represent unsurveyed or unpopulated terrain. A cell in a dense forest where no landslide was reported may have suffered an unrecorded shallow slide, or may be prone to failure under extreme rainfall.

> [!CAUTION]
> **Prohibition of Random Pseudo-Negative Sampling**
> A common bad practice in "hackathon ML" is to arbitrarily draw 100 random background points and label them as $y=0$. In steep Himalayan terrain like Kohima and Aizawl, this randomly assigns stable labels to unstable slopes with high TWI and 35° inclinations, corrupting model calibration and generating false negatives in life-critical early warning situations.

---

## 4. Historical Landslide Inventory Audit

Inspection of [`data/historical/landslide_events_cleaned.csv`](file:///c:/Users/sambi/Downloads/SIH%2026/data/historical/landslide_events_cleaned.csv) reveals 19 curated records:

| Category | Count | Percentage | Usability for 500 m Grid Training |
| :--- | :--- | :--- | :--- |
| **`VERIFIED`** | **11** | $57.9\%$ | **USABLE**: Exact GPS coordinates verified from surveyed field reports; matched to unique 500m cells. |
| **`NEEDS_VERIFICATION`** | **4** | $21.1\%$ | **UNUSABLE**: Broad village/junction centroid coordinates; crown scar not surveyed. |
| **`MISSING`** | **4** | $21.1\%$ | **UNUSABLE**: Geographic coordinates entirely absent from incident reports. |

### 4.1 Detailed Breakdown of Unusable Historical Records

To prevent false spatial associations, the following 8 records are strictly excluded from grid cell training:

1. `LS_KOH_2024_003` (*Kigwema-Mima Road Junction*): **`NEEDS_VERIFICATION`**. Coordinates ($25.591, 94.135$) represent an approximate road junction center. Assigning a 500 m cell would risk attributing terrain characteristics of an adjacent stable ridge to the failure scar.
2. `LS_KOH_2023_002` (*Kezocha Town Approach*): **`NEEDS_VERIFICATION`**. Approximate town coordinates; crown not demarcated.
3. `LS_KOH_2022_002` (*Jotsoma Bypass Section*): **`MISSING`**. Spatial coordinates unrecorded in incident bulletin.
4. `LS_KOH_2020_001` (*Old Reserve Colony*): **`MISSING`**. Urban retaining wall failure; GPS coordinates unrecorded.
5. `LS_AIZ_2024_003` (*Armed Veng / Salem Veng Sinking Area*): **`NEEDS_VERIFICATION`**. Neighborhood centroid of regional creeping slope; not an individual discrete rupture.
6. `LS_AIZ_2023_002` (*Sairang Rail Link Approach*): **`NEEDS_VERIFICATION`**. Broad railway sector centroid; specific cut-slope failure point not surveyed.
7. `LS_AIZ_2022_002` (*Rangvamual Bypass Sector*): **`MISSING`**. Spatial coordinates unrecorded.
8. `LS_AIZ_2020_002` (*Falkawn Access Corridor*): **`MISSING`**. Spatial coordinates unrecorded.

---

## 5. Environmental Feature Readiness Audit (Why Features Are Unavailable)

An investigation into the 27 unpopulated columns across all 6 environmental domains confirms why data has not yet been ingested:

| Feature Domain | Features Included | Configured Source | Ingestion Script Present? | Auth Required? | Blocking Issue | Can Be Populated Later? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Precipitation** | `rainfall_rate`, `rainfall_30min`, `rainfall_3h`, `rainfall_6h`, `rainfall_24h`, `rainfall_72h`, `rainfall_intensity`, `rainfall_duration_h`, `antecedent_rainfall_7d` | NASA GPM IMERG V07B (0.1°, ~10 km) | Yes ([`scripts/extract_historical_rainfall.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/extract_historical_rainfall.py)) | Yes (NASA Earthdata) | Earthdata credentials not yet configured; 0 HDF5 granules downloaded locally. | **YES** (Zero redesign required; run script once authenticated) |
| **Soil Moisture** | `soil_moisture_current`, `soil_moisture_previous`, `soil_moisture_change`, `soil_moisture_change_percent` | NASA SMAP Enhanced L3 9 km (SPL3SMP_E) | Yes ([`scripts/extract_historical_smap.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/extract_historical_smap.py)) | Yes (NASA Earthdata) | Earthdata credentials not yet configured; 0 HDF5 granules downloaded locally. | **YES** (Zero redesign required; run script once authenticated) |
| **SAR Change** | `vv_change_db`, `vh_change_db`, `vv_vh_change`, `change_confidence` | Copernicus Sentinel-1 IW GRD (10 m) | Yes ([`scripts/download_sentinel1.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/download_sentinel1.py) & [`scripts/process_sar_change.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/process_sar_change.py)) | Yes (NASA Earthdata) | Earthdata credentials not yet configured; catalog indexed (500 records) but 0 scenes downloaded. | **YES** (Zero redesign required; run scripts once authenticated) |
| **Context** | `vegetation_ndvi`, `flood_indicator` | Sentinel-2 (MSI) / Bhuvan Water | No standalone script | Public / Bhuvan login | Official state LULC/NDVI GeoTIFFs not yet ingested. | **YES** (Schema interface already built) |
| **Exposure** | `road_proximity_m`, `road_exposure_level`, `population_density_est`, `critical_infrastructure_count`, `impact_priority_score` | State PWD Highway GIS / WorldPop / OSM | No standalone script | Open / Local GIS | Vector shapefiles of roads and settlements not yet ingested. | **YES** (Schema interface already built) |
| **Verification** | `citizen_report_count`, `verification_timestamp`, `verification_confidence` | Mobile Incident Reporting System | Schema only | App Backend Auth | Mobile field reporting database not yet deployed. | **YES** (Schema interface already built) |

---

## 6. Real Data Sources Needed & Source-Readiness Table

| Feature Group | Authoritative Source | Native Resolution | Temporal Frequency | Access Portal | Current Status | Next Technical Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Static Terrain** | Copernicus DEM GLO-30 | 30 m | Static snapshot | AWS Open Data (Public) | **COMPLETE** | Ready for baseline modeling. |
| **Rainfall** | NASA GPM IMERG V07B | 0.1° (~10 km) | 30 minutes | NASA Earthdata / GES DISC | Ingestion script ready; credentials pending | Set `EARTHDATA_USERNAME` & download event granules. |
| **Soil Moisture** | NASA SMAP Enhanced L3 | 9 km | Daily | NASA Earthdata / NSIDC | Ingestion script ready; credentials pending | Set `EARTHDATA_USERNAME` & download event granules. |
| **Radar Disturbance** | Copernicus Sentinel-1 IW | 10 m | 12 days | ASF DAAC | Ingestion scripts ready; test set curated | Download 4 test scenes (~4.1 GB) & run `process_sar_change.py`. |
| **Landslide Inventory** | GSI Bhukosh / NLSM | 1:50,000 scale | Event-based | Geological Survey of India Portal | 11 verified events curated | Ingest GSI National Landslide Susceptibility inventory shapefile. |
| **Road Lifelines** | OpenStreetMap / State PWD | Vector lines | Static | Geofabrik India / State GIS | Schema ready; data unlinked | Compute Euclidean distance to NH-29 & NH-54. |

---

## 7. Possible Labeling Strategies for Negative Samples

To establish a defensible binary dataset without fabricating fake negatives, four technical strategies are evaluated:

| Strategy | Description | Required Data | Project Availability | False Negative Risk | Viability for Step 9 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. True Absence Field Surveys** | Ground-truth sites certified as stable by geological engineers during comprehensive field campaigns. | Published GSI stable slope inventory | **NOT AVAILABLE** in public portal | Zero | **Ideal, but blocked** pending government survey access. |
| **2. Geomorphometric Constraint Sampling** | Drawing negative samples exclusively from terrain where physical shear failure is mechanically impossible (e.g. mean slope $< 5^\circ$ on wide alluvial plains/river floodplains). | Verified 30 m DEM | Available, but **0 cells in Kohima or Aizawl have mean slope $< 5^\circ$** (minimum slope is $5.17^\circ$) | High (even low-slope foothills in NE India experience toe-undercutting) | **NOT VIABLE** in steep dissected hill terrain. |
| **3. Multi-Temporal Dry-Season Observation Windows** | Using the 11 verified positive cells during dry winter periods ($0\text{ mm}$ rain, low SMAP moisture) as negative temporal instances of the *same* physical cells. | Temporal IMD/GPM rainfall records | Script available; data download pending | Moderate (identifies non-triggering conditions, not non-susceptible slopes) | **VIABLE for Dynamic Trigger Modeling** once rainfall is downloaded. |
| **4. Positive-Unlabeled (PU) Learning / One-Class Modeling** | Treating the problem as identifying similarity to known positives without assuming unobserved background is negative (e.g., One-Class SVM, Biased Logistic Regression, or Heuristic Susceptibility Index). | Verified positives (11) + Static Terrain (16,961) | **CURRENTLY AVAILABLE** | Zero (avoids fabricating negatives) | **RECOMMENDED SCIENTIFIC APPROACH FOR STEP 9**. |

---

## 8. Temporal Dataset Alignment Requirements

A dynamic early warning model requires observations indexed by:

$$\text{Observation Record} = (\text{cell\_id}, \text{observation\_date}, \mathbf{x}_{\text{terrain}}, \mathbf{x}_{\text{rain}}(t), \mathbf{x}_{\text{smap}}(t), \mathbf{x}_{\text{sar}}(t), y)$$

Currently:
- Static terrain $\mathbf{x}_{\text{terrain}}$ is populated for all 16,961 cells.
- Dynamic vectors $\mathbf{x}_{\text{rain}}(t), \mathbf{x}_{\text{smap}}(t), \mathbf{x}_{\text{sar}}(t)$ are empty.
- When real Earthdata granules are downloaded, the pipeline will align GPM IMERG precipitation accumulations (30min, 3h, 24h, 72h) and SMAP volumetric moisture with each cell's observation date.

---

## 9. Spatial Validation Strategy for Step 9

Because geographic grid cells exhibit intense spatial autocorrelation (a cell's slope and elevation are nearly identical to its adjacent neighbor), standard random K-Fold cross-validation produces **severe spatial data leakage** and falsely inflated accuracy metrics (e.g., fake $98\%$ ROC-AUC).

### Proposed Validation Architecture for Step 9:
1. **Spatial Block Cross-Validation**:
   - Divide Kohima and Aizawl into contiguous spatial blocks (e.g. $5\text{ km} \times 5\text{ km}$ clusters).
   - Train on blocks $A, B, C$; evaluate on spatially disjoint block $D$.
2. **Cross-District Spatial Holdout**:
   - Train on Kohima District; evaluate out-of-domain transferability on Aizawl District (and vice versa).
3. **Temporal Holdout**:
   - Train on verified events from 2020–2023; evaluate on the 2024 monsoon events (e.g. Dzüdza Bridge failure and Melthum quarry disaster).

---

## 10. Data Leakage Safeguards

The following columns in `data/ml/feature_dataset.csv` directly encode ground-truth information and **MUST BE EXCLUDED** from the feature matrix $\mathbf{X}$ during any modeling in Step 9:
- `historical_event_id` (contains `LS_KOH_*` codes)
- `event_location_name` (text string identifying disaster site)
- `label_quality` (states `VERIFIED_HISTORICAL`)
- `cell_id`, `district`, `state` (spatial identifiers, unless used explicitly for group k-fold partitioning)

---

## 11. Explicit List of What Must NOT Be Fabricated

To maintain uncompromising ethical and scientific standards:
1. **Never fabricate negative landslide samples** by randomly tagging unobserved hillsides as $y=0$.
2. **Never simulate rainfall numbers** or generate random millimetre totals to populate GPM columns.
3. **Never synthesize soil moisture percentages** or interpolate fictitious saturation curves.
4. **Never create synthetic SAR decibel changes** to make change-detection algorithms look active.
5. **Never invent road proximity distances or population counts** without authoritative GIS layers.
6. **Never report fake model performance metrics** (e.g. fabricated ROC-AUC, F1-scores, or precision curves).

---

## 12. Recommended Next Technical Actions for Step 9

1. **Implement an Authoritative Heuristic Susceptibility Baseline**:
   - Compute a standard geomorphological Landslide Susceptibility Index (LSI) based on verified slope, curvature, and TWI physics (e.g. Mora-Vahrson or Weight-of-Evidence framework) across all 16,961 cells.
2. **Formulate Step 9 as Positive-Unlabeled (PU) / Anomaly Detection**:
   - Utilize One-Class classification or PU-learning algorithms that calibrate susceptibility using the 11 verified positive landslide cells without making ungrounded negative assumptions.
3. **Prepare the Data Ingestion Bridge for Earthdata Access**:
   - Once credentials are provided, execute the existing download scripts to ingest real GPM IMERG and SMAP dynamic layers.
