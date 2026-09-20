# SARVAS --- Technical Approach

## AI-Based Early Warning and Landslide Risk Monitoring System in the North Eastern Region of India

**Problem Statement:** 26001\
**Organization:** Ministry of Development of North Eastern Region
(MDoNER)\
**Theme:** Disaster Management\
**Category:** Software\
**Pilot districts:** Kohima, Nagaland and Aizawl, Mizoram

---

# 1. Technical Objective

The system is a **multi-source geospatial, spatiotemporal
disaster-intelligence platform** that estimates landslide hazard,
identifies flash-flood-prone areas, evaluates exposed assets, and
generates actionable early-warning intelligence.

The technical objective is not to claim deterministic prediction of
every landslide at an exact minute and coordinate. Instead, the system
estimates:

1.  **Static susceptibility:** where terrain and environmental
    conditions are inherently more prone to failure.
2.  **Dynamic hazard:** whether current and antecedent conditions are
    capable of triggering a landslide.
3.  **Flash-flood hazard:** where intense rainfall can generate rapid
    runoff, water accumulation and flow-path risk.
4.  **Compound hazard:** where landslide and flood hazards interact.
5.  **Exposure and impact:** which roads, settlements, population and
    critical infrastructure may be affected.
6.  **Operational priority:** where authorities should inspect, verify,
    warn or prepare resources first.
7.  **Near-real-time alerts:** geo-targeted warnings through an
    authorized verification and dissemination workflow.

The overall architecture is:

```text
Satellite + GIS + Historical Events + Field Reports
                         |
                         v
              Ingestion / Preprocessing
                         |
                         v
              Quality + Freshness Gate
                         |
              +----------+----------+
              |                     |
              v                     v
       Static Susceptibility    Dynamic Triggers
              |                     |
              |                     |
              +----------+----------+
                         |
                         v
                  Hazard Engine
                         |
                         v
              Calibration / Uncertainty
                         |
                         v
                Exposure / Impact
                         |
                         v
              Operational Priority
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
        GIS            Alerts       Field Verification
          |              |              |
          +--------------+--------------+
                         |
                         v
                  Feedback / Learning
```

---

# 2. Fundamental Design: Susceptibility vs Hazard vs Risk

These three concepts are explicitly separated.

## 2.1 Susceptibility

Answers:

> Where could a landslide occur because of the physical characteristics
> of the location?

Main inputs:

- slope
- elevation
- curvature
- TWI
- TPI
- relief
- geology
- geomorphology
- soil
- land cover
- vegetation
- drainage characteristics
- historical landslide evidence

## 2.2 Dynamic hazard

Answers:

> Are current environmental conditions capable of triggering failure?

Main inputs:

- rainfall
- rainfall intensity
- rainfall duration
- antecedent rainfall
- soil moisture
- flood condition
- Sentinel-1 change/deformation evidence
- verified field observations

## 2.3 Exposure / impact

Answers:

> If a hazardous area fails, what can be affected?

Main inputs:

- population
- settlements
- roads
- bridges
- buildings
- hospitals
- schools
- utilities
- critical infrastructure
- accessibility and alternative routes

Therefore:

```text
SUSCEPTIBILITY + TRIGGER = HAZARD

HAZARD + EXPOSURE + CRITICALITY = OPERATIONAL PRIORITY
```

Roads and population are not automatically physical landslide causes.
They are primarily exposure/impact variables unless engineering-quality
road-cut or drainage information is available.

---

# 3. Pilot Geography and Common Analysis Grid

## 3.1 Districts

The current pilot covers:

- Kohima District, Nagaland
- Aizawl District, Mizoram

The architecture is designed to scale to the complete North Eastern
Region.

## 3.2 District boundaries

District boundaries are stored as geospatial polygons and normalized to
WGS84 (`EPSG:4326`) for interoperability with web GIS.

## 3.3 Analysis grid

The project uses an approximately **500 m × 500 m analysis grid**.

Current grid:

- Kohima: 6,055 cells
- Aizawl: 10,906 cells
- Total: 16,961 cells

The 500 m grid is the **common analysis unit**, not the native
resolution of every sensor.

This distinction is mandatory.

Example:

```text
SRTM       ~30 m
Sentinel-2 10/20/60 m depending on band
GPM        ~0.1° (~10 km)
SMAP       ~9 km
Project    ~500 m analysis cell
```

A coarse satellite observation can therefore be mapped to many project
cells, but the system must never claim that the coarse sensor has
acquired 500 m native measurements.

---

# 4. Data-Source Architecture

---

Layer Source Data Purpose

---

Rainfall NASA GPM IMERG precipitation rate/accumulation Dynamic landslide + flash-flood
Early trigger

Soil moisture NASA SMAP SPL3SMP_E soil moisture Antecedent wetness
V006

Terrain SRTM DEM Static terrain

SAR Copernicus VV/VH/change/coherence where suitable Surface-change/deformation/flood
Sentinel-1 evidence

Vegetation Copernicus NDVI/NDMI/land-cover features Environmental/susceptibility
Sentinel-2 MSI condition

Geology GSI / authoritative lithology/structure Susceptibility
layers

Geomorphology GSI / authoritative geomorphic units Susceptibility
layers

Soil authoritative soil texture/depth/drainage etc. Susceptibility + hydrology
data

Hydrology DEM + hydrography flow accumulation/drainage/HAND Flood + landslide conditioning

Historical events GSI/state event location/date/type Labels and susceptibility evidence
agencies/verified  
 sources

Roads OSM / authoritative road network/class/bridges Exposure and possible
GIS anthropogenic conditioning

Population official/gridded population density Exposure
population data

Settlements OSM / authoritative settlements/buildings Exposure
GIS

Infrastructure authoritative hospitals/schools/bridges/utilities Exposure
GIS/OSM where  
 appropriate

Field reports authorized users observations/photos/location Verification/corroboration

---

---

# 5. Data Ingestion Layer

Each source follows:

```text
Source API / file
      |
      v
Download / query
      |
      v
Raw archive
      |
      v
Format conversion
      |
      v
Geospatial reprojection
      |
      v
Quality control
      |
      v
Feature extraction
      |
      v
500 m cell mapping
      |
      v
Feature store
```

Every observation stores:

```text
source
product
version
acquisition timestamp
ingestion timestamp
native resolution
temporal resolution
quality flag
data status
processing version
```

This provides complete data provenance.

---

# 6. NASA GPM IMERG Rainfall Pipeline

## 6.1 Why GPM

Rainfall is one of the most important dynamic triggers for
rainfall-induced landslides and flash floods.

A single rainfall value is insufficient. The system requires:

- intensity
- duration
- accumulation
- antecedent rainfall
- short-term and long-term rainfall history

## 6.2 Product

Primary rainfall source:

```text
NASA GPM IMERG Early Run
Product family: IMERG / 3IMERG
Temporal resolution: 30 minutes
Spatial grid: approximately 0.1° × 0.1°
Native spatial scale: approximately 10 km
```

IMERG Early is designed for low-latency applications. It should be
described as **near-real-time**, not instantaneous.

## 6.3 Earthdata authentication

The ingestion pipeline uses NASA Earthdata authentication.

Credentials must remain local:

```text
.env
environment variable
secure secret storage
```

Credentials must never be:

- hard-coded
- committed to Git
- exposed in the frontend
- pasted into public documentation

