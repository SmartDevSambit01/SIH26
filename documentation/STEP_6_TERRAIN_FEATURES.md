# STEP 6 — Terrain Features

## 1. Overview

This step derives morphometric terrain conditioning factors from the **Copernicus DEM GLO-30** digital elevation model and maps them as zonal statistics to the 500 m NER Safe risk grid. Terrain characteristics are the most critical **static conditioning factors** in landslide susceptibility modelling — they describe the physical geometry of the land surface that predisposes slopes to failure.

> **Important scientific note**: Slope and other terrain variables are *conditioning/susceptibility features* that must be learned and calibrated together with rainfall, soil moisture, and other dynamic variables. We do **not** use standalone threshold rules such as "slope above X° means landslide."

---

## 2. Data Source

| Attribute | Value |
|-----------|-------|
| **Product** | Copernicus DEM GLO-30 |
| **Provider** | European Space Agency (ESA) / Airbus Defence and Space |
| **Access** | AWS Open Data Registry (`copernicus-dem-30m` S3 bucket) |
| **Spatial Resolution** | 30 m (1.0 arc-second) |
| **Horizontal CRS (native)** | EPSG:4326 (WGS 84) |
| **Vertical Datum** | EGM2008 (Earth Gravitational Model 2008) |
| **Analysis CRS** | EPSG:32646 (UTM Zone 46N) |
| **Analysis Resolution** | 30 m × 30 m (metric) |
| **Acquisition Date** | 2026-09-16 |
| **Total Tiles** | 8 (4 per district) |

### Raw Tiles Downloaded

**Kohima District (Nagaland):**
- `Copernicus_DSM_COG_10_N25_00_E093_00_DEM.tif`
- `Copernicus_DSM_COG_10_N25_00_E094_00_DEM.tif`
- `Copernicus_DSM_COG_10_N26_00_E093_00_DEM.tif`
- `Copernicus_DSM_COG_10_N26_00_E094_00_DEM.tif`

**Aizawl District (Mizoram):**
- `Copernicus_DSM_COG_10_N23_00_E092_00_DEM.tif`
- `Copernicus_DSM_COG_10_N23_00_E093_00_DEM.tif`
- `Copernicus_DSM_COG_10_N24_00_E092_00_DEM.tif`
- `Copernicus_DSM_COG_10_N24_00_E093_00_DEM.tif`

---

## 3. Processing Pipeline

### 3.1 DEM Download (`scripts/download_dem.py`)

Downloads 8 Copernicus DEM GLO-30 COG tiles from the AWS S3 public endpoint directly into `data/terrain/raw/`. Logs file sizes and generates `copernicus_dem_metadata.json`.

### 3.2 DEM Clipping (`scripts/clip_rasters.py`)

1. **Mosaic**: Merges 4 tiles per district using `rasterio.merge`.
2. **Reproject**: Transforms from EPSG:4326 to UTM Zone 46N (EPSG:32646) at 30 m resolution using bilinear resampling.
3. **Clip**: Masks precisely to official district boundaries (GeoJSON polygons) using `rasterio.mask`.
4. **Output**: DEFLATE-compressed Float32 GeoTIFFs with NoData = -9999.0.

Outputs:
- `data/terrain/kohima_dem.tif` — 1358 × 1878 pixels
- `data/terrain/aizawl_dem.tif` — 1343 × 2532 pixels

### 3.3 Morphometry Derivation (`scripts/derive_morphometry.py`)

Computes four terrain derivative layers per district using standard geomorphometric algorithms on the metric UTM 46N grid:

#### 3.3.1 Slope (Horn 1981)

The slope angle is computed using Horn's (1981) 3×3 finite-difference method:

$$\text{slope} = \arctan\left(\sqrt{p^2 + q^2}\right) \times \frac{180}{\pi}$$

where $p = \frac{\partial z}{\partial x}$ and $q = \frac{\partial z}{\partial y}$ are estimated using the 8-cell Horn kernel:

