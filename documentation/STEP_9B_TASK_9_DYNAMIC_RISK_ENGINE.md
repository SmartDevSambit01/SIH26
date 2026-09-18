# Step 9B — Task 9: Dynamic Landslide Risk Engine Documentation

## 1. Purpose
The Dynamic Landslide Risk Engine is a transparent, data-driven policy baseline built to evaluate landslide hazard across 500m grid cells in Kohima (Nagaland) and Aizawl (Mizoram). It merges static terrain morphometry susceptibility with multi-temporal dynamic meteorological and satellite trigger factors without fabricating data or misrepresenting uncalibrated heuristics as trained artificial intelligence.

---

## 2. Core Architecture
The system maintains strict architectural separation between **Physical Hazard Susceptibility**, **Dynamic Triggers**, and **Exposure / Vulnerability**:

```text
+-------------------------------------------------------------------------+
|                      STATIC TERRAIN SUSCEPTIBILITY                      |
|  - SRTM 30m DEM Morphometry (Slope, Curvature, TWI, Relief)             |
|  - GSI Historical Landslide Inventory PU Learning Similarity            |
|  -> Baseline Terrain Susceptibility Index (TSI: 0 to 100)               |
+-------------------------------------------------------------------------+
                                     +
+-------------------------------------------------------------------------+
|                         DYNAMIC TRIGGER FEEDS                           |
|  - NASA GPM IMERG Precipitation (Half-Hourly, 0.1 deg)                  |
|  - NASA SMAP Volumetric Soil Moisture (Daily, 9km EASE-Grid)            |
|  - Hydrological Riverine Inundation (Drainage flood indicator)          |
|  - Copernicus Sentinel-1 C-SAR Backscatter Difference (VV/VH dB)        |
|  - Field Inspection & Citizen Incident Reports (Ground truth)           |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       DATA AVAILABILITY GATEKEEPER                      |
|  - Evaluates operational status per feed: AVAILABLE,                    |
|    REQUIRES_EXTERNAL_AUTH, NOT_YET_IMPLEMENTED                          |
|  - If required dynamic feeds are unavailable -> Halts dynamic scoring.  |
|  - Returns DYNAMIC_RISK_UNAVAILABLE honestly (No fake or zero values).   |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                    DYNAMIC TRIGGER & COMBINED SCORING                   |
|  - Dynamic Trigger Score = sum(weight_i * normalized_score_i)           |
|  - Combined Score = (0.50 * Baseline TSI) + (0.50 * Dynamic Triggers)   |
|  - Categorized into Policy Risk Levels: Critical, High, Warning, Watch, |
|    Low                                                                  |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  EXPLAINABLE EVIDENCE & RECOMMENDATION                  |
|  - Full contributing factor breakdown (raw, normalized, weighted)       |
|  - Confidence vs. Risk separation                                       |
+-------------------------------------------------------------------------+

*Note: Infrastructure, roads, population, and settlements belong strictly to
 the future EXPOSURE / IMPACT layer. They are NOT treated as direct physical
 triggers of slope failure.*
```

---

## 3. Static Baseline Susceptibility
- **Source:** `data/ml/baseline_susceptibility.csv` (derived from SRTM 30m DEM).
- **Metric:** Terrain Susceptibility Index (TSI, 0 to 100).
- **Classification:** `VERY_LOW`, `LOW`, `MODERATE`, `HIGH`, `VERY_HIGH`.
- **Status:** 100% complete and cached in memory across all 16,961 cells (Kohima: 6,055, Aizawl: 10,906).
- **Labeling Rule:** Always identified as *Baseline Terrain Susceptibility*. It is never described as an ML prediction or validated probability.

---

## 4. Dynamic Trigger Inputs
The dynamic engine ingests five distinct observation categories:
1. **Precipitation (GPM IMERG):** Intensity (`rainfall_rate` mm/h), short-term accumulations (`rainfall_30min`, `rainfall_3h`, `rainfall_6h`), daily triggers (`rainfall_24h`, `rainfall_72h`), and prolonged saturation (`antecedent_rainfall_7d`).
2. **Soil Moisture (SMAP 9km):** `soil_moisture_current` (volumetric water content m³/m³), `soil_moisture_previous`, `soil_moisture_change`, and `soil_moisture_change_percent`.
3. **Hydrological Flood:** `flood_indicator` (boolean indicating active surface inundation or toe-slope erosion).
4. **Sentinel-1 SAR Change:** `vv_change_db`, `vh_change_db`, `vv_vh_change`, and `change_confidence`. Corroborating anomaly evidence only; never an automatic label.
5. **Human Verification:** `citizen_report_count`, `officer_verification_status` (`UNVERIFIED`, `REPORTED`, `VERIFIED`, `REJECTED`), and historical site confirmation.

---

## 5. Transparent Weight Configuration
All weights are defined in a centralized, documented configuration (`DYNAMIC_WEIGHTS` in `backend/app/services/risk_engine.py`). They are transparent policy weights rather than unexplainable coefficients:

| Trigger Factor | Policy Weight | Percentage | Role |
|---|---|---|---|
| Precipitation (GPM) | `0.45` | 45% | Primary meteorological trigger |
| Soil Moisture (SMAP) | `0.35` | 35% | Primary antecedent pore-water pressure trigger |
| Flood Inundation | `0.10` | 10% | Corroborating toe-erosion / saturation factor |
| Sentinel-1 SAR Change | `0.05` | 5% | Corroborating radar backscatter anomaly |
| Field Verification | `0.05` | 5% | Corroborating ground inspection evidence |
| **Total** | **`1.00`** | **100%** | |

