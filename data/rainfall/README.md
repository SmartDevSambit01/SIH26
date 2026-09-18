# Rainfall Data (`data/rainfall/`)

## 1. Purpose
This folder contains rainfall datasets used to calculate dynamic triggers and early warning alert levels for **Kohima District** and **Aizawl District**.

## 2. Types of Rainfall Data
1. **Historical Gridded Rainfall**:
   - Used for establishing local rainfall intensity-duration (I-D) thresholds and antecedent rainfall indices.
   - Sources: India Meteorological Department (IMD) 0.25° x 0.25° daily gridded rainfall product or NASA GPM IMERG data.
2. **Station Observations / Automatic Weather Stations (AWS)**:
   - Data from IMD or state disaster management weather stations located in Kohima and Aizawl.
3. **Near Real-Time Rainfall (Operational Pipeline)**:
   - Feeds for ongoing daily/hourly precipitation monitoring.

## 3. Storage Format
- Gridded data: NetCDF (`.nc`), GeoTIFF (`.tif`), or pre-extracted CSV tables.
- Station data: CSV files indexed by station ID and timestamp.

## 4. Policy on Unavailable Data
- If station or gridded data is missing for a given day or timestamp, the system must report `RAINFALL_DATA_UNAVAILABLE` rather than imputing fabricated values.
