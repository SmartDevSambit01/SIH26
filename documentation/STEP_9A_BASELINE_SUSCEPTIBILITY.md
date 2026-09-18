# STEP 9A — Baseline Landslide Susceptibility Model and Positive-Unlabeled Analysis

**NER Safe (SIH 2026) — AI-Based Early Warning and Landslide Risk Monitoring System**
**Pilot Districts: Kohima (Nagaland) · Aizawl (Mizoram)**

---

## 1. Purpose

STEP 9A establishes a **transparent, reproducible terrain susceptibility baseline** across
the full 500 m × 500 m analysis grid. It serves two distinct functions:

1. **Terrain Susceptibility Index (TSI)**: A physics-based, heuristic multi-criteria score
   that ranks every grid cell by its geomorphological predisposition to slope failure, using
   only verified Copernicus DEM-derived terrain attributes. This is **not** a trained ML model.

2. **Positive-Unlabeled (PU) Terrain Similarity Analysis**: A statistical comparison of each
   grid cell's terrain signature against the multivariate profile of the 11 verified historical
   landslide sites. This quantifies how closely a cell's physical environment matches known
   failure terrain without fabricating any negative training labels.

> [!IMPORTANT]
> STEP 9A is a **pre-ML baseline**. It explicitly avoids conventional supervised binary
> classification (XGBoost, Random Forest, Logistic Regression, Neural Networks) because the
> project currently has only 11 confirmed positive samples and zero confirmed negative samples.
> Attempting supervised classification under these conditions would be scientifically invalid.

---

## 2. Input Data Sources

All inputs used in STEP 9A are derived exclusively from verified, authoritative data sources.
No synthetic, interpolated, or fabricated values are used.

| Input | Source File | Provenance |
| :--- | :--- | :--- |
| **Terrain morphometry** | `data/historical/grid_terrain_features.csv` | Derived from Copernicus DEM GLO-30 (30 m resolution) via [`scripts/derive_morphometry.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/derive_morphometry.py) |
| **Historical landslide events** | `data/historical/landslide_events_cleaned.csv` | GSI/NSDMA field-verified disaster records; 11 records with GPS coordinates confirmed to 500 m grid cell precision |
| **500 m analysis grid** | `data/boundaries/` | Created in STEP 2 via [`scripts/create_risk_grid.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/create_risk_grid.py) |

### Terrain Attributes Used

Derived at 500 m cell resolution by aggregating 30 m DEM pixels within each cell:

| Attribute | Unit | Physical Role in Slope Stability |
| :--- | :--- | :--- |
| `slope_mean` | Degrees (°) | Primary driver of gravitational shear stress along the failure plane |
| `slope_max` | Degrees (°) | Peak steepness within the cell; identifies sharp escarpments and road cuts |
| `twi_mean` | Dimensionless | Topographic Wetness Index; quantifies hydrological convergence and pore-water pressure accumulation |
| `curvature_mean` | m⁻¹ | Profile/planform curvature; negative (concave) values indicate runoff convergence hollows |
| `elevation_mean` | Metres (m) | Absolute elevation above sea level |
| `elevation_min` | Metres (m) | Minimum elevation within the 500 m cell |
| `elevation_max` | Metres (m) | Maximum elevation within the 500 m cell |

---

## 3. Terrain Susceptibility Index (TSI): Scoring Methodology

### 3.1 Factor Normalization

Each physical attribute is independently normalized to the continuous range **[0.0, 1.0]**
using physically motivated, domain-specific transformations. Normalization parameters are
**explicitly declared** and **not learned** from data.

| Factor | Normalization Formula | Physical Justification |
| :--- | :--- | :--- |
| **Slope Factor** | `clip(0.6×slope_mean + 0.4×slope_max, 0, 45) / 45` | Weighted blend emphasizes mean steepness but penalizes extreme local scarps; 45° is used as practical upper bound in dissected Himalayan terrain |
| **TWI Factor** | `clip((twi_mean − 4.0) / 4.0, 0, 1)` | TWI range in the study area is 4.0–10.0; values ≥ 6 indicate convergent hollows at elevated pore-water risk |
| **Curvature Factor** | `clip(0.5 − curvature_mean × 1.5, 0, 1)` | Concave (negative) curvature raises the factor; convex ridges are lower risk |
| **Relief Factor** | `clip((elevation_max − elevation_min) / 250.0, 0, 1)` | Local relief of 250 m within a 500 m cell indicates steep dissected topography |