## 6.4 Rainfall features

For every analysis cell and prediction timestamp:

```text
rain_30m
rain_1h
rain_3h
rain_6h
rain_12h
rain_24h
rain_48h
rain_72h
rain_7d
peak_intensity
rainfall_duration
antecedent_rainfall
```

## 6.5 Rolling accumulation

For half-hour rainfall observations:

```text
R_T = Σ precipitation_i
```

where all observations inside time window `T` are summed.

Examples:

```text
R_3h
R_6h
R_24h
R_72h
R_7d
```

## 6.6 Rainfall intensity

The system preserves both:

```text
rainfall rate
```

and:

```text
rainfall accumulation
```

because:

```text
100 mm in 2 hours
```

is not hydrologically equivalent to:

```text
100 mm in several days
```

## 6.7 Rainfall duration

Duration is derived from the sequence of rainfall observations and a
configurable intensity threshold.

Conceptually:

```text
duration =
continuous time with rainfall >= configured threshold
```

The threshold must eventually be learned/calibrated from local
historical events.

## 6.8 Antecedent rainfall

Antecedent rainfall represents prior wetting:

```text
AR_3d
AR_7d
```

and potentially longer windows.

This is important because a heavy burst following already-wet conditions
can have a different effect from the same burst after a dry period.

## 6.9 Current pipeline status

The prototype has successfully ingested real NASA GPM IMERG Early
observations.

The current pipeline has:

- discovered recent NASA granules;
- selected newest granules rather than oldest records;
- mapped GPM observations to all project cells;
- applied freshness validation;
- preserved native-resolution metadata.

Current implementation maps approximately **67 distinct GPM
macro-pixels** to the 16,961 project cells.

Therefore:

> 16,961 cells does not mean 16,961 independent GPM rainfall
> measurements.

---

# 7. NASA SMAP Soil-Moisture Pipeline

## 7.1 Why soil moisture

Rainfall represents forcing.

Soil moisture represents the antecedent hydrological state.

The combination:

```text
high recent rainfall
+
already wet soil
```

can indicate increased trigger conditions.

## 7.2 Product

Primary source:

```text
NASA SMAP
SPL3SMP_E
Version 006
Enhanced L3 Radiometer Global Daily
EASE-Grid 2.0
approximately 9 km
daily
```

Primary AM soil-moisture variable:

```text
/Soil_Moisture_Retrieval_Data_AM/soil_moisture
```

Units:

```text
m³/m³
```

The PM product/fields are handled where available and appropriate.

## 7.3 Features

```text
soil_moisture_current
soil_moisture_previous
soil_moisture_change
soil_moisture_change_percent
quality_flag
observation_timestamp
data_age
```

## 7.4 Change

```text
Delta_SM = SM_current - SM_previous
```

Percentage change:

```text
Delta_SM_percent =
100 × (SM_current - SM_previous) / abs(SM_previous)
```

with protection against invalid or zero denominators.

## 7.5 Spatial mapping

SMAP is approximately 9 km native resolution.

The project maps those observations to the 500 m analysis cells.

The system must display:

```text
Native SMAP resolution: ~9 km
Analysis grid: ~500 m
```

rather than implying 500 m SMAP resolution.

## 7.6 Freshness

Every SMAP observation receives:

```text
AVAILABLE
STALE
UNAVAILABLE
REQUIRES_AUTH
INVALID
```

A stale observation is not silently treated as current.

The current pilot has real NASA SMAP observations populated across the
project grid, but the latest cached observation may be stale depending
on ingestion time. The freshness gate therefore determines whether SMAP
is allowed to contribute to a current dynamic assessment.

---

# 8. SRTM DEM and Terrain Pipeline

## 8.1 DEM

Primary terrain source:

```text
USGS/NASA SRTM
approximately 30 m
```

## 8.2 Terrain derivatives

The DEM is processed into:

```text
elevation
slope
aspect
curvature
TPI
TRI
relief
TWI
flow direction
flow accumulation
drainage density
distance to drainage
HAND
```

## 8.3 Slope

Slope is calculated from local elevation gradients.

Conceptually:

```text
slope =
atan(sqrt((dz/dx)² + (dz/dy)²))
```

The system stores slope in degrees and can additionally derive percent
slope.

## 8.4 Aspect

Aspect represents direction of slope orientation.

It may influence environmental characteristics such as:

- solar exposure;
- vegetation;
- evapotranspiration;
- moisture persistence.

Aspect should not receive an arbitrary universal danger score.

## 8.5 Curvature

Curvature identifies:

```text
concave terrain
convex terrain
approximately planar terrain
```

It is useful for representing local water convergence/divergence and
morphology.

## 8.6 TWI

Topographic Wetness Index:

```text
TWI = ln(a / tan(beta))
```

where:

- `a` = specific catchment area;
- `beta` = local slope angle.

TWI is used as a terrain-derived wetness/convergence indicator.

## 8.7 TPI

Topographic Position Index compares local elevation with surrounding
terrain.

It can help distinguish:

```text
ridge
upper slope
mid-slope
valley
depression
```

## 8.8 Flow accumulation

Flow accumulation identifies where DEM-derived runoff converges.

It is particularly important for the flash-flood module.

---

# 9. Geological Susceptibility Layer

## 9.1 Why geology

Slope stability depends on:

- lithology;
- rock strength;
- weathering;
- fractures;
- bedding;
- joints;
- faults;
- lineaments;
- permeability;
- regolith/soil thickness.

## 9.2 Features

Where authoritative datasets are available:

```text
lithology
geological unit
weathering
fault distance
lineament density
structural orientation
geological contacts
```

are spatially joined to the 500 m cells.

## 9.3 Source priority

Preferred hierarchy:

```text
GSI / government authoritative source
        >
official state GIS
        >
validated scientific dataset
        >
open supplementary source
```

No geological value is fabricated when coverage is unavailable.

---

# 10. Geomorphology

Geomorphological units describe terrain-forming processes.

Possible source categories include:

```text
structural hills
dissected hills
valleys
terraces
alluvial surfaces
debris/scree
erosional landforms
```

The actual categories must be derived from the source dataset.

Features:

```text
geomorphology_class
geomorphic_distance
landform_type
```

are encoded for susceptibility.

---

# 11. Soil Properties

Where reliable spatial soil data are available:

```text
soil_texture
sand_fraction
silt_fraction
clay_fraction
soil_depth
bulk_density
hydraulic_conductivity
permeability
drainage_class
available_water_capacity
organic_matter
```

can be added.

Why:

```text
rainfall
   |
   +--> infiltration
   |
   +--> soil saturation
   |
   +--> runoff
```

Soil properties therefore influence both landslide conditioning and
flood runoff.

---

# 12. Sentinel-2 Vegetation Pipeline

## 12.1 Why vegetation

Vegetation can influence:

- root reinforcement;
- interception;
- evapotranspiration;
- surface erosion;
- soil exposure;
- land-use change.

Vegetation is therefore a conditioning/environmental feature.

It is not valid to use a simplistic rule:

```text
low NDVI = landslide
```

without local evidence.

## 12.2 Satellite

Primary optical source:

```text
Copernicus Sentinel-2 MSI
```

Band resolution:

```text
10 m / 20 m / 60 m
depending on band
```

## 12.3 NDVI

For Sentinel-2:

```text
NDVI = (B8 - B4) / (B8 + B4)
```

