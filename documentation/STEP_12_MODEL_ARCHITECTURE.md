# STEP 12 — MODEL ARCHITECTURE & FLOWCHART

## Data Flow & Processing Pipeline

```
Historical Landslides (GSI Verified 11 Cells)
                   +
Copernicus / SRTM 30m DEM Morphometry
                   ↓
   [Stage A: Static TSI Susceptibility]
                   ↓
GPM IMERG Rainfall ─────────────┐
SMAP Soil Moisture ─────────────┤
Sentinel-1 SAR Change ──────────┼──→ [Stage B: Dynamic Trigger Engine]
Flood Inundation ───────────────┤
Officer Verification ───────────┘
                   ↓
         [Hazard Model Engine]
                   ↓
      [Calibration Readiness Gate]
                   ↓
     [Calibrated Hazard Probability]
                   ↓
   [Exposure & Impact Score Filter]
                   ↓
     [Operational Risk Level (5-Class)]
                   ↓
        [Multi-Level Early Warning]
```

## Modular Components
1. **Model Audit**: `scripts/audit_model_readiness.py` → `data/ml/model_readiness_audit.json`
2. **Feature Builder**: `scripts/build_ml_dataset.py` → `data/ml/feature_dataset.csv`
3. **Evaluation Engine**: `scripts/evaluate_risk_model.py` → `data/ml/model_metrics.json`
4. **Model Services**: `backend/app/services/ml_model_service.py` & `model_calibration_service.py`
5. **API Router**: `backend/app/routes/model.py`
6. **Frontend UI**: `CellDetailsModal.jsx` & `AreaRiskDashboard.jsx`
