# Soil Moisture Data (`data/soil_moisture/`)

## 1. Purpose
This directory holds soil moisture and saturation datasets for **Kohima District** and **Aizawl District**. Soil moisture acts as a key pre-conditioning factor that dictates whether rainfall will lead to slope instability.

## 2. Expected Data Sources
- **Satellite Remote Sensing**:
  - NASA SMAP (Soil Moisture Active Passive) L3/L4 products.
  - ESA CCI (Climate Change Initiative) Soil Moisture.
  - Copernicus Climate Change Service (C3S) soil moisture products.
- **In-Situ Sensors**:
  - Soil moisture telemetry stations if deployed by state agricultural or disaster departments.

## 3. Important Notes on Spatial Resolution
- Satellite soil moisture typically has coarse resolution (~9 km to ~36 km).
- Any downscaling methods applied must be documented transparently.
- If high-resolution soil moisture is unavailable, the modeling pipeline will clearly treat soil saturation as an optional layer or report it as unavailable rather than fabricating fine-grained values.