### 3.2 TSI Computation

The Terrain Susceptibility Index is a **linear weighted combination** of the four normalized factors:

```
TSI = 100 × (w_slope × slope_factor + w_twi × twi_factor + w_curv × curv_factor + w_relief × relief_factor)
```

Three heuristic weight configurations are available, selected at runtime via `--config`:

| Configuration | w_slope | w_twi | w_curv | w_relief | Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BALANCED` (default) | 0.45 | 0.25 | 0.15 | 0.15 | General-purpose; balanced geomorphic weighting |
| `SLOPE_DOMINANT` | 0.60 | 0.20 | 0.10 | 0.10 | Rock-dominated steep terrain; translational failures |
| `HYDRO_DOMINANT` | 0.35 | 0.40 | 0.15 | 0.10 | Saturated colluvial soils; debris flows |

> [!WARNING]
> **These weights are heuristic and provisional.** They are drawn from geomorphological expert
> knowledge of Himalayan terrain failure mechanics, not optimized against a labeled training
> dataset. They will be updated once sufficient verified positive and negative ground-truth
> samples are available for data-driven weight calibration.

### 3.3 TSI Classification Thresholds

| TSI Score Range | Class | Interpretation |
| :--- | :--- | :--- |
| 85.0 – 100.0 | `VERY_HIGH` | Extreme terrain susceptibility; steep convergent hollows with high local relief |
| 70.0 – 84.9 | `HIGH` | High susceptibility; combination of steep slopes and hydrological convergence |
| 50.0 – 69.9 | `MODERATE` | Moderate susceptibility; typical of dissected hill terrain in NE India |
| 30.0 – 49.9 | `LOW` | Lower susceptibility; gentler slopes or convex ridgelines |
| 0.0 – 29.9 | `VERY_LOW` | Minimal terrain susceptibility; flat or broad ridge terrain |
| — | `NODATA_BORDER` | Insufficient DEM coverage within the 500 m cell boundary; no score assigned |

### 3.4 Attribution / Explainability Output

For each scored cell, the `primary_terrain_contributors` field records the percentage
contribution of each normalized factor to the total TSI score. Example:
```
Slope (52%), TWI (22%), Curvature (15%), Relief (11%)
```
This supports transparent, auditable decision-making for operational hazard officers.

---

## 4. Current TSI Results — Dataset Statistics

Computed across the full 500 m × 500 m analysis grid using the `BALANCED` configuration:

| Metric | Value |
| :--- | :--- |
| **Total grid cells** | 16,961 |
| **Kohima cells** | 6,055 |
| **Aizawl cells** | 10,906 |
| **NODATA_BORDER cells** | 2,895 |
| **Cells with valid TSI scores** | 14,066 |
| **TSI Score range** | 17.45 – 89.57 |

### TSI Class Distribution

| Class | Count | Percentage |
| :--- | :--- | :--- |
| VERY_HIGH | 26 | 0.15% |
| HIGH | 1,659 | 9.78% |
| MODERATE | 10,938 | 64.49% |
| LOW | 1,436 | 8.47% |
| VERY_LOW | 7 | 0.04% |
| NODATA_BORDER | 2,895 | 17.07% |

> [!NOTE]
> The predominance of MODERATE-class terrain reflects the characteristic steep-but-rolling
> dissected hill topography of the Naga Hills and Mizo Hills, where the entire terrain has
> inherently elevated slope angles (regional minimum slope: 5.17°).

---

## 5. Ground-Truth Label Status

### 5.1 Label Distribution

STEP 9A enforces the **Anti-Fabrication and Scientific Truthfulness Protocol**:

| Label Status | Count | Meaning |
| :--- | :--- | :--- |
| `CONFIRMED_POSITIVE` | **11** | Grid cells hosting a GSI/NSDMA-verified historical landslide with exact GPS coordinates matched to the 500 m cell |
| `UNKNOWN` | **16,950** | All remaining cells — not confirmed stable; may be prone to failure |
| `CONFIRMED_NEGATIVE` | **0** | Intentionally absent — no authoritative stable-slope inventory exists |

### 5.2 Confirmed Positive Cells

The 11 verified historical landslide sites matched to 500 m grid cells:

| Cell ID | District | TSI Score | TSI Class | PU Similarity | Event ID |
| :--- | :--- | :--- | :--- | :--- | :--- |
| KOH_01187 | Kohima | 64.69 | MODERATE | 0.6527 | LS_KOH_2022_001 |
| KOH_01378 | Kohima | 61.48 | MODERATE | 0.8558 | LS_KOH_2024_001 |
| KOH_02654 | Kohima | 50.39 | MODERATE | 0.7780 | LS_KOH_2021_001 |
| KOH_03071 | Kohima | 56.20 | MODERATE | 0.7987 | LS_KOH_2023_001 |
| KOH_03175 | Kohima | 58.02 | MODERATE | 0.6038 | LS_KOH_2024_002 |
| AIZ_01960 | Aizawl | 62.59 | MODERATE | 0.7417 | LS_AIZ_2024_001 |
| AIZ_02185 | Aizawl | 64.88 | MODERATE | 0.4673 | LS_AIZ_2024_002 |
| AIZ_02314 | Aizawl | 74.62 | HIGH | 0.6329 | LS_AIZ_2021_001 |
| AIZ_02321 | Aizawl | 57.06 | MODERATE | 0.8397 | LS_AIZ_2023_001 |
| AIZ_02431 | Aizawl | 60.72 | MODERATE | 0.3679 | LS_AIZ_2020_001 |
| AIZ_02559 | Aizawl | 63.26 | MODERATE | 0.8643 | LS_AIZ_2022_001 |

> [!NOTE]
> 10 of 11 verified landslide sites fall in the MODERATE TSI class. This is consistent
> with NE India's terrain character: even relatively moderate-scoring cells on the 0–100 scale
> represent geologically susceptible slopes when absolute slope angles remain above 20°.
> Only AIZ_02314 (Aizawl 2021) reaches HIGH class.

---

## 6. Positive-Unlabeled (PU) Terrain Similarity Analysis

### 6.1 Why PU Analysis, Not Supervised Classification

Conventional supervised binary ML requires both confirmed positive samples (y=1) and
confirmed negative samples (y=0). In the NER Safe dataset:

- **y=1 (Positives):** 11 GPS-verified landslide sites
- **y=0 (Negatives):** **Zero authoritative confirmed non-landslide survey points**
- **Unlabeled Background:** 16,950 cells — cannot be assumed stable

Randomly assigning background cells as y=0 would inject severe false-negative bias:
in steep terrain where every cell exceeds 5° slope, labeling arbitrary hillsides as
"confirmed stable" corrupts the classifier and generates dangerous false assurance.

### 6.2 PU Reference Profile: Fitting the Positive Cluster

The **PU Reference Profile** is computed by measuring the multivariate mean (μ) and
standard deviation (σ) of the 11 verified positive cells across five terrain dimensions:

| Terrain Dimension | Physical Meaning |
| :--- | :--- |
| `slope_mean` | Average slope angle across the failure cell |
| `slope_max` | Steepest point within the failure cell |
| `twi_mean` | Hydrological convergence at the failure location |
| `curvature_mean` | Concavity/convexity of the failure slope |
| `elevation_mean` | Elevation above sea level of the failure site |

This produces a five-dimensional reference centroid representing the terrain signature
of known historical failures.

### 6.3 PU Similarity Score Computation

For each unlabeled cell, the **standardized Euclidean distance** from the positive
reference centroid is computed:

```
norm_diff = (cell_vector − μ_pos) / σ_pos
distance  = sqrt(sum(norm_diff²))
```

This is converted to a **Gaussian similarity kernel** on [0.0, 1.0]:

```
similarity = exp(−0.5 × (distance / 2.5)²)
```

A similarity of 1.0 indicates terrain identical to the verified positive cluster.
A similarity near 0.0 indicates physically dissimilar terrain.

### 6.4 PU Similarity Classification

| Similarity Range | Class | Interpretation |
| :--- | :--- | :--- |
| > 0.75 | `HIGH_TERRAIN_SIMILARITY` | Terrain environment closely resembles verified failure sites |
| 0.40 – 0.75 | `MODERATE_TERRAIN_SIMILARITY` | Partially similar; requires additional dynamic triggers for risk assessment |
| 0.15 – 0.40 | `LOW_TERRAIN_SIMILARITY` | Limited terrain resemblance to historical failure sites |
| < 0.15 | `DISSIMILAR_TERRAIN` | Terrain environment substantially different from known failure sites |
| — | `NODATA_BORDER` | No terrain data available; no similarity computed |

> [!WARNING]
> **PU similarity is NOT a probability of landslide occurrence.** It is a terrain
> similarity metric only. A HIGH_TERRAIN_SIMILARITY cell has physical terrain resembling
> historical failure sites but may require specific rainfall, seismic, or anthropogenic
> triggers to fail. An UNKNOWN label means we have no ground-truth evidence either way.

---

## 7. Spatial Block Partitioning

All 16,961 cells are assigned to **5 km × 5 km spatial blocks** to prevent spatial
autocorrelation leakage in future ML validation:

- Kohima blocks: prefixed `BLK_KOH_Rnn_Cnn`
- Aizawl blocks: prefixed `BLK_AIZ_Rnn_Cnn`
- Total unique spatial blocks: **243**

When future ML models are trained, spatially disjoint block groups will be used as
cross-validation folds to avoid inflated accuracy from neighboring cell leakage.

---

## 8. What This Is NOT

| What STEP 9A produces | What it explicitly does NOT produce |
| :--- | :--- |
| Heuristic terrain susceptibility index | A trained predictive model |
| PU terrain similarity scores | Probability of landslide occurrence |
| Transparent, auditable factor weights | Data-driven optimized weights |
| Spatial block assignments for future CV | Cross-validation performance metrics |
| 11 verified positive cell identifiers | Any inferred negative samples |

> [!CAUTION]
> Do not report TSI scores or PU similarity values as model accuracy, precision, recall,
> F1-score, or ROC-AUC. No such metrics exist or are appropriate at this stage.
> The STEP 9A output is a **baseline spatial layer**, not a ML model prediction.

---

## 9. Known Limitations

1. **Static analysis only.** TSI uses only time-invariant terrain attributes (slope, TWI,
   curvature, relief). It does not incorporate dynamic triggers: antecedent rainfall,
   soil moisture saturation, seismic loading, or road-cut destabilization.

2. **Heuristic weights are unvalidated.** The BALANCED, SLOPE_DOMINANT, and HYDRO_DOMINANT
   weight configurations are based on regional geomorphological expert knowledge. They have
   not been calibrated against a statistically sufficient labeled training set.

3. **Small positive reference set.** The PU reference profile is fit on 11 cells. With such
   a small positive set, the σ values in several terrain dimensions are high, producing
   wide similarity kernels. The similarity scores are indicative, not probabilistic.

4. **NODATA coverage.** 2,895 cells (17.1%) at district boundaries have insufficient DEM
   coverage and are excluded from TSI and PU analysis.

5. **No negative ground truth.** The complete absence of confirmed non-landslide survey
   points prevents supervised binary classification and limits quantitative model evaluation.

6. **Uniform cell resolution.** The 500 m grid aggregates terrain diversity within each cell.
   Sub-cell heterogeneity (e.g., a 30 m scar within a 500 m moderate-slope cell) may cause
   some historical sites to appear in lower-scoring cells than their actual micro-topographic
   condition warrants.

---

## 10. Future Path Toward Supervised ML

The following technical path leads from the STEP 9A heuristic baseline to a scientifically
defensible supervised ML model:

### Prerequisite 1 — Negative Ground Truth Acquisition
Obtain authoritative non-landslide survey points from:
- GSI National Landslide Susceptibility Mapping Programme stable-slope polygons
- Field engineering surveys along NH-29 and NH-54 certified stable sections
- Multi-temporal dry-season SAR coherence analysis identifying permanently stable terrain

### Prerequisite 2 — Dynamic Feature Population
Populate currently empty feature columns in `data/ml/feature_dataset.csv` by:
- Downloading NASA GPM IMERG V07B HDF5 granules (requires NASA Earthdata credentials)
- Downloading NASA SMAP Enhanced L3 daily composites (requires NASA Earthdata credentials)
- Processing 4 curated Sentinel-1 SAR scene pairs through `scripts/process_sar_change.py`

### Prerequisite 3 — Label Volume Expansion
Source additional verified positive landslide inventory from:
- GSI Bhukosh national disaster database
- NLSM (National Landslide Susceptibility Mapping) inventory shapefile
- State Disaster Management Authority (SDMA) Nagaland and Mizoram field reports
- Bhuvan NRSC landslide atlas polygons

### Minimum Training Threshold for Supervised ML
Industry practice for spatial hazard modeling recommends ≥ 100–200 verified positive
samples per district before conventional binary classifiers (XGBoost, Random Forest) are
trained. Current inventory: **5 Kohima, 6 Aizawl**. Supervised ML is not appropriate until
this threshold is reached.

### When These Prerequisites Are Met
- Replace PU similarity with calibrated One-Class SVM or PU Learning (elkanoto / pulearn)
- Transition to spatial block cross-validation (5 km blocks already pre-assigned)
- Train XGBoost or Random Forest on verified positive + authoritative negative pairs
- Report calibrated probability scores per cell (not TSI heuristic scores)

---

## 11. Output Dataset Schema

File: [`data/ml/baseline_susceptibility.csv`](file:///c:/Users/sambi/Downloads/SIH%2026/data/ml/baseline_susceptibility.csv)

| Column | Type | Description |
| :--- | :--- | :--- |
| `cell_id` | String | Unique 500 m grid cell identifier (e.g., `KOH_01187`) |
| `district` | String | District name: `Kohima` or `Aizawl` |
| `latitude` | Float | Cell centroid latitude (WGS84, decimal degrees) |
| `longitude` | Float | Cell centroid longitude (WGS84, decimal degrees) |
| `spatial_block_id` | String | 5 km spatial block identifier for future spatial CV |
| `slope_mean` | Float or empty | Mean slope (degrees); empty for NODATA cells |
| `elevation_mean` | Float or empty | Mean elevation (metres); empty for NODATA cells |
| `curvature_mean` | Float or empty | Mean profile curvature (m⁻¹); empty for NODATA cells |
| `twi_mean` | Float or empty | Mean Topographic Wetness Index; empty for NODATA cells |
| `terrain_susceptibility_score` | Float [0–100] or empty | Heuristic TSI score; empty for NODATA cells |
| `terrain_susceptibility_class` | String | TSI class: VERY_LOW / LOW / MODERATE / HIGH / VERY_HIGH / NODATA_BORDER |
| `pu_terrain_similarity` | Float [0–1] or empty | Gaussian terrain similarity to positive cluster; empty for NODATA cells |
| `pu_similarity_class` | String | PU class: HIGH / MODERATE / LOW / DISSIMILAR / NODATA_BORDER |
| `primary_terrain_contributors` | String | Percentage attribution of each factor to TSI score |
| `label_status` | String | `CONFIRMED_POSITIVE` (11 cells) or `UNKNOWN` (16,950 cells) |
| `historical_event_id` | String | Event ID (e.g., `LS_KOH_2022_001`) for positives; empty for UNKNOWN |

---

## 12. Validation

Dataset integrity is enforced by [`scripts/validate_baseline_susceptibility.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/validate_baseline_susceptibility.py).

