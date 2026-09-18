# NER Safe - Landslide Early Warning Backend API (FastAPI)

## 1. Overview
The `backend/` package houses the Python FastAPI web service and data access layer for **NER Safe** (SIH 2026). It serves the 500m geographic analysis grid, baseline terrain susceptibility (TSI), verified historical landslide records, and transparent status for dynamic meteorological and satellite feeds.

> **Important Prototype Notice:** This service is an SIH prototype data layer. No trained dynamic ML risk model currently exists. The static baseline susceptibility is deterministic terrain morphometry and PU learning similarity derived from SRTM 30m DEM.

---

## 2. Directory Structure
```text
backend/
├── app/
│   ├── __init__.py           # Package version
│   ├── main.py               # FastAPI application entrypoint & lifespan
│   ├── config.py             # Project-relative paths & district metadata
│   ├── schemas/              # Pydantic v2 validation models
│   │   ├── __init__.py
│   │   ├── common.py         # HealthResponse, ErrorResponse
│   │   ├── district.py       # DistrictSummary, DistrictRiskResponse
│   │   ├── cell.py           # CellSummary, CellParametersResponse
│   │   ├── observations.py   # Dynamic observation models (GPM, SMAP, SAR)
│   │   └── model.py          # ModelMetadata, ModelMetrics
│   ├── routes/               # API route handlers
│   │   ├── __init__.py       # Router aggregator
│   │   ├── health.py         # GET /api/health
│   │   ├── districts.py      # GET /api/districts, /grid, /risk
│   │   ├── cells.py          # GET /api/cells/{cell_id}, /parameters
│   │   ├── observations.py   # GET /api/rainfall, /soil-moisture, /satellite
│   │   └── model.py          # GET /api/model/metadata, /metrics
│   └── services/
│       ├── __init__.py
│       └── data_service.py   # In-memory cached dataset service
├── tests/                    # Pytest test suite (17 tests)
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_districts.py
│   ├── test_cells.py
│   ├── test_observations.py
│   └── test_model.py
├── requirements.txt          # Python dependencies
└── README.md                 # This documentation
```

---

## 3. Installation & Setup

### Requirements
- Python 3.11+ (Tested on Python 3.13)
- Dependencies in `requirements.txt`:
  - `fastapi>=0.110.0`
  - `uvicorn[standard]>=0.28.0`
  - `pydantic>=2.6.0`
  - `pandas>=2.0.0`
  - `pytest>=8.0.0`
  - `httpx>=0.27.0`

### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Start Development Server
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Interactive OpenAPI documentation will be accessible at:
- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

### Run Backend Tests
```bash
cd backend
python -m pytest -v
```

---

## 4. Implemented API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service overview & documentation links |
| `GET` | `/api/health` | Health check endpoint (`status: "ok"`) |
| `GET` | `/api/districts` | Pilot districts summary: Kohima (6,055) & Aizawl (10,906) |
| `GET` | `/api/districts/{district}/grid` | 500m analysis grid in standard GeoJSON |
| `GET` | `/api/districts/{district}/risk` | Baseline terrain susceptibility (TSI) for all district cells |
| `GET` | `/api/cells/{cell_id}` | Detailed terrain, baseline, and historical incident data for a cell |
| `GET` | `/api/cells/{cell_id}/parameters` | Multi-source structured parameters across all 7 layers |
| `GET` | `/api/cells/{cell_id}/risk` | Transparent dynamic landslide risk assessment with explainable evidence |
| `GET` | `/api/rainfall/latest` | GPM IMERG precipitation observations (`REQUIRES_EXTERNAL_AUTH`) |
| `GET` | `/api/soil-moisture/latest` | SMAP 9km soil moisture observations (`REQUIRES_EXTERNAL_AUTH`) |
| `GET` | `/api/satellite/latest` | Sentinel-1 C-SAR change observations (`REQUIRES_EXTERNAL_AUTH`) |
| `GET` | `/api/model/metadata` | AI/ML readiness metadata (`model_status: "NOT_TRAINED"`) |
| `GET` | `/api/model/metrics` | Model evaluation metrics (`status: "NOT_AVAILABLE"`) |

---

## 5. Conceptual Separation & Data Integrity

The backend strictly maintains the following architectural separation:

```
STATIC / BASELINE:
SRTM 30m DEM Morphometry + GSI Verified Historical Landslides
      ↓
Baseline Terrain Susceptibility Index (TSI) [AVAILABLE]

DYNAMIC TRIGGERS:
NASA GPM Rainfall + NASA SMAP Soil Moisture + Copernicus Sentinel-1 SAR
      ↓
[REQUIRES_EXTERNAL_AUTH — No placeholder or fabricated values]

FUTURE DYNAMIC RISK ENGINE:
[NOT_READY / NOT_TRAINED — To be implemented in subsequent phases]
```

### Truthful Status Handling
- **GPM Rainfall:** Returns `data_status: "REQUIRES_EXTERNAL_AUTH"`, all measurements `null`.
- **SMAP Soil Moisture:** Returns `data_status: "REQUIRES_EXTERNAL_AUTH"`, all measurements `null`.
- **Sentinel-1 SAR:** Returns `data_status: "REQUIRES_EXTERNAL_AUTH"`, all change dB values `null`.
- **Flood / Exposure:** Returns `status: "NOT_YET_IMPLEMENTED"`.
- **Model Evaluation:** Returns `status: "NOT_AVAILABLE"`, `metrics_available: false`.

---

## 6. Security & Credential Rules
- **No secrets in repository:** No NASA Earthdata credentials, Copernicus API keys, or tokens are committed or exposed through API endpoints.
- **Future Credentials:** External ingestors will read credentials strictly from local environment variables or secure key vaults.
- **CORS:** Restricted to local frontend development origins (`localhost:5173`, `localhost:4173`).