where:

```text
B8 = near infrared
B4 = red
```

## 12.4 Additional vegetation features

Where data quality permits:

```text
NDVI
NDMI
EVI
vegetation fraction
seasonal vegetation anomaly
vegetation change
```

## 12.5 Cloud handling

Before extracting optical features:

```text
cloud mask
cirrus mask
invalid-pixel mask
```

are applied.

Cloud-contaminated observations are not treated as valid vegetation
measurements.

## 12.6 Vegetation change

For two valid observations:

```text
Delta_NDVI =
NDVI_current - NDVI_reference
```

A persistent decline can be used as environmental-change evidence, but
must be corroborated before being interpreted as landslide evidence.

---

# 13. Sentinel-1 SAR Pipeline

## 13.1 Why Sentinel-1

Sentinel-1 uses C-band synthetic aperture radar.

SAR is valuable because it can operate:

- day and night;
- through cloud cover;
- during monsoon conditions.

## 13.2 Features

Possible features:

```text
VV backscatter
VH backscatter
VV/VH ratio
VV temporal change
VH temporal change
coherence
interferometric deformation
deformation velocity
deformation acceleration
change confidence
```

## 13.3 Backscatter change

For two observations:

```text
Delta_VV =
VV_current - VV_previous
```

and:

```text
Delta_VH =
VH_current - VH_previous
```

## 13.4 InSAR

For suitable acquisitions:

```text
SLC t1
   +
SLC t2
   |
   v
Interferogram
   |
   v
Phase processing
   |
   v
Unwrapping
   |
   v
Atmospheric/orbit correction
   |
   v
LOS deformation
```

This can provide evidence of pre-failure ground movement.

## 13.5 Corroboration requirement

SAR change is not automatically a landslide.

Backscatter changes may result from:

- vegetation;
- soil moisture;
- surface roughness;
- construction;
- agriculture;
- flooding;
- geometric effects.

Therefore SAR is treated as corroborating evidence.

## 13.6 Current pilot status

The project has a Sentinel-1 acquisition/indexing architecture, but
actual scene downloads/processing require the corresponding external
data access/authentication.

The system therefore uses:

```text
PENDING
REQUIRES_AUTH
UNAVAILABLE
```

rather than fabricating SAR values.

---

# 14. Historical Landslide Inventory

## 14.1 Sources

Historical events should be compiled from:

- Geological Survey of India;
- state disaster-management agencies;
- government reports;
- verified field reports;
- validated remote-sensing interpretation.

## 14.2 Event schema

```text
event_id
date
time
latitude
longitude
district
state
source
source_reference
landslide_type
trigger
confidence
geometry
description
```

## 14.3 Label quality

Each record receives:

```text
VERIFIED
NEEDS_VERIFICATION
APPROXIMATE
MISSING_COORDINATE
```

Only sufficiently reliable events become hard positive labels.

## 14.4 No false negatives

This rule is critical:

```text
no recorded landslide
```

does not mean:

```text
confirmed no landslide
```

An unobserved location is unknown.

Therefore the system must not randomly label all other cells as
negatives.

---

# 15. Feature Engineering

The final feature dataset is organized around:

```text
cell_id × prediction_timestamp
```

### Static features

```text
elevation
slope
aspect
curvature
TPI
TRI
TWI
relief
lithology
geomorphology
soil properties
land cover
NDVI
vegetation change
distance to drainage
drainage density
lineament/fault features
historical event density
```

### Dynamic features

```text
rain_30m
rain_1h
rain_3h
rain_6h
rain_12h
rain_24h
rain_48h
rain_72h
rain_7d
peak rainfall intensity
rainfall duration
antecedent rainfall
soil moisture current
soil moisture previous
soil moisture change
soil moisture change %
flood indicator
Sentinel-1 change
deformation/coherence where valid
field verification
```

### Exposure features

```text
road distance
road length in hazard area
road class
bridge exposure
population density
settlement density
building count
hospital distance
school distance
critical infrastructure count
```

---

# 16. Data Quality and Freshness Gate

Before any model inference:

```text
RAW OBSERVATION
       |
       v
Schema validation
       |
       v
Coordinate validation
       |
       v
Range validation
       |
       v
Timestamp validation
       |
       v
Missing-value validation
       |
       v
Freshness validation
       |
       v
Spatial coverage validation
       |
       v
QUALITY GATE
```

## 16.1 Data statuses

```text
AVAILABLE
STALE
UNAVAILABLE
REQUIRES_AUTH
INVALID
PARTIAL
```

## 16.2 Missing values

Never perform:

```text
missing rainfall -> 0
missing soil moisture -> 0
missing SAR -> no change
```

Instead:

```text
value = NULL
status = UNAVAILABLE
```

This prevents the model from confusing missing data with safe
conditions.

---

# 17. Static Susceptibility Model

The first model stage answers:

> Where is the terrain inherently susceptible?

A transparent baseline can be expressed as:

```text
TSI =
w1*slope
+w2*TWI
+w3*curvature
+w4*relief
+w5*geology
+w6*geomorphology
+w7*soil
+w8*landcover
+w9*historical_evidence
```

All features are normalized before combination.

Weights must be one of:

1.  learned from adequate training data;
2.  justified by an authoritative methodology;
3.  explicitly documented prototype policy weights.

They must not be described as ML-learned if they were manually selected.

---

# 18. Positive-Unlabeled Learning

The pilot historical dataset has very few verified positive cells and
does not contain a reliable set of confirmed negatives.

Therefore:

```text
Positive = verified landslide
Unknown = not confirmed
```

not:

```text
Unknown = negative
```

A Positive-Unlabeled or anomaly/similarity approach can:

1.  learn environmental similarity to known event cells;
2.  identify cells with similar susceptibility conditions;
3.  combine that evidence with terrain susceptibility;
4.  avoid falsely claiming that unobserved cells are safe.

This is appropriate as an interim architecture while the verified
inventory is expanded.

---

# 19. Dynamic Trigger Engine

The dynamic engine converts current conditions into trigger evidence.

Prototype trigger inputs:

```text
Rainfall
Soil moisture
Flood
Sentinel-1
Field verification
```

A transparent prototype configuration can be:

```text
Rainfall             45%
Soil moisture        35%
Flood                 10%
Sentinel-1 SAR         5%
Field verification     5%
```

Therefore:

```text
DynamicScore =
0.45*RainScore
+0.35*SoilScore
+0.10*FloodScore
+0.05*SARScore
+0.05*VerificationScore
```

These are **prototype policy weights**, not calibrated probabilities.

Only quality-approved, available observations contribute.

---

# 20. Rainfall Trigger Normalization

Rainfall should not use one arbitrary universal threshold.

Instead, derive several normalized indicators:

```text
I_30m
I_3h
I_6h
I_24h
I_72h
I_7d
```

and eventually estimate local rainfall-duration relationships.

Conceptual workflow:

```text
Historical events
      |
      v
Extract rainfall history
      |
      v
Event rainfall-duration analysis
      |
      v
Threshold candidates
      |
      v
False alarm / miss analysis
      |
      v
Local operational thresholds
```

Possible future methods:

```text
Intensity-Duration threshold
Cumulative rainfall threshold
Antecedent rainfall threshold
Intensity-Duration-Antecedent model
```

Thresholds must be locally validated for NER.

---

