# STEP 5: NASA SMAP Soil Moisture Ingestion & Feature Engineering

**NER Safe (SIH 2026) — AI-Based Early Warning and Landslide Risk Monitoring System**  
**Pilot Focus:** Kohima District (Nagaland) & Aizawl District (Mizoram)  
**Status:** Step 5 Completed — Ingestion Pipeline, Historical Extraction & Schema Validation Verified  

---

## 1. What is NASA SMAP?

The **Soil Moisture Active Passive (SMAP)** mission is an Earth-observing satellite observatory launched by the **National Aeronautics and Space Administration (NASA)** in January 2015. 

SMAP carries an advanced, highly sensitive **L-band passive microwave radiometer** operating at $1.41\text{ GHz}$. This sensor measures natural microwave thermal emissions radiating from the Earth's surface. Because water has an extraordinarily high dielectric constant (~80) compared to dry mineral soil (~3 to 5), the microwave brightness temperature observed by the radiometer directly correlates to the volumetric water content present within the upper surface soil layer.

---

## 2. Why Soil Moisture Matters for Landslide Risk

Rainfall alone does not trigger a slope failure; it is the **water retained inside the soil matrix** that destabilizes hillslopes.

1. **Pore-Water Pressure Accumulation:**  
   When dry soil absorbs rainwater, the air between soil particles is replaced by water. As saturation approaches 100%, positive pore-water pressure builds up. This pressure pushes soil grains apart, dramatically reducing the internal friction and effective normal stress ($\sigma' = \sigma - u$) that holds hillsides together (Coulomb-Terzaghi failure criterion).
2. **Antecedent Watershed Pre-Conditioning:**  
   A cloudburst of $50\text{ mm}$ over parched, unsaturated terrain may be absorbed harmlessly. The identical $50\text{ mm}$ cloudburst occurring over soil already at 90% saturation will produce catastrophic surface runoff, rapid liquefaction, and destructive translational debris flows.
3. **Early Warning Lead Time:**  
   Soil moisture acts as a **slow-moving memory state** of the watershed. By tracking how saturated the ground is before storm systems arrive, disaster authorities gain vital hours or days of situational awareness.

---

## 3. Product Selected & Official Specifications

NER Safe uses the official, peer-reviewed Level 3 enhanced radiometer data product:

| Parameter | Product Specification |
| :--- | :--- |
| **Official Title** | SMAP Enhanced L3 Radiometer Global Daily 9 km EASE-Grid Soil Moisture |
| **Product Short Name** | `SPL3SMP_E` |
| **Version** | Version 6 (`006`) |
| **Archive Host** | NASA National Snow and Ice Data Center DAAC (NSIDC DAAC) / Earthdata Cloud |
| **Digital Object Identifier (DOI)** | [10.5067/M20OXIZHY3RJ](https://doi.org/10.5067/M20OXIZHY3RJ) |
| **Native Spatial Grid** | **EASE-Grid 2.0 Global Cylindrical** (EPSG:6933, $9008.0556\text{ m} \times 9008.0556\text{ m}$) |
| **Native Spatial Resolution** | **Approximately 9 km** |
| **Temporal Frequency** | **Daily global composite** |
| **Preferred Orbit Pass** | **Descending morning pass (~06:00 local solar time)**, where thermal equilibrium between the canopy and topsoil layer minimizes retrieval error. |
| **Scientific Measurement Unit** | **Volumetric soil water content in $\text{m}^3/\text{m}^3$** (cubic meters of water per cubic meter of soil). |
| **Valid Physical Bounds** | $0.02\text{ to }0.60\ \text{m}^3/\text{m}^3$ (Fill value: $-9999.0$) |

---

## 4. Native Spatial Resolution & The 500 m Analysis Grid

> [!IMPORTANT]
> **500m is the project analysis/display grid; it is not the native spatial resolution of SMAP.**  
> Native SMAP soil moisture has an intrinsic spatial footprint of **~9 km**. Our terrain risk grid operates at **500 m resolution**.  
> We do **NOT** claim 500-meter soil moisture measurements. A single 9 km × 9 km SMAP grid cell covers approximately **324 analysis cells** ($18 \times 18$ grid). SMAP serves as an antecedent regional saturation index across the watershed, not as an individual hillslope piezometer.

```
+-------------------------------------------------------------------------------+
| SMAP Enhanced L3 Radiometer Pixel: ~9 km x 9 km (EASE-Grid 2.0)               |
| Covers ~324 project analysis cells (18 x 18 grid)                              |
|                                                                               |
|   +---------------------------------------+                                   |
|   | NER Safe Analysis Grid Cell: 500m x 500m  |                                   |
|   | (Administrative & Display Unit)       |                                   |
|   +---------------------------------------+                                   |
+-------------------------------------------------------------------------------+
```

---

## 5. Temporal Resolution: What "Latest Available" Means

- **Daily Composite:** SMAP passes over any given point on Earth approximately once every 24 to 72 hours depending on orbit overlap.
- **Why It Is NOT Continuous Real-Time:**  
  SMAP is a polar-orbiting satellite, **not a continuous live ground sensor or live video stream**. Radiometer passes are processed and published to NASA DAAC archives with typical latencies of **12 to 24 hours**.
- **Accurate Terminology:**  
  The system strictly labels SMAP readings as **"Latest available satellite soil moisture"** or **"Satellite soil moisture observation"**. We never mislead disaster managers by calling it "real-time".

---

## 6. NASA Earthdata Authentication Architecture

Access to NASA NSIDC DAAC and Earthdata Cloud data products requires authenticated User Registration System (URS) credentials.

### High-Level Authentication Mechanism:
1. When the ingestion script executes, it inspects the environment for secure access tokens or credentials.
2. If credentials exist, an HTTPS request with Bearer authorization is dispatched to NASA's URS server (`urs.earthdata.nasa.gov`), obtaining a session cookie.
3. The authenticated stream downloads the Level 3 HDF5 granule (`SMAP_L3_SM_P_E_*.h5`).

### Credential Configuration (Zero Hardcoding):
Credentials are **never** placed into code or committed to Git. They are securely supplied via environment variables:
```bash
# Option A: User & Password
export NASA_EARTHDATA_USERNAME="your_username"
export NASA_EARTHDATA_PASSWORD="your_password"

# Option B: Bearer Token
export EARTHDATA_TOKEN="your_personal_access_token"

# Option C: ~/.netrc configuration file
# machine urs.earthdata.nasa.gov login <USER> password <PASS>
```

### Controlled Safe State When Credentials Are Missing:
If credentials are not yet configured on a deployment machine:
- The pipeline **does not crash**.
- The pipeline **never invents fake soil-moisture values**.
- The pipeline outputs standardized records where soil moisture numbers are empty (`""`), `data_status = 'REQUIRES_EXTERNAL_AUTH'`, and `quality_flag = 'UNAVAILABLE_PENDING_EARTHDATA_LOGIN'`.
- This constitutes a **successful and transparent pipeline state**.

---

## 7. Deterministic Spatial Mapping to the 500 m Grid

All 16,961 analysis cells across Kohima and Aizawl are mapped to SMAP EASE-Grid 2.0 cells using exact geographic reprojection:

1. **Reprojection Formula:**  
   Centroid coordinates $(\lambda, \phi)$ in WGS 84 (EPSG:4326) are projected to EASE-Grid 2.0 Global Cylindrical (EPSG:6933) using `pyproj`:
   $$\text{col} = \left\lfloor \frac{x - x_{\min}}{9008.0556} \right\rfloor, \quad \text{row} = \left\lfloor \frac{y_{\max} - y}{9008.0556} \right\rfloor$$
   where $x_{\min} = -17,367,530.44\text{ m}$ and $y_{\max} = 7,314,540.83\text{ m}$.
2. **Identifier Generation:**  
   The resulting integer indices form the unique SMAP cell key: `EASE2_M09_R{row:04d}_C{col:04d}`.
3. **Macro-Coverage:**  
   The 16,961 analysis cells map to **61 distinct 9 km EASE-Grid 2.0 pixels** covering Kohima and Aizawl.

---

## 8. Quality Control & Filtering

Raw radiometer measurements are screened using the official Level 3 retrieval quality dataset:
- **Quality Bitmask (`retrieval_qual_flag`):**  
  Only pixels with Bit 0 = 0 (Retrieval Recommended) are accepted as `AVAILABLE`.
- **Physical Sanity Bounds:**  
  $0.02\text{ m}^3/\text{m}^3 \le \theta \le 0.60\text{ m}^3/\text{m}^3$. Any negative values (fill values: $-9999$) or physically impossible values ($>0.60$) are rejected.
- **Surface Condition Exclusion:**  
  Observations flagged for active heavy precipitation, standing open water, or radio frequency interference (RFI) are marked `QUALITY_REJECTED`.

---

## 9. Calculation of Moisture Metrics (Current, Previous, Change)

When valid observations exist for an analysis cell:

1. **Current Moisture ($\theta_{\text{current}}$):**  
   Volumetric water content ($\text{m}^3/\text{m}^3$) on observation date $t$.
2. **Previous Moisture ($\theta_{\text{previous}}$):**  
   Most recent valid antecedent daily observation for the exact same EASE-Grid cell ($t - 1\text{ to }t - 3\text{ days}$).
3. **Absolute Change ($\Delta \theta$):**  
   $$\Delta \theta = \theta_{\text{current}} - \theta_{\text{previous}} \quad [\text{m}^3/\text{m}^3]$$
4. **Percentage Change ($\Delta \theta_{\%}$):**  
   $$\Delta \theta_{\%} = \left( \frac{\theta_{\text{current}} - \theta_{\text{previous}}}{\theta_{\text{previous}}} \right) \times 100 \quad [\%]$$
   *Safe Division Guard:* If $\theta_{\text{previous}} \le 0$ or either value is unavailable, the percentage is safely set to null/empty without raising a divide-by-zero error.

---

## 10. Low-Bandwidth & Offline Architecture

- **ONLINE:** The system requests the latest daily SMAP composite when published by NSIDC DAAC.
- **LIMITED BANDWIDTH:** The server distributes compact tabular deltas ($\Delta \theta$ per 9 km macro pixel) rather than multi-gigabyte HDF5 files.
- **OFFLINE OPERATION:**  
  When internet connectivity is lost during monsoonal disruptions:
  - The client application displays the previously cached soil-moisture snapshot.
  - The UI presents a prominent warning banner:
    ```
    [OFFLINE] Showing last available satellite soil moisture from: 2024-08-18 (Sync Age: 28 hours)
    ```
  - If cached data is older than 72 hours, `data_status` transitions to `STALE`.
  - Cached data is **never** labeled as current or real-time.

---

## 11. Known Scientific Limitations in Northeast India

1. **Shallow Sensing Depth (~5 cm):**  
   L-band radiometers penetrate only the top 0 to 5 cm of the soil. Deep-seated rotational landslides (failing at depths of 2 to 15 m) are influenced by deep groundwater tables that satellite radiometers cannot directly measure.
2. **Dense Canopy Attenuation:**  
   Northeast India's dense semi-evergreen subtropical forests and bamboo canopies scatter and attenuate microwave radiation, increasing retrieval uncertainty.
3. **Steep Topographic Distortion:**  
   Rugged topography creates geometric shadows and slopes facing toward or away from the antenna, requiring careful calibration during multi-hazard modeling.

---

## 12. Pre-Deployment Checklist Before Production

- [ ] Register institutional NASA Earthdata account for automated server-to-server daemon syncing.
- [ ] Configure `NASA_EARTHDATA_USERNAME` and `NASA_EARTHDATA_PASSWORD` on production server.
- [ ] Establish daily automated cron schedule (`0 8 * * *`) to fetch descending orbit granules following morning pass release.
- [ ] Integrate local IMD / AWS rain-gauge calibration to ground-truth satellite surface saturation against local soil texture.

---

## 13. Pipeline Verification Results

1. **Latest SMAP Ingestion Script:** [`scripts/ingest_smap_soil_moisture.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/ingest_smap_soil_moisture.py)
2. **Historical SMAP Extraction Script:** [`scripts/extract_historical_smap.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/extract_historical_smap.py)
3. **Validation Suite:** [`scripts/validate_smap_soil_moisture.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/validate_smap_soil_moisture.py)
4. **Validation Outcome:** **14/14 checks PASSED**.
   - 16,961 cells completely mapped.
   - Zero fake soil moisture numbers generated.
   - Core datasets intact and unmodified.

---
*Generated: STEP 5 — NER Safe SIH 2026 Project*  
*NASA SMAP Soil Moisture Ingestion Pipeline*
