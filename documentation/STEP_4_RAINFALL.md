# Step 4: Historical Rainfall Feature Extraction

> **Project:** NER Safe (SIH 2026)  
> **Pilot Focus:** Kohima District (Nagaland) & Aizawl District (Mizoram)  
> **Primary Sensor:** NASA Global Precipitation Measurement (GPM) IMERG  
> **Status:** Extraction Pipeline Implemented & Validated; Data Transparency Enforced

---

## 1. NASA GPM IMERG Product Specifications

The historical rainfall processing pipeline is built exclusively around the authoritative NASA Global Precipitation Measurement (GPM) satellite mission dataset:

- **Official Product:** **GPM_3IMERGHH** (Integrated Multi-satellitE Retrievals for GPM, Version 07B / Final & Late Runs).
- **Hosting Facility:** NASA Goddard Earth Sciences Data and Information Services Center (GES DISC) / Earthdata Cloud.
- **Spatial Resolution:** **0.1° × 0.1°** (approximately **10 km × 10 km** at equatorial to temperate latitudes).
- **Temporal Resolution:** **30 minutes (Half-Hourly)**.
- **Measurement Units:** Precipitation calibrated rate in millimeters per hour (`mm/hr`) and half-hourly accumulation (`mm`).
- **Data Latency Profiles:**
  - *Early Run:* ~4 hours latency (multi-satellite passive microwave + calibrated IR; useful for real-time alerts).
  - *Late Run:* ~14 hours latency (includes forward/backward morphing; balanced for monitoring).
  - *Final Run:* ~3.5 to 4 months latency (calibrated with GPCC monthly ground rain-gauge analysis; standard research baseline for historical analysis).

---

## 2. Spatial Scale Notice: 10 km vs. 500 m Resolution

> [!IMPORTANT]
> **Spatial Scale Disparity Notice:**  
> Satellite-derived GPM IMERG rainfall has an intrinsic native grid resolution of **~10 km (0.1°)**.  
> Our terrain landslide risk grid is partitioned into **500 m cells**.  
> **We do NOT claim 500-meter rainfall precision.** A single 10 km × 10 km GPM satellite pixel covers approximately 400 terrain grid cells ($20 \times 20$ cells). In our architecture, the satellite rainfall grid cell serves as a regional macro-meteorological trigger overlaying high-resolution static terrain conditioning factors (slope, aspect, curvature).

### GPM Grid Cell Mapping for Pilot Landslides

| District | Verified Event | Matched 500m Grid Cell | Matched 0.1° GPM Grid Cell (~10 km) | Center Coordinates |
| :--- | :--- | :--- | :--- | :--- |
| **Kohima** | Dzudza Bridge (NH-29) | `KOH_01378` | `GPM_0.1DEG_N25.65_E094.05` | 25.65°N, 94.05°E |
| **Kohima** | Kisama Village Road | `KOH_03175` | `GPM_0.1DEG_N25.65_E094.15` | 25.65°N, 94.15°E |
| **Kohima** | Phesama (NH-29 South) | `KOH_03071` | `GPM_0.1DEG_N25.65_E094.15` | 25.65°N, 94.15°E |
| **Kohima** | Sechu Zubza Slope | `KOH_01187` | `GPM_0.1DEG_N25.75_E094.05` | 25.75°N, 94.05°E |
| **Kohima** | Tarliedzu Area | `KOH_02654` | `GPM_0.1DEG_N25.65_E094.05` | 25.65°N, 94.05°E |
| **Aizawl** | Melthum Stone Quarry | `AIZ_01960` | `GPM_0.1DEG_N23.65_E092.75` | 23.65°N, 92.75°E |
| **Aizawl** | Hlimen Veng Ridge | `AIZ_02185` | `GPM_0.1DEG_N23.65_E092.75` | 23.65°N, 92.75°E |
| **Aizawl** | Durtlang Hills Highway | `AIZ_02321` | `GPM_0.1DEG_N23.75_E092.75` | 23.75°N, 92.75°E |
| **Aizawl** | Sihphir Approach Road | `AIZ_02559` | `GPM_0.1DEG_N23.85_E092.75` | 23.85°N, 92.75°E |
| **Aizawl** | Ramhlun Vengthlang | `AIZ_02314` | `GPM_0.1DEG_N23.75_E092.75` | 23.75°N, 92.75°E |
| **Aizawl** | Bawngkawn Chhimveng | `AIZ_02431` | `GPM_0.1DEG_N23.75_E092.75` | 23.75°N, 92.75°E |

---

## 3. Extraction Methodology & Accumulation Math

Rainfall metrics around each verified event timestamp ($t_0$) are structured into multi-scale temporal windows:

1. **Immediate 30-Minute Accumulation (`rainfall_30min`)**:
   $$R_{\text{30min}} = P(t_0) \times 0.5 \text{ hours}$$
   where $P(t_0)$ is the calibrated precipitation rate in mm/hr from the single half-hour GPM granule containing $t_0$.

2. **3-Hour Accumulation (`rainfall_3h`)**:
   $$R_{\text{3h}} = \sum_{i=0}^{5} R_{\text{30min}}(t_0 - i \cdot 30\text{min})$$
   Sum of the 6 half-hourly intervals preceding and including the event time.

3. **6-Hour Accumulation (`rainfall_6h`)**:
   $$R_{\text{6h}} = \sum_{i=0}^{11} R_{\text{30min}}(t_0 - i \cdot 30\text{min})$$
   Sum of the 12 half-hourly intervals up to event time.

4. **24-Hour Accumulation (`rainfall_24h`)**:
   $$R_{\text{24h}} = \sum_{i=0}^{47} R_{\text{30min}}(t_0 - i \cdot 30\text{min})$$
   Cumulative daily precipitation triggering slope failure.

5. **72-Hour Accumulation (`rainfall_72h`)**:
   $$R_{\text{72h}} = \sum_{i=0}^{143} R_{\text{30min}}(t_0 - i \cdot 30\text{min})$$
   Cumulative 3-day precipitation index.

6. **Rainfall Intensity (`rainfall_intensity`)**:
   $$I = \frac{R_{\text{30min}}}{0.5} \text{ mm/hr}$$

7. **Antecedent Rainfall (`antecedent_rainfall`)**:
   $$R_{\text{antecedent}} = R_{\text{72h}} - R_{\text{24h}}$$
   Precipitation accumulated during the 48-hour window prior to the final 24-hour event period, representing pre-saturation of the soil mantle.

---

## 4. Anti-Fabrication & Data Availability Status

In strict accordance with project rules, **no synthetic, simulated, or interpolated precipitation values were created**.

### Status Breakdown

| Category | Count | Status Code | Explanation |
| :--- | :--- | :--- | :--- |
| **Total Events Processed** | 19 | — | All curated events from Step 3. |
| **Verified Coordinates** | 11 | `UNAVAILABLE_EARTHDATA_AUTH_REQUIRED` | Exact coordinates and GPM grid cells identified; awaiting Earthdata Login token / local HDF5 granules. Values populated as `NaN`. |
| **Unverified Coordinates** | 4 | `SKIPPED_UNVERIFIED_COORDINATES` | Approximate locality centroids; skipped to prevent false spatial associations. |
| **Missing Coordinates** | 4 | `SKIPPED_MISSING_COORDINATES` | No coordinates recorded; rainfall extraction omitted. |
| **Successfully Matched (Real Data)** | 0 | — | No offline granules or Earthdata credentials configured locally. |

### How to Authenticate & Download Live GPM IMERG Data

To pull live numeric observations into `data/historical/landslide_rainfall_features.csv`:
1. Register a free account at [NASA Earthdata](https://urs.earthdata.nasa.gov/).
2. Create `~/.netrc` with:
   ```text
   machine urs.earthdata.nasa.gov login <YOUR_USERNAME> password <YOUR_PASSWORD>
   ```
   Or set the environment variable `EARTHDATA_TOKEN=<YOUR_TOKEN>`.
3. Re-run:
   ```bash
   python scripts/extract_historical_rainfall.py
   ```

---

## 5. Automated Validation Results

The pipeline script [`scripts/extract_historical_rainfall.py`](file:///c:/Users/sambi/Downloads/SIH%2026/scripts/extract_historical_rainfall.py) executed automated validation checks:
- [x] **Non-Negative Values:** Verified that no negative precipitation values exist.
- [x] **Coordinate Range:** Verified latitude ($22^\circ\text{N} - 28^\circ\text{N}$) and longitude ($91^\circ\text{E} - 96^\circ\text{E}$) bounds.
- [x] **Timestamp Validity:** Verified standard ISO format and chronological validity.
- [x] **Data Source Recorded:** Verified that `rainfall_source` is explicitly logged for 100% of rows.
- [x] **ID Uniqueness:** 0 duplicate event IDs detected.

---

## 6. Limitations of Satellite Precipitation in Northeast India

1. **Coarse Spatial Footprint (10 km)**:
   - Steep mountain ridges in Kohima and Aizawl create extreme microclimates and localized rain-shadow effects within distances of 1 to 2 km. A 10 km satellite average can underestimate localized cloudbursts.
2. **Orographic Cloud Water Attenuation**:
   - Passive microwave sensors can experience attenuation over rugged topography, occasionally underestimating intense warm-rain orographic clouds common in the Northeast during monsoon peaks.
3. **Temporal Infilling**:
   - Between microwave satellite passes, IMERG uses infrared (IR) cloud-top temperature morphing, which can introduce variance in short 30-minute accumulations.