$$p = \frac{(z_3 + 2z_6 + z_9) - (z_1 + 2z_4 + z_7)}{8 \Delta x}$$

$$q = \frac{(z_7 + 2z_8 + z_9) - (z_1 + 2z_2 + z_3)}{8 \Delta y}$$

Units: degrees (0° – 90°).

#### 3.3.2 Aspect

Slope orientation computed from the same partial derivatives:

$$\text{aspect}_{\text{math}} = \arctan2(-q, p)$$

Converted from mathematical convention (east = 0°, counter-clockwise) to compass convention (north = 0°, clockwise):

$$\text{aspect} = (90° - \text{aspect}_{\text{math}}) \mod 360°$$

Flat pixels (slope < 0.001°) are assigned aspect = −1. Units: degrees (0° – 360°, or −1 for flat).

#### 3.3.3 Curvature (Zevenbergen & Thorne 1987)

Total (mean) curvature using the quadratic surface fit:

$$D = \frac{(z_W + z_E)/2 - z_C}{L^2}$$
$$E = \frac{(z_N + z_S)/2 - z_C}{L^2}$$
$$\text{curvature} = -2(D + E) \times 100$$

- Positive values → convex upward (ridge-like topography)
- Negative values → concave upward (valley-like topography)
- Units: 100 × m⁻¹

#### 3.3.4 Topographic Wetness Index (TWI)

Beven & Kirkby (1979):

$$\text{TWI} = \ln\left(\frac{a}{\tan \beta}\right)$$

where:
- $a$ = specific catchment area (m² per unit contour length), computed via D8 single-flow-direction accumulation
- $\beta$ = local slope angle (minimum 0.001 rad enforced to avoid division by zero)

Higher TWI values indicate areas of greater hydrological accumulation potential.

### 3.4 Zonal Statistics (`scripts/assign_grid_terrain.py`)

Maps 30 m raster values to each 500 m risk grid cell polygon:

| Feature | Aggregation | Description |
|---------|-------------|-------------|
| `elevation_mean` | Arithmetic mean | Mean elevation of 30 m pixels within cell |
| `elevation_min` | Minimum | Lowest elevation within cell |
| `elevation_max` | Maximum | Highest elevation within cell |
| `slope_mean` | Arithmetic mean | Mean slope angle |
| `slope_max` | Maximum | Steepest slope within cell |
| `aspect_mean` | Circular mean | atan2(Σ sin θ, Σ cos θ), handles 0°/360° boundary |
| `curvature_mean` | Arithmetic mean | Mean total curvature |
| `twi_mean` | Arithmetic mean | Mean wetness index |

> **Note on resolution**: 500 m grid features are representative *zonal statistics* of the underlying 30 m DEM. Each 500 m cell contains approximately 278 (≈ 500²/30²) underlying DEM pixels. This provides good statistical representation but does not constitute 500 m measurement resolution.

Output: `data/historical/grid_terrain_features.csv`

---

## 4. Results Summary

### 4.1 Kohima District (Nagaland)

| Metric | Value |
|--------|-------|
| DEM dimensions | 1358 × 1878 pixels |
| Valid pixels | 1,608,473 (63.1%) |
| Slope range | 0.05° – 70.84° (mean 22.18°) |
| Curvature range | −8.4567 – 7.3539 |
| TWI range | 2.47 – 17.52 (mean 5.86) |
| Processing time | ~30 s |

### 4.2 Aizawl District (Mizoram)

| Metric | Value |
|--------|-------|
| DEM dimensions | 1343 × 2532 pixels |
| Valid pixels | 2,173,145 (63.9%) |
| Slope range | 0.00° – 68.16° (mean 25.30°) |
| Curvature range | −9.7886 – 8.3813 |
| TWI range | 2.54 – 16.78 (mean 5.59) |
| Processing time | ~42 s |

### 4.3 Observations

