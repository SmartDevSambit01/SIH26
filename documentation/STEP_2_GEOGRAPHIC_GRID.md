# Step 2: Geographic Foundation & Analysis Grid

> **Project:** NER Safe (SIH 2026)  
> **Pilot Focus:** Kohima District (Nagaland) & Aizawl District (Mizoram)  
> **Status:** Completed & Validated

---

## 1. Boundary Data Provenance

The geographic administrative boundaries for both pilot districts were acquired from open, authoritative administrative records:

- **Source Registry:** Local Government Directory (LGD), Ministry of Panchayati Raj, Government of India, integrated via the **geoBoundaries gbOpen ADM2 India dataset** (Release `v9469f09`).
- **License:** Open Data Commons Open Database License (ODbL) 1.0.
- **Verification:** Boundaries and computed spatial areas were verified against official Census of India and State Disaster Management Authority (NSDMA & MSDMA) published district profiles.
- **Original Source Files:** Stored in `data/boundaries/raw/geoBoundaries-IND-ADM2.geojson`.
- **Processed Files:**
  - `data/boundaries/kohima_district.geojson`
  - `data/boundaries/aizawl_district.geojson`
  - `data/boundaries/pilot_districts.geojson` (combined collection)

---

## 2. Coordinate Reference Systems (CRS)

To ensure spatial metric accuracy while retaining web-mapping compatibility:

1. **Storage & Web Mapping Standard (WGS 84 / EPSG:4326)**:
   - All exported GeoJSON files (boundaries and analysis grids) are encoded in standard WGS 84 (EPSG:4326) with 6 decimal places of precision (~0.1m precision).
   - This ensures direct compatibility with MapLibre GL JS, Leaflet, and standard web mapping libraries.
2. **Projected Metric Standard (UTM Zone 46N / EPSG:32646)**:
   - Northeast India (including Nagaland and Mizoram between 92°E and 95°E) lies within UTM Zone 46N.
   - All metric operations—including the 500m grid cell geometry generation, area calculation, and boundary clipping—were executed in UTM Zone 46N before reprojecting back to WGS 84.

---

## 3. District Metrics & Spatial Extents

| Metric | Kohima District (Nagaland) | Aizawl District (Mizoram) |
| :--- | :--- | :--- |
| **State** | Nagaland (`IN-NL`) | Mizoram (`IN-MZ`) |
| **Geometry Type** | Valid `Polygon` (0 self-intersections) | Valid `Polygon` (0 self-intersections) |
| **Calculated Area** | **1,447.61 km²** | **2,612.52 km²** |
| **Perimeter Length**| 218.74 km | 373.01 km |
| **Centroid (Lat, Lon)** | `(25.773910°N, 94.106928°E)` | `(23.801188°N, 92.845192°E)` |
| **Bounding Box (WGS84)**| `[93.89129, 25.51901, 94.29940, 26.02657]` | `[92.60465, 23.31733, 93.04286, 24.41030]` |

---

## 4. 500-Meter Geographic Analysis Grid

A regular 500m × 500m cell grid was constructed over each district's bounding envelope in UTM Zone 46N, clipped to the official polygon boundary, and exported to GeoJSON format:

- `data/boundaries/kohima_grid_500m.geojson`
- `data/boundaries/aizawl_grid_500m.geojson`

### Cell Counts & Coverage

| Attribute | Kohima District | Aizawl District | Total Pilot System |
| :--- | :--- | :--- | :--- |
| **Grid Cell Resolution** | 500 m × 500 m (0.25 km²) | 500 m × 500 m (0.25 km²) | 500 m × 500 m |
| **Total Analysis Cells** | **6,055** | **10,906** | **16,961** |
| **Interior Full Cells** | 5,525 (91.2%) | 9,993 (91.6%) | 15,518 (91.5%) |
| **Clipped Border Cells** | 530 (8.8%) | 913 (8.4%) | 1,443 (8.5%) |
| **Candidate Matrix Size** | 82 cols × 113 rows (9,266) | 90 cols × 242 rows (21,780) | 31,046 candidate cells |
| **File Size (GeoJSON)** | 2.85 MB | 5.01 MB | 7.86 MB |

### Feature Properties Schema

Each grid cell feature in the GeoJSON contains the following properties:

```json
{
  "cell_id": "KOH_00001",
  "district": "Kohima",
  "state": "Nagaland",
  "centroid_lat": 25.521251,
  "centroid_lon": 94.108422,
  "area_sqm": 250000.0,
  "grid_size_m": 500.0
}
```

- `cell_id`: Unique alphanumeric key (`KOH_XXXXX` or `AIZ_XXXXX`).
- `district`: Name of district (`Kohima` or `Aizawl`).
- `state`: Name of state (`Nagaland` or `Mizoram`).
- `centroid_lat` / `centroid_lon`: Cell centroid coordinates in decimal degrees (WGS84).
- `area_sqm`: Exact surface area in square meters (250,000 m² for full cells, less for boundary-clipped cells).
- `geometry`: Polygon or MultiPolygon clipped strictly to the district border.

---

## 5. Automated Validation Results

All generated files were tested using `scripts/validate_geographic_data.py`:
- [x] **File Existence**: Both district boundaries and both 500m grid files exist.
- [x] **Geometry Validity**: 100% of geometries are valid (0 self-intersections or bowtie loops).
- [x] **ID Uniqueness**: 0 duplicate `cell_id` values across all 16,961 cells.
- [x] **Boundary Containment**: 100% of generated grid cells intersect and lie strictly within the district boundary. Cells completely outside were discarded during generation.
- [x] **Property Integrity**: Every feature contains `cell_id`, `district`, `centroid_lat`, `centroid_lon`, `area_sqm`, and `grid_size_m`.

---

## 6. Assumptions and Limitations

1. **District Reorganizations**:
   - In recent years, Nagaland and Mizoram have reorganized some district subdivisions (e.g., carving out Tseminyu from Kohima in late 2021, and Saitual / Hnahthial from Aizawl/Champhai/Lunglei).
   - The boundary datasets used here represent the post-reorganization boundaries as catalogued in the official Local Government Directory (LGD), resulting in 1,447.61 km² for Kohima and 2,612.52 km² for Aizawl.
2. **Planar Projection Approximation**:
   - The 500m grid was constructed using planar Euclidean projection in UTM Zone 46N (EPSG:32646). While UTM 46N is standard for the region and maintains sub-meter scale distortion at central meridians, true geodesic distances on extreme slopes can show slight variations. This is standard practice in regional landslide susceptibility modeling.
3. **500-Meter Spatial Granularity**:
   - A 500m cell size provides an optimal balance for the first prototype: fine enough to capture hillslopes and drainage sub-catchments, yet light enough (~17,000 total cells) to allow instant spatial lookups and browser rendering without tile server bottlenecks.