### Validation Run — STEP 9A Completion

```
python scripts/validate_baseline_susceptibility.py
```

**Result: 21/21 integrity checks PASSED**

Checks cover:
- Structural integrity (row count, columns, unique IDs)
- Geographic validity (district names, coordinate ranges, spatial block format)
- Label integrity and anti-fabrication (no negative labels, exactly 11 positives, 16,950 unknown)
- Terrain feature value ranges (TSI 0–100, NODATA handling)
- PU similarity value ranges (0.0–1.0)
- Explainability field completeness

---

## 13. Scripts

| Script | Purpose |
| :--- | :--- |
| [`scripts/build_baseline_susceptibility.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/build_baseline_susceptibility.py) | Runs the STEP 9A pipeline: loads terrain data, computes TSI, fits PU reference profile, writes output CSV |
| [`scripts/validate_baseline_susceptibility.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/validate_baseline_susceptibility.py) | Validates all integrity conditions on the output CSV (21 checks) |

### Rebuilding the Baseline

If re-running the pipeline from scratch:

```bash
python scripts/build_baseline_susceptibility.py --config BALANCED
python scripts/validate_baseline_susceptibility.py
```

Available `--config` values: `BALANCED` (default), `SLOPE_DOMINANT`, `HYDRO_DOMINANT`

---

*Generated: STEP 9A completion — NER Safe SIH 2026 project*
*Anti-Fabrication Protocol: Active — zero synthetic or fabricated values in this document*
