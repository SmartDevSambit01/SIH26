# STEP 12.1 — SCIENTIFIC PARAMETER RESEARCH & LITERATURE EVIDENCE

## Overview
This document compiles peer-reviewed scientific literature and technical reports from authoritative agencies (**Geological Survey of India (GSI)**, **India Meteorological Department (IMD)**, **ISRO / NRSC**, **NASA**, and **ESA**) on landslide triggering mechanisms and parameter thresholds for Northeast India (specifically Kohima, Nagaland and Aizawl, Mizoram).

---

## 1. Geological & Geomorphological Context

### A. Kohima District, Nagaland
- **Geology**: Predominantly composed of Tertiary **Disang Group** shales and slates with intercalated sandstones. Highly folded, faulted, and crushed during Himalayan-Indo-Burman orogeny.
- **Weathering & Overburden**: Disang shales weather rapidly into fine-grained clayey-silty soil overburden (1.5 m – 6 m thick). When saturated, effective shear strength and cohesion drops drastically.
- **Slope Angle Prone Range**: **25° to 45°**. Slopes steeper than 45° are predominantly barren rock scarps with lower soil accumulation.
- **Key Corridors**: NH-29 (Dzudza, Phesama, Sechu Zubza) and Kisama heritage village zone.

### B. Aizawl District, Mizoram
- **Geology**: Formed by north-south trending narrow anticlinal ridges and synclinal valleys of the **Surma Group** (Bhuban Formation) consisting of alternating sandstone, siltstone, and shale beds.
- **Geological Structure**: Steep dip slopes (30° – 50°) prone to planar rockslides and wedge failures, particularly along road cuts and quarry faces.
- **Slope Angle Prone Range**: **30° to 50°**.
- **Key Corridors**: Melthum Quarry, Hlimen Ridge, Durtlang Hills, and Bawngkawn Chhimveng.

---

## 2. Rainfall Trigger Thresholds

| Parameter | Kohima Threshold | Aizawl Threshold | Source & Evidence Strength |
| :--- | :--- | :--- | :--- |
| **Hourly Intensity** | 15 – 25 mm/h | 20 – 30 mm/h | GSI NLSM Guidelines (2020) / MIRSAC (2021) — **HIGH** |
| **24-Hour Cumulative** | 80 – 120 mm | 100 – 135 mm | GSI / IMD (2022) / SDMA Cyclone Remal Report (2024) — **VERY HIGH** |
| **7-Day Antecedent** | 180 – 250 mm | 180 – 250 mm | Journal of Asian Earth Sciences (2019) / NRSC — **HIGH (REGIONAL)** |

---

## 3. Soil Moisture & Satellite Radar Indicators

### A. Soil Moisture Saturation (SMAP L3)
- **Volumetric Moisture Threshold**: **0.38 to 0.48 m³/m³** (corresponding to >80-85% soil saturation).
- **24-Hour Soil Moisture Delta**: **> +20% change** indicates rapid wetting front infiltration.
- **Status Tag**: `DISTRICT_SPECIFIC_THRESHOLD_UNAVAILABLE` (Global NASA Landslide Program contextual evidence applied).

### B. Sentinel-1 SAR Backscatter Amplitude Change
- **VV/VH Change Delta**: **-3.0 dB to -4.5 dB** change between pre-event and post-event co-polarization imagery.
- **Mechanism**: Loss of vegetation structure and surface roughness change due to fresh landslide scarps.
- **Status Tag**: `DISTRICT_SPECIFIC_THRESHOLD_UNAVAILABLE` (ESA / ASF Global Earth Observation guidelines applied).

---

## 4. Evidence Master Table

All evidence records are preserved in [data/research/landslide_parameter_evidence.csv](file:///c:/Users/sambi/Downloads/SIH%2026/data/research/landslide_parameter_evidence.csv) with fields:
`parameter`, `parameter_group`, `min_value`, `max_value`, `unit`, `region`, `district`, `trigger_type`, `source_title`, `source_organization`, `source_year`, `source_url`, `evidence_strength`, `applicability`, `notes`.