- **Aizawl has steeper average terrain** (mean slope 25.3° vs 22.2°), consistent with the deeply dissected ridges of Mizoram.
- **TWI values** are comparable between districts (means ~5.6–5.9), indicating similar drainage density.
- **Curvature** distributions are symmetric around zero (means ≈ −0.0005), which is expected for a diverse landscape of ridges and valleys.
- All slope values fall within the valid 0°–90° range; no computational artefacts detected.

---

## 5. Output Files

### Rasters (`data/terrain/`)

| File | Description | Size |
|------|-------------|------|
| `kohima_dem.tif` | Clipped DEM | 5.7 MB |
| `kohima_slope.tif` | Slope (degrees) | 5.8 MB |
| `kohima_aspect.tif` | Aspect (degrees) | 5.9 MB |
| `kohima_curvature.tif` | Total curvature | 5.6 MB |
| `kohima_twi.tif` | Topographic Wetness Index | 5.7 MB |
| `aizawl_dem.tif` | Clipped DEM | 7.9 MB |
| `aizawl_slope.tif` | Slope (degrees) | 7.9 MB |
| `aizawl_aspect.tif` | Aspect (degrees) | 7.9 MB |
| `aizawl_curvature.tif` | Total curvature | 7.7 MB |
| `aizawl_twi.tif` | Topographic Wetness Index | 7.7 MB |

### Tabular Data (`data/historical/`)

| File | Description | Rows |
|------|-------------|------|
| `grid_terrain_features.csv` | Zonal statistics per 500 m grid cell | 16,961 |

---

## 6. Validation

Automated validation is run via `scripts/validate_terrain_data.py`, which checks:

1. **Raw tile existence** — all 8 Copernicus DEM tiles present
2. **Clipped DEM integrity** — CRS, dimensions, valid pixel count, elevation plausibility (0–4000 m), NoData < 15%
3. **Morphometric rasters** — existence, CRS, value range plausibility
4. **Grid CSV** — column completeness, row count (16,961), cell ID uniqueness, district coverage, numeric plausibility

---

## 7. Scripts Reference

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `scripts/download_dem.py` | Download Copernicus DEM tiles | AWS S3 | `data/terrain/raw/*.tif` |
| `scripts/clip_rasters.py` | Mosaic, reproject, clip DEM | Raw tiles + boundaries | `data/terrain/{district}_dem.tif` |
| `scripts/derive_morphometry.py` | Compute slope, aspect, curvature, TWI | Clipped DEMs | `data/terrain/{district}_{layer}.tif` |
| `scripts/assign_grid_terrain.py` | Zonal stats to 500 m grid | Rasters + grid GeoJSON | `data/historical/grid_terrain_features.csv` |
| `scripts/validate_terrain_data.py` | Automated validation suite | All terrain outputs | Console report (exit 0/1) |

---

## 8. Limitations & Constraints

1. **Copernicus DEM GLO-30** represents a static snapshot of terrain and does not capture post-event topographic changes from landslides.
2. **TWI estimation** uses D8 (single-flow-direction) accumulation, which is adequate for regional assessment but may underestimate convergent flow in complex terrain compared to D-infinity methods.
3. **500 m zonal aggregation** inherently smooths the 30 m terrain signal. Pixel-level variability within cells is captured via min/max statistics but sub-pixel features are not resolved.
4. **Vertical accuracy** of Copernicus DEM is typically LE90 < 4 m on slopes < 20° and degrades on steeper slopes and under dense vegetation cover (relevant for both NE India districts).

---

## 9. References

- Beven, K.J. & Kirkby, M.J. (1979). A physically based, variable contributing area model of basin hydrology. *Hydrological Sciences Bulletin*, 24, 43–69.
- Horn, B.K.P. (1981). Hill shading and the reflectance map. *Proceedings of the IEEE*, 69(1), 14–47.
- Zevenbergen, L.W. & Thorne, C.R. (1987). Quantitative analysis of land surface topography. *Earth Surface Processes and Landforms*, 12, 47–56.
- ESA (2023). Copernicus DEM – Global and European Digital Elevation Model. Product Handbook.
