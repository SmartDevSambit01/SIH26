# Satellite Remote Sensing Data (`data/satellite/`)

## 1. Purpose
This directory stores satellite imagery and derived thematic products covering **Kohima District** and **Aizawl District**.

## 2. Expected Data & Products
1. **Optical Imagery (Multispectral)**:
   - Sources: Sentinel-2 (MSI), Landsat-8/9 (OLI/TIRS).
   - Derived Indices:
     - **NDVI (Normalized Difference Vegetation Index)**: For assessing vegetation cover health and deforestation.
     - **LULC (Land Use / Land Cover)**: Categorized land cover (forest, agricultural, urban/built-up, water bodies, barren land).
2. **Synthetic Aperture Radar (SAR)**:
   - Source: Sentinel-1 (C-band SAR, GRD).
   - Utility: All-weather, cloud-penetrating imagery useful during heavy monsoon cloud cover to detect surface changes and soil wetness proxies.

## 3. Storage Guidelines
- Files must be clipped to district bounding boxes to conserve storage.
- Raw scene archives should be logged with acquisition dates, cloud cover percentages, and sensor IDs.
- Never substitute synthetic images for missing satellite passes.