# 21. Soil-Moisture Trigger

Soil moisture can be converted into normalized evidence using:

```text
current percentile
historical percentile
change %
antecedent wetness
```

Conceptually:

```text
SMScore =
f(
current moisture,
moisture anomaly,
rate of change,
rainfall context
)
```

A high soil-moisture value alone does not prove landslide occurrence.

It is a trigger/conditioning signal.

---

# 22. Dynamic Hazard Combination

The prototype combines:

```text
Static Susceptibility
+
Dynamic Trigger Evidence
```

Example:

```text
CombinedHazard =
0.50*StaticSusceptibility
+
0.50*DynamicTrigger
```

This is a transparent prototype policy.

Once enough validated training data exist, the manually defined
combination can be replaced by a learned model.

---

# 23. Machine-Learning Hazard Model

## 23.1 Candidate algorithms

For tabular geospatial features:

```text
XGBoost
LightGBM
Random Forest
HistGradientBoosting
```

The first production candidate should normally be a strong interpretable
tree-based model rather than an unnecessarily complex deep-learning
system.

## 23.2 Input

```text
X_t =
{
terrain,
geology,
geomorphology,
soil,
vegetation,
rainfall history,
soil moisture,
SAR,
flood,
season,
land cover,
historical evidence
}
```

## 23.3 Target

Potential target:

```text
Y_t =
1 if a validated landslide event occurs
0 if a validated non-event/background observation is confirmed
```

Until reliable negative/background labels exist, use PU learning or
another appropriate weakly supervised strategy.

---

# 24. Probability Calibration

A model score is not automatically a probability.

Do not say:

```text
model = 0.80
therefore 80% probability
```

unless calibration has been demonstrated.

Candidate calibration methods:

```text
Platt scaling
Isotonic regression
Beta calibration
```

Calibration must use independent validation data.

---

# 25. Spatial Validation

Random splitting can produce overly optimistic results because nearby
grid cells are spatially correlated.

Use:

```text
Spatial block cross-validation
```

For example:

```text
5 km × 5 km geographic blocks
```

Train on some blocks and test on geographically separated blocks.

---

# 26. Temporal Validation

The model must not use future information to predict the past.

Example:

```text
Training:
older event years

Testing:
later event year
```

The exact split depends on the final validated inventory.

All features must satisfy:

```text
feature_timestamp <= prediction_timestamp
```

---

# 27. Cross-District Generalization

Test geographic transferability:

```text
Train -> Kohima
Test  -> Aizawl
```

and:

```text
Train -> Aizawl
Test  -> Kohima
```

This measures whether the model is learning generalizable relationships
rather than memorizing one district.

---

# 28. Evaluation Metrics

Use:

```text
Precision
Recall
F1
ROC-AUC
PR-AUC
Brier score
Calibration error
False Alarm Rate
Miss Rate
Lead Time
Spatial Hit Rate
```

For rare-event landslides, PR-AUC and event-level recall can be
especially informative.

Do not report a generic accuracy number without a scientifically valid
validation design.

---

# 29. Landslide Probability Output

After adequate training and calibration:

```text
P(Landslide | X_t)
```

can be produced.

The probability should be interpreted only within the validated
population and forecast horizon.

Before calibration:

```text
probability = NULL
calibration_status = NOT_CALIBRATED
```

This is preferable to inventing a calibrated percentage.

---

# 30. Flash-Flood Module

The platform contains a separate flood-hazard pipeline because
landslides and flash floods can share rainfall forcing but have
different physical mechanisms.

The flash-flood module estimates:

```text
flash-flood susceptibility
+
rainfall-triggered runoff hazard
+
flow-path concentration
+
possible inundation
```

It should not claim exact street-level flood depth unless hydraulic
observations/model calibration support that output.

---

# 31. Flash-Flood Static Susceptibility

Primary features:

```text
elevation
slope
flow accumulation
flow direction
TWI
drainage density
distance to stream
catchment area
valley geometry
HAND
soil infiltration properties
land cover
imperviousness where available
stream network
```

The most important conceptual process is:

```text
Rainfall
   |
   v
Infiltration / runoff
   |
   v
Flow accumulation
   |
   v
Drainage network
   |
   v
Downstream concentration
```

---

# 32. DEM-Based Hydrological Processing

The flood module uses:

```text
DEM
 |
 v
Hydrologic conditioning
 |
 v
Flow direction
 |
 v
Flow accumulation
 |
 v
Stream extraction
 |
 v
Catchment delineation
 |
 v
Drainage density
 |
 v
HAND
```

These layers are then mapped to the common analysis grid.

---

# 33. HAND --- Height Above Nearest Drainage

Conceptually:

```text
HAND =
elevation(cell)
-
elevation(reference drainage)
```

Low HAND generally identifies terrain closer vertically to drainage
channels.

It is useful for flood susceptibility but is not, by itself, a complete
flood-depth model.

---

# 34. Flash-Flood Rainfall Trigger

The flood trigger uses:

```text
rain_30m
rain_1h
rain_3h
rain_6h
rain_12h
rain_24h
rain_72h
peak intensity
rainfall duration
antecedent rainfall
```

Conceptually:

```text
FlashFloodTrigger =
f(
short-duration intensity,
rainfall accumulation,
antecedent wetness,
catchment response,
flow concentration
)
```

This is more physically meaningful than using rainfall alone.

---

# 35. Rainfall-Runoff Model

For an advanced flood system:

```text
Rainfall
   |
   v
Interception
   |
   v
Infiltration
   |
   v
Surface runoff
   |
   v
Channel routing
   |
   v
Water accumulation
   |
   v
Flood extent/depth
```

Candidate hydrological approaches:

```text
SCS Curve Number
Green-Ampt infiltration
Unit hydrograph
Kinematic-wave runoff
Distributed hydrological model
```

The final choice depends on the availability of:

- soil;
- land cover;
- rainfall;
- drainage;
- channel geometry;
- gauge/stream observations;
- historical flood extents.

---

# 36. Flash-Flood ML Model

Potential inputs:

```text
rainfall intensity
rainfall accumulation
antecedent rainfall
soil moisture
flow accumulation
HAND
TWI
slope
drainage density
distance to stream
catchment area
land cover
imperviousness
soil
historical flood labels
```

Targets can be:

```text
flood / no flood
```

or, if enough observations exist:

```text
inundation depth
inundation extent
arrival time
```

---

# 37. Sentinel-1 Flood Detection

SAR can help detect flood extent even under cloud cover.

Workflow:

```text
Pre-event SAR
       +
Post-event SAR
       |
       v
Radiometric calibration
       |
       v
Speckle filtering
       |
       v
Terrain correction
       |
       v
Backscatter comparison
       |
       v
Water classification
       |
       v
Flood polygon
       |
       v
500 m grid intersection
       |
       v
flood_indicator
```

The flood layer can then feed:

```text
FlashFloodHazard
```

and, where relevant:

```text
LandslideDynamicContext
```

---

# 38. Compound Landslide + Flood Hazard

The system explicitly supports compound events.

Example:

```text
Extreme rainfall
       |
       +-----------------------+
       |                       |
       v                       v
Slope saturation          Runoff generation
       |                       |
       v                       v
Landslide hazard          Flash-flood hazard
       |                       |
       +-----------+-----------+
                   |
                   v
             Compound hazard
```

A mountainous road corridor can therefore have:

```text
landslide-prone slope
+
downstream flash-flood corridor
+
bridge exposure
```

which creates a higher operational response requirement.

---

# 39. Road Intelligence

Roads have two technical roles.

## 39.1 Physical conditioning

If detailed road engineering data exist, road cuts can affect:

- slope geometry;
- drainage;
- toe support;
- runoff concentration.

Such engineering features can be included in susceptibility.

## 39.2 Exposure

For operational impact:

```text
road_distance
road_length_inside_hazard_zone
road_class
bridge_count
alternative_route_availability
```

are exposure variables.

Example:

```text
same hazard score
+
major highway
```

has different operational consequences from:

```text
same hazard score
+
unoccupied remote slope
```

---

# 40. OpenStreetMap Road Pipeline

Where appropriate, OSM can provide:

```text
motorway
trunk
primary
secondary
tertiary
residential
track
bridge
tunnel
```

The system can calculate:

```text
nearest_road_distance
road_length_intersecting_hazard
road_class
bridge_exposure
```

OSM coverage may be incomplete, so the dataset must retain source and
completeness metadata.

---

# 41. Population and Settlement Exposure

Population is not a landslide cause.

It is an exposure variable.

Features:

```text
population_density
population_inside_hazard_area
settlement_density
building_count
distance_to_settlement
```

Potential output:

```text
Estimated population exposed
```

only when reliable population data are available.

---

# 42. Critical Infrastructure

Potential assets:

```text
Hospitals
Schools
Bridges
Police stations
Fire stations
Government offices
Power infrastructure
Water infrastructure
Telecommunication infrastructure
Relief shelters
Major roads
Railways
Airports
```

Each asset can store:

```text
asset_id
asset_type
latitude
longitude
criticality
nearest_hazard_cell
hazard_score
exposure_status
```

---

# 43. Exposure / Impact Model

The impact layer is separate from the physical hazard model.

Conceptually:

```text
Impact =
f(
hazard,
population,
road importance,
infrastructure criticality,
accessibility,
isolation,
alternative routes
)
```

A simple conceptual relationship is:

```text
OperationalPriority
=
Hazard × Exposure × Criticality
```

The exact implementation must be documented and validated.

---

# 44. Area-Level Risk Intelligence

Users should be able to search:

```text
Kohima
Aizawl
Durtlang
Khonoma
Bara Bazar
Treasury
```

The search system must be cross-district.

A search for an Aizawl locality should:

```text
identify locality
      |
      v
identify district
      |
      v
switch map to district
      |
      v
highlight associated cells
      |
      v
display risk dashboard
```

The result can show:

```text
hazard
rainfall
soil moisture
terrain
vegetation
flood
SAR
roads
population
infrastructure
historical events
data freshness
recommended action
```

---

# 45. GIS Map Architecture

Frontend:

```text
React
+
MapLibre GL JS
```

Map layers:

```text
Satellite basemap
District boundary
500 m analysis grid
Susceptibility
Risk
Historical landslides
Rainfall
Soil moisture
Flood
Sentinel-1
Vegetation
Roads
Settlements
Infrastructure
Drainage
```

Controls:

```text
Zoom
Pan
Search
District switch
Layer toggle
Cell hover
Cell click
Locality selection
Historical event inspection
```

---

# 46. Cell-Level Explainability

Every selected cell should provide:

```text
Cell ID
District
Coordinates

Static susceptibility
Dynamic trigger
Combined hazard

Rainfall:
  30 min
  3 h
  24 h
  72 h
  7 d
  intensity
  duration

Soil moisture:
  current
  previous
  change
  freshness

Terrain:
  elevation
  slope
  curvature
  TWI
  TPI
  relief

Vegetation:
  NDVI
  change

SAR:
  VV
  VH
  change
  confidence

Flood:
  indicator
  flow accumulation
  HAND

Exposure:
  road
  population
  infrastructure

Data quality:
  source
  age
  completeness
```

---

# 47. Risk Classification

Prototype risk classes:

Risk class Score Color Meaning

---

Critical \>=80 Purple Immediate investigation / urgent advisory
High 60--79.9 Red Severe hazard attention
Warning 45--59.9 Orange Early warning / inspection
Watch 30--44.9 Yellow Enhanced monitoring
Low \<30 Green Routine monitoring

These are **prototype operational thresholds** until calibrated against
validated local events.

They must not be presented as universal scientific thresholds.

---

# 48. Alert Decision Engine

The alert workflow is:

```text
Risk Engine
     |
     v
Threshold / anomaly detection
     |
     v
Candidate Alert
     |
     v
Authorized Officer Verification
     |
     v
CAP-formatted alert
     |
     v
Geo-targeted dissemination
     |
     +--> District Authority
     +--> Disaster Management Authority
     +--> Field Teams
     +--> Local Communities
```

The prototype should not automatically issue a public evacuation order
from an unverified AI score.

---

# 49. Near-Real-Time Alert Architecture

The system is designed for:

```text
near-real-time
```

because satellite products have different acquisition and processing
latency.

Examples:

```text
GPM:
30-minute observation cadence, low-latency product

SMAP:
daily observation product

Sentinel-1:
acquisition/revisit dependent

Sentinel-2:
acquisition + cloud-free observation dependent

Field reports:
event-driven
```

Therefore the dashboard must always display:

```text
last observation
data age
source
freshness status
```

---

# 50. Common Alerting Protocol

The alert payload can use CAP-style fields:

```text
identifier
sender
sent
status
msgType
scope
event
urgency
severity
certainty
effective
expires
area
polygon/circle
instruction
```

Cell Broadcast integration should be represented as:

```text
integration-ready
```

until authorized government/telecom infrastructure is actually
connected.

The system must not claim direct control over telecom towers.

---

# 51. Field Verification

Human verification is a first-class data source.

Possible observations:

```text
fresh ground crack
road settlement
retaining-wall failure
rockfall
mud movement
water seepage
blocked drainage
fresh debris
flooded road
bridge overtopping
```

Each report stores:

```text
location
timestamp
report type
evidence
reporter role
confidence
verification status
```

Workflow:

```text
Field/Citizen Report
       |
       v
Geolocation
       |
       v
Evidence validation
       |
       v
Authorized verification
       |
       v
Risk evidence update
       |
       v
Alert decision
```

---

# 52. Human + AI Corroboration

The system follows:

```text
AI detects anomaly
        |
        v
AI identifies high-risk cell
        |
        v
Field evidence requested
        |
        v
Officer verifies
        |
        v
Alert confidence increases
```

This reduces dependence on any single sensor.

The architecture is therefore:

```text
Predict
+
Verify
+
Corroborate
+
Prioritize
+
Act
+
Learn
```

---

# 53. Uncertainty Model

A mature system should return both:

```text
hazard
```

and:

```text
uncertainty
```

Example:

```text
hazard_score = 72
uncertainty = MEDIUM
data_completeness = 68%
```

Uncertainty sources:

```text
coarse rainfall resolution
coarse soil moisture
missing SAR
cloud contamination
limited historical labels
incomplete road data
incomplete infrastructure data
model extrapolation
```

A high hazard supported by several independent sensors should be
distinguished from a high score generated from sparse evidence.

---

# 54. Sensor-Fusion Confidence

For every cell:

```text
Rainfall       AVAILABLE
Soil moisture  AVAILABLE
Terrain        AVAILABLE
SAR            AVAILABLE
Flood          AVAILABLE
Field report   VERIFIED
```

