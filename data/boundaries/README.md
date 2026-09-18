# Administrative Boundaries (`data/boundaries/`)

## 1. Purpose
This directory contains vector boundary layers defining the geographic extent of **Kohima District (Nagaland)** and **Aizawl District (Mizoram)**, along with key administrative and infrastructure sub-layers.

## 2. Expected Files
- `kohima_district.geojson`: Official district boundary polygon for Kohima.
- `aizawl_district.geojson`: Official district boundary polygon for Aizawl.
- `subdivisions/`: Sub-divisional, block, and municipal ward boundaries.
- `infrastructure/`: Major highways (NH-2, NH-29, NH-54, etc.), secondary roads, and settlements.

## 3. Format & Standards
- Standard CRS: EPSG:4326 (WGS 84 Latitude/Longitude).
- Encoding: UTF-8.
- Validation: All polygons must be topologically valid (no self-intersections or unclosed rings) so that PostGIS functions (`ST_Contains`, `ST_Intersects`) execute without errors.

## 4. Sources
- Survey of India / Census of India.
- OpenStreetMap (for road corridors and settlement nodes).
- Bhuvan (ISRO) administrative boundary layers.
