# Terrain Data (`data/terrain/`)

## 1. Purpose
This directory contains digital elevation models (DEM) and primary morphometric derivatives covering **Kohima District** and **Aizawl District**. Terrain characteristics are the most critical static conditioning factors in landslide susceptibility modeling.

## 2. Expected Layers & Derived Rasters
All rasters should be clipped to the official district boundaries and projected to UTM Zone 46N (EPSG:32646):
- **DEM (Digital Elevation Model)**: Base elevation in meters above sea level (e.g., CartoDEM 30m, SRTM 30m, Copernicus DEM 30m).
- **Slope**: Slope angle in degrees (0° - 90°).
- **Aspect**: Slope orientation (compass direction 0° - 360°).
- **Curvature**: Planform curvature, profile curvature, and total curvature.
- **Topographic Wetness Index (TWI)**: Measure of hydrological accumulation potential.
- **Stream Network / Drainage**: Stream lines and distance-to-stream rasters.

## 3. Storage Format
- Format: GeoTIFF (`.tif`), single-band, floating point (Float32) or integer (Int16) with LZW or DEFLATE compression.
- Metadata: Accompanying `.json` or `.xml` describing pixel size, source DEM, and processing date.
