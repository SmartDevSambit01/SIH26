# NER Safe (SIH 2026)
> **AI-Powered Early Warning & Landslide Risk Monitoring System for the North Eastern Region**

---

## 1. Project Overview

**NER Safe** is an early warning and landslide risk monitoring platform designed specifically for the fragile and landslide-prone topography of Northeast India. 

The primary objective is to assist local disaster management authorities, district administrations, and citizens by providing:
- Pre-disaster susceptibility assessments and early warnings.
- Real-time / dynamic rainfall-triggered hazard alerts.
- Post-disaster incident reporting and quick access to emergency resources.

---

## 2. Pilot Scope (Working Prototype)

To maintain technical depth, data fidelity, and high reliability, the first working prototype focuses strictly on **two pilot districts**:

1. **Kohima District**, Nagaland
2. **Aizawl District**, Mizoram

Both districts present steep terrain, heavy seasonal monsoonal precipitation, high urbanization on hill slopes, and well-documented historical landslide occurrences.

---

## 3. Engineering & Architectural Principles

1. **Simple, Maintainable Monolith**: 
   - No distributed microservices or unnecessary complexity.
   - Clean, modular separation between frontend, backend, and ML components.
2. **Data Integrity & Truthfulness**:
   - Zero tolerance for fabricated datasets, hallucinated predictions, mock satellite feeds, or fake accuracy figures.
   - All spatial layers and risk models must be tied to verifiable data sources (e.g., GSI, IMD, CartoDEM/SRTM).
3. **Graceful Handling of Missing Data**:
   - If a live sensor, weather feed, or satellite coverage is unavailable, the system explicitly returns `UNAVAILABLE` rather than generating artificial placeholders.

---

## 4. Technology Stack

- **Frontend**: React (Vite), Tailwind CSS, MapLibre GL JS
- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Database**: PostgreSQL with PostGIS extension (for spatial queries and geometry storage)
- **Machine Learning**: Python, scikit-learn, XGBoost
- **Geospatial & Data Processing**: GDAL, Rasterio, GeoPandas, Shapely, Pandas, NumPy

---

## 5. Repository Structure

```text
SIH 26/
├── DESIGN.md                 # Landing page visual specification (DO NOT MODIFY)
├── README.md                 # Project root documentation (this file)
├── frontend/                 # React + Vite web dashboard and citizen portal
├── backend/                  # FastAPI REST API and PostGIS database services
├── ml/                       # Landslide susceptibility and risk scoring models
├── data/                     # Geospatial, environmental, and historical datasets
│   ├── historical/           # Past landslide inventory records
│   ├── rainfall/             # Gridded/station rainfall data
│   ├── soil_moisture/        # Satellite / sensor soil wetness data
│   ├── terrain/              # DEM, slope, aspect, curvature rasters
│   ├── satellite/            # Optical and SAR remote sensing products
│   └── boundaries/           # Administrative shapefiles / GeoJSON for Kohima & Aizawl
├── scripts/                  # Data ingestion, clipping, and preprocessing utilities
└── documentation/            # Architectural guides, API specs, and data registries
```

---

## 6. District Profiles

| Parameter | Kohima District | Aizawl District |
| :--- | :--- | :--- |
| **State** | Nagaland | Mizoram |
| **Terrain** | High-relief hills, fragile shale/sandstone | Steep ridge-and-valley topography |
| **Primary Trigger** | Heavy monsoon rainfall & toe-cutting | Prolonged monsoonal rain & slope cutting |
| **Key Authority** | NSDMA (Nagaland State DMA) | MSDMA (Mizoram State DMA) |