The system derives an evidence-confidence indicator from:

```text
number of independent sources
freshness
quality
spatial alignment
agreement/disagreement
```

The UI can show:

```text
Hazard: HIGH
Confidence: HIGH
```

or:

```text
Hazard: HIGH
Confidence: LOW
```

without pretending that confidence itself is a probability.

---

# 55. Advanced Spatiotemporal Model

After enough training data are available, the system can evolve from
feature snapshots to sequences.

Example:

```text
t-168h
t-144h
t-120h
...
t-24h
t
```

Each timestamp contains:

```text
rainfall
soil moisture
SAR
flood
```

while static features remain:

```text
terrain
geology
soil
land cover
```

A temporal model can then learn:

```text
dry
 -> wetting
 -> persistent rainfall
 -> saturation
 -> extreme trigger
 -> failure
```

Candidate models:

```text
LSTM
GRU
Temporal CNN
Temporal Transformer
ConvLSTM
Spatiotemporal GNN
```

Deep learning should only be introduced when the event inventory
supports it.

---

# 56. Graph-Based Spatial Modeling

The 500 m grid can be converted to a graph.

```text
Cell A ---- Cell B ---- Cell C
  |           |           |
Cell D ---- Cell E ---- Cell F
```

Edges can represent:

```text
spatial adjacency
flow direction
drainage connectivity
road connectivity
river connectivity
```

This is especially useful for flood propagation and upstream/downstream
relationships.

---

# 57. Leakage Prevention

No future information may enter a historical prediction.

Incorrect:

```text
Predict event at T
using imagery captured after T
```

Correct:

```text
Prediction at T
uses only information available <= T
```

Examples:

```text
rainfall(t-72h ... t)
soil moisture(last observation <= t)
SAR(last valid acquisition <= t)
Sentinel-2(last valid cloud-free observation <= t)
terrain(static)
```

---

# 58. Event-Centric Training

For every historical event:

```text
Event location
+
surrounding cells
+
pre-event temporal window
```

should be constructed.

Example:

```text
T-168h
T-120h
T-72h
T-48h
T-24h
T
```

For every time step:

```text
rainfall
soil moisture
SAR
flood
```

are joined with static terrain/geology/vegetation features.

This preserves temporal causality.

---

# 59. Training Data Expansion

The pilot cannot remain dependent on a very small number of verified
events for a production-grade calibrated probability model.

Training expansion should include:

```text
historical landslide points
historical landslide polygons
event date/time
rainfall history
soil moisture
terrain
geology
vegetation
SAR evidence
flood condition
land cover
road context
field validation
```

The system should continuously convert verified events into high-quality
training examples.

---

# 60. Negative / Background Sampling

When sufficient event inventory exists, scientifically defensible
background/non-event sampling can be created.

Possible approaches:

```text
verified non-event observations
carefully sampled background locations
temporal non-event windows
```

The sampling procedure must be documented.

Do not create negatives by simply assigning:

```text
all non-event cells = 0
```

without considering observation bias.

---

# 61. Model Calibration Pipeline

```text
Validated event dataset
        |
        v
Train model
        |
        v
Spatial CV
        |
        v
Temporal test
        |
        v
Independent validation
        |
        v
Calibration
        |
        v
Calibration metrics
        |
        v
Deploy only if acceptable
```

Calibration metrics:

```text
Brier score
Expected Calibration Error
Reliability curve
Calibration intercept
Calibration slope
```

---

# 62. Model Explainability

For tree models:

```text
SHAP
feature importance
partial dependence
```

Example explanation:

```text
High recent rainfall
+
high antecedent wetness
+
steep slope
+
high TWI
+
supporting SAR change
=
elevated hazard evidence
```

The interface should expose the contributing evidence rather than only a
black-box score.

---

# 63. Model Output Contract

Example:

```json
{
  "cell_id": "KOH_01378",
  "timestamp": "2026-09-18T00:00:00Z",
  "static_susceptibility": 61.48,
  "dynamic_trigger_score": 72.3,
  "hazard_score": 66.89,
  "risk_level": "HIGH",
  "probability": null,
  "calibration_status": "NOT_CALIBRATED",
  "data_quality": "PARTIAL",
  "factors": {
    "rainfall": "HIGH",
    "soil_moisture": "ELEVATED",
    "terrain": "HIGH_SUSCEPTIBILITY",
    "sar": "UNAVAILABLE",
    "flood": "AVAILABLE"
  }
}
```

When calibrated:

```text
probability
```

can be populated.

Before calibration:

```text
probability = null
```

---

# 64. API Architecture

Backend:

```text
Python
FastAPI
Pydantic
GeoPandas
Rasterio
NumPy
Pandas
scikit-learn
XGBoost / LightGBM
PostgreSQL/PostGIS
```

Core APIs:

```text
GET /api/districts
GET /api/districts/{district}/grid
GET /api/districts/{district}/risk

GET /api/cells/{cell_id}
GET /api/cells/{cell_id}/risk
GET /api/cells/{cell_id}/parameters

GET /api/rainfall/latest
GET /api/soil-moisture/latest
GET /api/satellite/latest
GET /api/flood/latest

GET /api/areas
GET /api/areas/{area_id}/risk

GET /api/model/metadata
GET /api/model/metrics

GET /api/alerts
POST /api/alerts/generate
POST /api/alerts/{id}/verify
POST /api/alerts/{id}/acknowledge
POST /api/alerts/{id}/expire
```

---

# 65. Production Database

Recommended database:

```text
PostgreSQL + PostGIS
```

Core entities:

```text
districts
analysis_cells
rainfall_observations
soil_moisture_observations
sar_observations
vegetation_observations
flood_observations
landslide_events
roads
settlements
infrastructure
risk_assessments
alerts
field_reports
model_versions
```

Large raw satellite files should remain in object storage rather than
being unnecessarily placed inside relational tables.

---

# 66. Data Lake / File Architecture

Recommended:

```text
data/
  raw/
  intermediate/
  processed/
  features/
  models/
  validation/
  research/
```

Example:

```text
data/raw/gpm/
data/raw/smap/
data/raw/sentinel1/
data/raw/sentinel2/

data/processed/terrain/
data/processed/geology/
data/processed/vegetation/
data/processed/flood/

data/features/
data/models/
data/validation/
```

---

# 67. Technology Stack

## Frontend

```text
React
Vite
MapLibre GL JS
GeoJSON / vector tiles
```

## Backend

```text
Python
FastAPI
Pydantic
Pandas
NumPy
GeoPandas
Rasterio
Shapely
PyProj
SciPy
scikit-learn
XGBoost / LightGBM
```

## Satellite / geospatial

```text
NASA Earthdata
Earthaccess
HDF5
GDAL
Rasterio
Sentinel processing tools
```

## Database

```text
PostgreSQL
PostGIS
```

## Validation

```text
pytest
schema validation
geospatial validation
data-quality validation
model validation
API tests
```

---

# 68. Security

All external credentials are local-only.

Use:

```text
.env
environment variables
secure secret manager
```

Protect:

```text
NASA Earthdata token
passwords
API keys
service credentials
```

Never expose secrets in:

```text
frontend JavaScript
Git
GeoJSON
logs
screenshots
public folders
documentation
```

---

# 69. Pipeline Scheduling

