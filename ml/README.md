# Machine Learning (`ml/`)

## 1. Overview
The `ml/` directory contains pipelines, scripts, and model specifications for **Landslide Susceptibility Mapping (LSM)** and rainfall-triggered dynamic risk assessment in the pilot districts: **Kohima (Nagaland)** and **Aizawl (Mizoram)**.

## 2. Guiding Principles & Anti-Fabrication Rules
- **No Fabricated Data**: Models must be trained exclusively on verified historical landslide inventories (e.g., GSI Bhukosh, state disaster management records) and legitimate environmental rasters (CartoDEM/SRTM, IMD).
- **No Fake "AI" Accuracy Claims**: Metric reporting (ROC-AUC, F1-score, Precision, Recall) must reflect actual cross-validation on spatial holdout sets. Spatial autocorrelation leakage must be mitigated using spatial block cross-validation.
- **Explainability**: Models must output verifiable feature contributions (e.g., slope angle, aspect, distance to drainage, rainfall intensity) rather than black-box guesses.

## 3. Technology Stack
- **Languages & Frameworks**: Python 3.11+, scikit-learn, XGBoost
- **Data Wrangling**: Pandas, NumPy
- **Spatial Processing**: Rasterio, GeoPandas, GDAL

## 4. Modeling Approach
1. **Static Susceptibility (LSM)**:
   - Uses conditioning factors: Slope, Aspect, Elevation, Curvature, Topographic Wetness Index (TWI), Distance to Roads, Distance to Streams, Land Use / Land Cover (LULC), and Lithology/Soil type.
   - Algorithms: XGBoost Classifier, Random Forest (scikit-learn).
   - Target: Binary classification (landslide occurrence vs. non-landslide points).
2. **Dynamic Risk Assessment**:
   - Integrates static susceptibility with antecedent rainfall and current precipitation thresholds (e.g., empirical rainfall intensity-duration curves or cumulative 3-day rainfall triggers).

## 5. Directory Structure
```text
ml/
├── README.md                 # This file
├── requirements-ml.txt       # ML specific dependencies (xgboost, scikit-learn, rasterio)
├── notebooks/                # Jupyter exploratory analysis and factor correlation checks
├── src/
│   ├── dataset.py            # Sampling points & raster value extraction
│   ├── features.py           # Feature engineering & normalization
│   ├── train.py              # Model training and spatial cross-validation
│   ├── evaluate.py           # Real metric calculations (ROC-AUC, confusion matrix)
│   └── inference.py          # Susceptibility inference for new points or grid cells
└── saved_models/             # Exported model weights/artifacts (.joblib, .json)
```

## 6. Current Status
- **Pending Model Training**: Waiting for validated ground-truth inventory and processed DEM rasters for Kohima and Aizawl before running training pipelines.