**Baseline Combination Configuration:**
- `baseline_susceptibility`: `0.50` (50%)
- `dynamic_triggers`: `0.50` (50%)

---

## 6. Normalization & Scoring
- **Precipitation:** Normalizes short-term intensity (up to 50 mm/h) and 24-hour accumulation (up to 150 mm) onto a 0–100 scale:
  $$\text{Score}_{\text{rain}} = \min\left(100, \frac{\text{rate}}{50} \times 40 + \frac{R_{24h}}{150} \times 60\right)$$
- **Soil Moisture:** Evaluates volumetric water content relative to steep hillslope saturation limits (0.05 to 0.50 m³/m³):
  $$\text{Score}_{\text{soil}} = \min\left(100, \frac{\text{current}}{0.50} \times 100\right)$$
- **SAR Anomaly:** Evaluates backscatter decibel differential relative to significant ground disruption thresholds ($|\Delta \sigma^\circ| \ge 3 \text{ dB}$).
- **Verification:** Historical verified site = 100.0; officer verified = 100.0; citizen reported = 50.0; unverified = 0.0.

---

## 7. Calibration Requirement
> **Scientific Integrity Requirement:** The normalization thresholds above are prototype policy baselines. They **require formal empirical calibration** against verified historical landslide events and regional geotechnical rainfall threshold curves (e.g., Caine intensity-duration curves calibrated specifically for Northeast Indian terrain). The engine explicitly returns:
> `calibration_status = "NOT_CALIBRATED_REQUIRES_VERIFIED_EVENTS"`

---

## 8. Prototype Policy Risk Levels
Combined hazard scores map to five standardized operational categories:

| Level | Score Range | Color Name | Hex Code | Action Advisory |
|---|---|---|---|---|
| **Critical** | $\ge 80.0$ | Purple | `#A855F7` | Immediate slope advisory; toe-slope evacuation |
| **High** | $60.0 - 79.9$ | Red | `#EF4444` | Severe distress warning; restrict hill transport |
| **Warning** | $45.0 - 59.9$ | Orange | `#F97316` | Early warning; inspect drainage cut-slopes |
| **Watch** | $30.0 - 44.9$ | Yellow | `#EAB308` | Advisory watch; monitor antecedent saturation |
| **Low** | $< 30.0$ | Green | `#22C55E` | Standard monitoring; stable conditions |

---

## 9. Data Availability Logic
The engine adheres to strict anti-fabrication rules:
- If GPM or SMAP feeds require external credentials (`REQUIRES_EXTERNAL_AUTH`), the engine **refuses to invent synthetic observations**.
- Dynamic trigger score and combined risk score are returned as `null`.
- The cell status is explicitly marked:
  ```json
  "risk_status": "DYNAMIC_RISK_UNAVAILABLE",
  "dynamic_trigger_score": null,
  "combined_risk_score": null
  ```
- Meanwhile, the static baseline susceptibility remains fully accessible (`AVAILABLE`, TSI score 0–100).
- This prevents dangerous false-negative or false-positive alarms caused by default zeroes or fabricated mock numbers.

---

## 10. Explainability & Evidence Breakdown
Every risk assessment returns a transparent evidence list detailing every contributing factor:
```json
{
  "factor": "rainfall",
  "status": "REQUIRES_EXTERNAL_AUTH",
  "raw_value": null,
  "normalized_score": null,
  "weight": 0.45,
  "weighted_contribution": null,
  "description": "NASA GPM IMERG observations require NASA Earthdata login credentials. No fake rainfall values generated."
}
```
If dynamic inputs are provided (e.g. during calibrated live feeds or test fixtures), the exact raw values, normalized scores, and mathematical contributions are displayed so emergency officers can audit why an alert was triggered.

---

## 11. Confidence vs. Risk Separation
The system never conflates **Hazard Risk** with **Data Confidence**:
- `combined_risk_score`: Represents the physical potential for slope failure (0 to 100).
- `data_completeness`: Represents the fraction of active sensor feeds currently reporting valid data (0.0 to 1.0).
- Missing data lowers data completeness and sets status to `DYNAMIC_RISK_UNAVAILABLE`; it does not artifically lower the perceived risk to "Low" or "Safe".

---

## 12. Current Limitations
- **NASA Earthdata Credentials:** Dynamic GPM rainfall and SMAP soil moisture pipelines currently require external user credentials for automatic live polling.
- **Sentinel-1 Bandwidth:** Real-time SAR scene downloads and InSAR phase unwrapping are computationally intensive and operate on a 12-day orbital repeat cycle rather than real-time feeds.
- **Label Sparsity:** Only 11 verified positive historical landslide sites exist in the GSI catalog for Kohima and Aizawl, preventing high-confidence supervised ML training.

---

## 13. Why This is NOT a Trained ML Model
1. **Scientific Honesty:** Supervised machine learning algorithms (Random Forest, XGBoost, Deep Neural Networks) trained on only 11 verified positive labels across 16,961 cells would suffer from catastrophic class imbalance and severe spatial overfitting.
2. **Deterministic Transparency:** Emergency managers and district disaster authorities in Nagaland and Mizoram require inspectable causal logic rather than black-box probability predictions.
3. **Future Roadmap:** Once automated crowd-sourced citizen reports, NSDMA field inspection logs, and multi-year satellite temporal series are aggregated, this rule-based policy engine will serve as the ground-truth baseline against which supervised spatial ML models will be benchmarked.