A production deployment can schedule ingestion according to source
cadence.

Conceptually:

```text
GPM
 -> frequent ingestion

SMAP
 -> daily ingestion

Sentinel-1
 -> acquisition-driven ingestion

Sentinel-2
 -> acquisition/cloud-quality driven ingestion

Field reports
 -> event-driven

Static GIS
 -> version-driven update
```

Each ingestion run updates:

```text
last_success_timestamp
last_observation_timestamp
data_age
freshness_status
```

---

# 70. Monitoring

Operational monitoring should track:

```text
GPM last observation
SMAP last observation
Sentinel-1 last acquisition
Sentinel-2 last valid scene
pipeline success/failure
download failures
missing cells
stale observations
API latency
model inference latency
alert count
alert verification time
```

---

# 71. Model Drift

Monitor:

```text
rainfall distribution drift
soil-moisture distribution drift
land-cover changes
vegetation changes
road expansion
urbanization
new infrastructure
sensor/product changes
```

If drift is detected:

```text
Review
 -> Retrain
 -> Recalibrate
 -> Revalidate
 -> Redeploy
```

---

# 72. Reproducibility

Every model release stores:

```text
code version
data versions
feature schema
training period
validation design
hyperparameters
model artifact
calibration artifact
metrics
thresholds
feature importance
software versions
```

A prediction must be traceable to the input observations that generated
it.

---

# 73. Fail-Safe Architecture

If a dynamic source is unavailable:

```text
DO NOT:
fabricate data
fill missing rainfall with zero
fill missing SMAP with zero
treat missing SAR as no change
pretend stale data are live
claim calibrated probability
```

Instead:

```text
dynamic_status = UNAVAILABLE
dynamic_score = NULL
probability = NULL
static_susceptibility = available
```

The GIS can still show static susceptibility.

---

# 74. Operational Decision Layer

AI should provide decision support, not replace authorized
disaster-management decisions.

Workflow:

```text
AI hazard
    |
    v
Exposure
    |
    v
Recommended action
    |
    v
Authorized authority
    |
    v
Warning / response
```

Possible system recommendations:

```text
MONITOR
INSPECT
VERIFY
RESTRICT ACCESS
ISSUE WARNING
PRE-POSITION RESPONSE TEAMS
PREPARE EVACUATION
EVACUATE
```

Actual public instructions remain under authorized disaster-management
protocols.

---

# 75. Priority Queue

If hundreds of cells become hazardous:

```text
Hazard
+
Exposure
+
Criticality
+
Evidence confidence
```

can be used to create an operational response queue.

Example data:

```text
Priority
Cell
District
Hazard
Population exposed
Road exposure
Critical infrastructure
Confidence
Recommended action
```

This converts a raw map into an actionable operational dashboard.

---

# 76. Complete End-to-End Landslide Pipeline

```text
NASA GPM
   |
   +--> Rainfall rate
   +--> Accumulation
   +--> Intensity
   +--> Duration
   +--> Antecedent rainfall

NASA SMAP
   |
   +--> Current soil moisture
   +--> Previous soil moisture
   +--> Change
   +--> Change %

SRTM
   |
   +--> Elevation
   +--> Slope
   +--> Aspect
   +--> Curvature
   +--> TWI
   +--> TPI
   +--> Relief
   +--> Flow accumulation

GSI / authoritative GIS
   |
   +--> Geology
   +--> Geomorphology
   +--> Structure
   +--> Soil

Sentinel-2
   |
   +--> NDVI
   +--> NDMI
   +--> Vegetation change
   +--> Land-cover information

Sentinel-1
   |
   +--> VV
   +--> VH
   +--> Backscatter change
   +--> Coherence/deformation where valid

Historical inventory
   |
   +--> Verified events
   +--> Event timing
   +--> Event location

Field reports
   |
   +--> Human verification
   +--> Evidence
   +--> Confirmation

                |
                v
        FEATURE ENGINEERING
                |
                v
       STATIC SUSCEPTIBILITY
                |
                v
       DYNAMIC TRIGGER ENGINE
                |
                v
          HAZARD ENGINE
                |
                v
       CALIBRATION / UNCERTAINTY
                |
                v
        EXPOSURE / IMPACT
                |
                v
       OPERATIONAL PRIORITY
                |
                v
       GIS + ALERT + RESPONSE
```

---

# 77. Complete Flash-Flood Pipeline

```text
NASA GPM
   |
   +--> 30 min rainfall
   +--> short-duration accumulation
   +--> 1h / 3h / 6h
   +--> 24h / 72h
   +--> intensity
   +--> duration

NASA SMAP
   |
   +--> antecedent wetness

SRTM DEM
   |
   +--> Flow direction
   +--> Flow accumulation
   +--> Catchment area
   +--> TWI
   +--> Drainage density
   +--> HAND
   +--> Valley geometry

Soil
   |
   +--> infiltration properties

Land cover
   |
   +--> imperviousness
   +--> runoff characteristics

Hydrography
   |
   +--> streams
   +--> drainage network

Sentinel-1
   |
   +--> flood extent evidence

Historical flood inventory
   |
   +--> training labels

                |
                v
        RAINFALL-RUNOFF MODEL
                |
                v
       FLASH-FLOOD HAZARD
                |
                v
        FLOOD EXTENT / FLOW
                |
                v
          EXPOSURE ANALYSIS
                |
                v
              ALERT
```

---

# 78. Compound Disaster Intelligence

The platform can combine:

```text
Landslide hazard
+
Flash-flood hazard
+
Road exposure
+
Bridge exposure
+
Population exposure
+
Critical infrastructure
```

Example:

```text
Heavy rainfall
      |
      +--> steep slope --> landslide hazard
      |
      +--> saturated soil --> landslide hazard
      |
      +--> high flow accumulation --> flash-flood hazard
      |
      +--> low HAND --> flood exposure
      |
      +--> major road/bridge --> high operational impact
```

The result is a **compound disaster response zone**.

---

# 79. Advanced Future Architecture

After sufficient data accumulation:

```text
Multi-source feature store
        |
        v
Spatiotemporal ML
        |
        +--> Landslide probability
        |
        +--> Flash-flood probability
        |
        +--> Compound hazard
        |
        v
Probability calibration
        |
        v
Uncertainty estimation
        |
        v
Exposure model
        |
        v
Operational optimization
        |
        v
Automated monitoring
        |
        v
Continuous learning
```

Potential advanced methods:

```text
XGBoost / LightGBM
Temporal Transformer
Graph Neural Network
ConvLSTM
ensemble learning
Bayesian uncertainty
```

---

# 80. Continuous Learning Loop

Every verified event becomes a new learning record:

```text
Prediction
   |
   v
Observed condition
   |
   v
Field verification
   |
   v
Validated event label
   |
   v
Training dataset
   |
   v
Model retraining
   |
   v
Calibration
   |
   v
Spatial/temporal validation
   |
   v
New model release
```

This is how the prototype can progressively move toward a calibrated
regional operational model.

---

# 81. Production-Grade Model Readiness

A genuinely calibrated landslide probability system requires:

```text
Large validated event inventory
+
reliable background/non-event observations
+
temporal alignment
+
spatial coverage
+
multi-year observations
+
quality-controlled satellite data
+
spatial validation
+
temporal validation
+
independent test set
+
probability calibration
+
uncertainty estimation
```

The current pilot should therefore distinguish:

```text
OPERATIONAL PROTOTYPE
```

from:

```text
FULLY CALIBRATED REGIONAL PRODUCTION MODEL
```

The latter is achieved through data accumulation and repeated
validation, not by assigning an arbitrary percentage to a prototype
score.

---

# 82. Scientific Integrity Rules

The system must never:

1.  claim GPM is a 500 m native rainfall product;
2.  claim SMAP is a 500 m native soil-moisture product;
3.  claim a satellite observation is live when it is stale;
4.  convert missing data to zero;
5.  convert unknown cells into confirmed negatives;
6.  call an uncalibrated score a probability;
7.  claim exact deterministic landslide timing;
8.  claim SAR change is automatically a landslide;
9.  claim NDVI alone predicts landslides;
10. treat roads/population as physical causes without engineering
    justification;
11. claim flood depth without a validated hydraulic/hydrological basis;
12. claim model accuracy without a valid independent evaluation;
13. claim Cell Broadcast delivery without authorized infrastructure
    integration.

---

# 83. Current Pilot Implementation State

The existing prototype already contains the foundation for:

```text
500 m analysis grid
Kohima + Aizawl
SRTM terrain
slope
elevation
curvature
TWI
historical landslide evidence
NASA GPM ingestion
NASA SMAP ingestion
dynamic risk engine
MapLibre GIS
cross-district area search
cell-level details
alert workflow
officer verification
CAP-ready alert structure
data freshness gates
FastAPI backend
React frontend
```

Current dynamic source realities must remain visible:

```text
GPM:
real NASA observations
near-real-time product
freshness monitored

SMAP:
real NASA observations
daily product
freshness monitored
may be stale depending on latest acquisition

Sentinel-1:
architecture ready
actual data dependent on access/authentication

Sentinel-2:
can provide vegetation/land-cover features once valid scenes are ingested

Flood:
can use DEM hydrology + rainfall and later Sentinel-1 flood observations

Road/population/infrastructure:
must be populated only from real datasets
```

---

# 84. Recommended Development Sequence

## Phase 1 --- Stable foundation

```text
District boundaries
500 m grid
SRTM
terrain derivatives
historical inventory
```

## Phase 2 --- Dynamic rainfall

```text
GPM ingestion
freshness
rolling rainfall features
rainfall duration
antecedent rainfall
```

## Phase 3 --- Soil moisture

```text
SMAP ingestion
current/previous
change
freshness
```

## Phase 4 --- Dynamic hazard

```text
static susceptibility
+
rainfall
+
soil moisture
```

## Phase 5 --- Optical/environmental

```text
Sentinel-2
NDVI
NDMI
land cover
vegetation change
```

## Phase 6 --- Radar

```text
Sentinel-1
VV/VH
change
coherence/deformation
```

## Phase 7 --- Hydrology

```text
flow accumulation
drainage
HAND
rainfall-runoff
flood extent
```

## Phase 8 --- Exposure

```text
roads
bridges
population
settlements
buildings
critical infrastructure
```

## Phase 9 --- ML

```text
large validated inventory
PU -> supervised ML
spatial CV
temporal holdout
cross-district testing
```

## Phase 10 --- Calibration

```text
Platt / isotonic / beta calibration
Brier
ECE
reliability
independent test
```

## Phase 11 --- Operations

```text
uncertainty
alerts
field verification
audit
monitoring
retraining
```

---

# 85. Final Technical Architecture

The complete target architecture is:

```text
                           SATELLITES
                              |
        +---------------------+----------------------+
        |                     |                      |
       GPM                   SMAP                Sentinel-1
        |                     |                      |
    Rainfall             Soil moisture        SAR / flood / deformation
        |                     |                      |
        +---------------------+----------------------+
                              |
                         Sentinel-2
                              |
                    Vegetation / land cover
                              |
        +---------------------+----------------------+
        |                     |                      |
       SRTM                   GSI                  GIS
        |                     |                      |
      Terrain             Geology              Roads / population
        |                geomorphology          infrastructure
        |                     |                      |
        +---------------------+----------------------+
                              |
                     Historical Inventory
                              |
                     Field Verification
                              |
                              v
                    DATA QUALITY GATE
                              |
                              v
                    FEATURE ENGINEERING
                              |
                +-------------+-------------+
                |                           |
                v                           v
        STATIC SUSCEPTIBILITY        DYNAMIC TRIGGERS
                |                           |
                +-------------+-------------+
                              |
                              v
                       HAZARD MODEL
                              |
                              v
                 CALIBRATION / UNCERTAINTY
                              |
                              v
                      EXPOSURE MODEL
                              |
                              v
                   OPERATIONAL PRIORITY
                              |
             +----------------+----------------+
             |                |                |
             v                v                v
            GIS             ALERTS          FIELD APP
             |                |                |
             +----------------+----------------+
                              |
                              v
                       VERIFIED EVENTS
                              |
                              v
                     MODEL LEARNING LOOP
```

---

# 86. Reference Data Products and Documentation

## NASA GPM

IMERG documentation:

https://gpm.nasa.gov/data/imerg

GPM data directory:

https://gpm.nasa.gov/data/directory

IMERG technical documentation:

https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation

## NASA SMAP / NSIDC

SMAP SPL3SMP_E Version 6:

https://nsidc.org/data/spl3smp_e/versions/6

NASA Earthdata Login:

https://urs.earthdata.nasa.gov/

NASA Earthdata Search:

https://search.earthdata.nasa.gov/

## Sentinel-1

ESA Sentinel-1 mission:

https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Introducing_Sentinel-1

ESA Sentinel-1 instrument:

https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Instrument

## Sentinel-2

ESA Sentinel-2 facts:

https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/Facts_and_figures

## SRTM

USGS SRTM archive:

https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission

## Geological Survey of India

GSI landslide hazard resources:

https://bhusanket.gsi.gov.in/LS_hazard.html

GSI Bhusanket:

https://bhusanket.gsi.gov.in/

## OpenStreetMap

OSM licensing/use:

https://wiki.openstreetmap.org/wiki/License/Use_Cases

## IMD / MAUSAM

Indian rainfall dataset reference:

https://mausamjournal.imd.gov.in/index.php/MAUSAM/article/view/851

---

# 87. One-Line Technical Summary

> **SARVAS is a multi-source spatiotemporal geospatial system that
> combines NASA GPM rainfall, NASA SMAP soil moisture, SRTM terrain,
> Sentinel-1 SAR, Sentinel-2 vegetation, geological and hydrological
> layers, historical landslides, field verification, and exposure data
> to estimate dynamic landslide and flash-flood hazard, prioritize
> affected assets, and support near-real-time disaster warnings.**

---

# 88. Key Engineering Principle

The final system should evolve as:

```text
DATA
  ->
QUALITY
  ->
FEATURES
  ->
SUSCEPTIBILITY
  ->
DYNAMIC TRIGGERS
  ->
HAZARD
  ->
CALIBRATED PROBABILITY
  ->
UNCERTAINTY
  ->
EXPOSURE
  ->
PRIORITY
  ->
VERIFICATION
  ->
ALERT
  ->
OBSERVED EVENT
  ->
LEARNING
```

This is the complete A-to-Z technical path from the current SIH
prototype to a scientifically defensible, calibrated, scalable regional
disaster-intelligence platform.
