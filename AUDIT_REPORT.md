# SARVAS / NER Safe — Implementation Audit

**Scope:** Compares `PRD.md` ("SARVAS — Technical Approach", identical content to `Sarvas Technical Approach.pdf`) against the actual state of `backend/`, `frontend/`, `data/`, `ml/`, `scripts/`, and `documentation/` as of 2026-09-20 (single commit: `77d8fb6`).

**Headline finding:** this is well past a typical hackathon skeleton. The 500m grid (6,055 Kohima + 10,906 Aizawl = 16,961 cells), the historical inventory (11 verified events), and the ingestion scripts for GPM/SMAP/Sentinel-1 all match the PRD's numbers and anti-fabrication rules exactly. The core blocker is external: **NASA Earthdata / ASF authentication is not resolved**, so all three dynamic satellite feeds are stale/blocked, which cascades into the risk engine, the ML layer, and several frontend panels all reporting "unavailable" by design rather than by bug. Separately, several frontend UI paths (Alerts/Reports/About/Login, exposure data, flood) are visual stubs with no backend behind them yet.

---

## 1. Scorecard

| Layer | Component | Status |
|---|---|---|
| Data | 500m grid (Kohima+Aizawl) | ✅ Done — exact PRD cell counts |
| Data | District boundaries | ✅ Done — real GeoJSON, WGS84 |
| Data | Historical landslide inventory | 🟡 Partial — 19 events/11 verified, but missing `landslide_type`/`trigger`/`confidence` fields from spec schema |
| Data | SRTM terrain derivatives | 🟡 Partial — DEM/slope/aspect/curvature/TWI rasters exist; no relief/flow-accumulation/HAND/TPI as standalone rasters |
| Data | NASA GPM rainfall | 🟡 Blocked — real pipeline, but only one stale all-zero snapshot, no live feed |
| Data | NASA SMAP soil moisture | 🟡 Blocked — real parsed granule exists but flagged STALE, no live feed |
| Data | Sentinel-1 SAR | 🔴 Not ingested — catalog only (dry-run), 0 of 500 granules downloaded |
| Data | Sentinel-2 vegetation/NDVI | 🔴 Not present anywhere in the stack |
| Data | Geology/geomorphology/soil layers | 🔴 Not present |
| Data | Roads/population/infrastructure exposure | 🔴 Not present |
| ML | Static susceptibility (TSI) | ✅ Done — heuristic weighted formula, honestly labeled "not ML-learned" |
| ML | PU-learning / similarity | 🟡 Partial — distance-metric baseline exists, not a trained classifier |
| ML | Supervised model (XGBoost/LightGBM) | 🔴 Not started — `ml/` has only a README describing the target structure |
| ML | Calibration / uncertainty | 🔴 Not started (correctly reports `NOT_CALIBRATED`) |
| Backend | Core REST API | ✅ Done — 18/19 spec endpoints implemented |
| Backend | Dynamic risk engine | ✅ Done as code, but dead-in-practice (needs both rainfall+soil-moisture live to fire) |
| Backend | Alerts workflow + CAP structure | ✅ Done — generation, verification, ack, expiry, CAP-shaped payload |
| Backend | Database (PostgreSQL/PostGIS) | 🔴 Not present — flat CSV/GeoJSON + in-memory dict only |
| Backend | Flood endpoint/logic | 🔴 Stub — `NOT_YET_IMPLEMENTED` everywhere |
| Backend | Data quality enum | 🟡 Partial — statuses used as free strings, no shared enum, no INVALID/PARTIAL |
| Frontend | Landing page | 🟡 Mostly matches DESIGN.md — 4 small text/content deviations |
| Frontend | Risk map (MapLibre) | ✅ Done — real satellite/dark basemaps, real grid+boundary+historical layers |
| Frontend | Area/cell risk dashboards | 🟡 Partial — terrain/historical/AI-prediction live; exposure/SAR/flood 100% hardcoded "Unavailable" |
| Frontend | Cross-district search | ✅ Done (map toolbar) / 🟡 Weak (landing-page search only string-matches "aizawl") |
| Frontend | Alerts/Reports/About/Login/Signup pages | 🔴 Dead nav stubs (no router at all) |
| Frontend | Tests | 🔴 None |
| Cross-cutting | Reproducibility (versioning, model artifacts) | 🔴 Not present |
| Cross-cutting | Scientific-integrity rules (PRD §82) | ✅ Followed — no zero-fill, no fake probabilities, no fabricated SAR/NDVI claims found anywhere |

---

## 2. What's genuinely done well

- **Grid and boundaries are real and exact.** `kohima_grid_500m.geojson` (6,055 features) and `aizawl_grid_500m.geojson` (10,906 features) match PRD §3.3 precisely; district polygons are real single-feature GeoJSON in WGS84.
- **Anti-fabrication discipline is real, not aspirational.** `scripts/ingest_gpm_rainfall.py` and `ingest_smap_soil_moisture.py` explicitly refuse to zero-fill missing values and flag `REQUIRES_EXTERNAL_AUTH`/`STALE` instead (PRD §16.2, §73). The backend risk engine (`risk_engine.py`) mirrors this: it will not compute a combined score unless both rainfall and soil moisture are actually available, and returns `DYNAMIC_RISK_UNAVAILABLE` rather than guessing. No `random.uniform()`/fabricated sensor values were found anywhere in `app/` or `scripts/`.
- **Historical inventory is real**, not synthetic: 19 named events (Dzudza Bridge NH-29, Kisama Heritage Village, etc.) with cited sources (NSDMA, MSDMA, GSI, PIB), 11 of them coordinate-verified — this is the figure the screenshot's "11 Verified" badge reflects.
- **The dynamic hazard formula matches PRD §19–22 exactly**: rainfall 45% / soil moisture 35% / flood 10% / SAR 5% / verification 5% for the dynamic trigger, 50/50 static+dynamic combination, and Critical(≥80)/High(60-79.9)/Warning(45-59.9)/Watch(30-44.9)/Low(<30) thresholds — all implemented as documented "prototype policy weights," not misrepresented as ML output.
- **Alerts workflow is fully built**: generation → officer verify/reject/override → acknowledge → expire, with a CAP v1.2-shaped payload and honest `INTEGRATION_PENDING_AUTHORIZATION` status for telecom dissemination rather than a fake "sent" confirmation (PRD §48–50).
- **The map is a real, working MapLibre GL integration**, not a mockup — real satellite/dark-vector basemaps, real risk-colored 500m grid, real historical-event layer, real hover/click interactivity, real cross-district fly-to search.
- **76 backend tests** exercise the actual FastAPI app (not mocks) across districts, cells, areas, alerts, and the risk-engine math.

---

## 3. Gaps, by layer

### 3.1 Data pipeline (blocks nearly everything downstream)

1. **NASA Earthdata / ASF authentication is unresolved.** `scratch/diagnose_403.py`, `test_one_granule.py`, `test_one_smap_granule.py` are live evidence of a 403 the team hit and hasn't cleared. Until this is fixed, GPM stays a single stale zero-rainfall snapshot, SMAP stays STALE, and Sentinel-1 stays at "catalog only, 0 of 500 granules downloaded." **This is the single highest-leverage fix** — it unblocks the risk engine, the ML feature table, and multiple frontend panels simultaneously.
2. **Sentinel-2 (vegetation/NDVI) is entirely absent** — no script, no schema field, no route. PRD §12 treats this as a full pipeline stage (Phase 5 in §84); currently 0% started.
3. **Geology, geomorphology, and soil property layers are absent** (PRD §9–11). No GSI/authoritative data has been sourced. This directly weakens the static susceptibility (TSI) formula, which currently only has slope/TWI/curvature/relief/historical-evidence terms populated — geology/geomorphology/soil/landcover weights in the PRD's TSI formula (§17) have no real input.
4. **No exposure data at all** — roads, population, settlements, critical infrastructure (PRD §39–43) don't exist anywhere in `data/`. This is why every frontend "Exposure" panel is a hardcoded "Unavailable — GIS layer pending integration" with no fetch even attempted.
5. **Historical event schema is thinner than spec**: missing `landslide_type`, `trigger`, `confidence` fields (PRD §14.2). Only the VERIFIED/NEEDS_VERIFICATION/MISSING tri-state exists as a rough proxy.
6. **Terrain derivatives are incomplete**: DEM/slope/aspect/curvature/TWI exist as rasters; relief and TPI exist only as CSV scalar columns; flow accumulation and HAND (needed for the entire flash-flood module, PRD §30–37) don't exist in any form.
7. **Stale/aspirational documentation**: `data/historical/README.md`, `ml/README.md`, `scripts/README.md`, and `documentation/README.md` all describe files or states that don't match what's actually on disk (e.g., `documentation/README.md` lists 5 files that don't exist; `scripts/README.md`'s "Planned Scripts" table omits the 31 scripts that actually exist). Low cost, high confusion risk for anyone onboarding.

### 3.2 ML

1. **No trained model exists.** `ml/` contains only a README describing a target `src/train.py`/`saved_models/` layout that hasn't been built. The only "model" in production is the heuristic TSI + PU-similarity baseline in `scripts/build_baseline_susceptibility.py`, which is honestly self-documented as non-ML.
2. **This is arguably correct sequencing, not a bug**: with only 11 verified positives and 0 confirmed negatives, PRD §18 and §59-60 explicitly say a real supervised model shouldn't be trained yet. The gap is real but the PRD itself frames it as Phase 9 (§84), gated on training-data expansion — so the right framing for a reviewer is "not due yet," not "missing."
3. **No calibration, no uncertainty model** (PRD §24, §53) — correctly reported as `NOT_CALIBRATED` rather than faked, but functionally absent.
4. **No reproducibility artifacts** (PRD §72): no model version file, no feature-schema version, no hyperparameter record, no `.pkl`/`.joblib` artifacts anywhere. The self-generated audit JSONs (`model_readiness_audit.json` etc.) are QA reports, not a versioning system.

### 3.3 Backend

1. **No PostgreSQL/PostGIS** despite being named as the recommended database in PRD §65 and the tech stack in §67/#4 of README.md. All state is flat CSV/GeoJSON read into memory at startup, and alerts live in a plain Python dict — **restarting the server loses all alert history**. For a hackathon prototype this is a reasonable simplification, but it's a hard blocker for anything persistent/multi-instance.
2. **`GET /api/flood/latest` is missing entirely**, and flood logic is hardcoded to `NOT_YET_IMPLEMENTED` in both `data_service.py` and `risk_engine.py`. The entire flash-flood module (PRD §30-37) has zero backend implementation.
3. **The dynamic risk engine is currently dead-in-production**: `evaluate_cell_risk` requires both rainfall AND soil moisture to be `AVAILABLE` before it will compute anything, and per §3.1 above neither currently is live — so in the deployed state, every `/api/cells/{id}/risk` call returns `DYNAMIC_RISK_UNAVAILABLE`. The code is correct; it just has nothing to work with yet.
4. **Data-quality statuses aren't a shared enum** — they're duplicated string literals across `data_service.py`, `risk_engine.py`, and the ingestion scripts, with some drift (e.g., backend uses `REQUIRES_EXTERNAL_AUTH` while scripts use `REQUIRES_AUTH`; no `INVALID`/`PARTIAL` status is ever produced by the backend, only by the ingestion scripts). Low risk today, but will bite once more statuses are wired through.
5. **A few hardcoded scalars masquerade as computed stats**: `verified_positive_cells: 11` is hardcoded independently in two files (`data_service.py` and `model_calibration_service.py`) rather than derived from the historical CSV at request time — a silent drift risk if the inventory grows. `data_completeness_score: 0.28` in `ml_model_service.py` is also a hardcoded literal rather than computed (contrast with `risk_engine.py`, which does compute completeness dynamically).
6. **`backend/requirements.txt` doesn't declare `h5py`/`earthaccess`/`rasterio`**, yet `backend/tests/test_gpm_ingestion.py` imports `h5py` and reaches into the root-level `scripts/` package — this test doesn't actually exercise `backend/app` and will fail/skip in any clean backend-only install.
7. **No `.env.example`** documenting the `EARTHDATA_TOKEN`/`EARTHDATA_USERNAME`/`EARTHDATA_PASSWORD` variables the ingestion scripts need — anyone picking this up cold has to read script source to know what to set.

### 3.4 Frontend

1. **No router — Alerts, Reports, About, Login, and Sign Up are dead stubs.** `App.jsx` only toggles between two views (Landing, RiskMap) via local state; nav clicks for the other four items do nothing, and Login/Sign Up buttons have no `onClick` at all. The real `AlertPanel` component is fully built but only reachable as a slide-in panel *inside* the risk map, not as its own page.
2. **Landing page has 3-4 literal deviations from DESIGN.md**, which explicitly says not to redesign it:
   - Motto renders `Predict • Monitor • Protect` (bullet) instead of the spec's required `Predict . Monitor . Protect` (periods) — DESIGN.md explicitly calls out "do not replace periods with arrows," and a bullet is the same category of change.
   - Safety strip text is `Your safety is our priority.` instead of the spec's exact `Your safety our priority`.
   - Quick Access uses heading "Nearby Healthcare & Police Stations" / link text "View List" instead of the spec's `Quick Access:` / `List`.
   - An extra stat strip (`8 States`, `Real-time Data`, `AI Prediction`, `Community Driven`) was added under Report-an-Incident — DESIGN.md §25 explicitly forbids "Extra statistics."
3. **Exposure, SAR, and flood panels in the cell/area dashboards are 100% hardcoded placeholder text** with no fetch attempted at all (not even a failing one) — e.g., "Citizen Reports: 0 filed" is a literal `0` in JSX, not a field from any API response. This matches the backend gap in §3.3.2/3.1.4 above; frontend and backend are consistently missing the same data, which is good (no invented mismatch), but means these sections are pure visual scaffolding today.
4. **`AreaRiskDashboard`'s "Dynamic Real-Time Sensors" block is hardcoded narrative text** (e.g., a literal string "AVAILABLE — Real NASA GPM data (2026-09-18...)" baked into JSX) rather than being data-bound to the actual API response — this one is a real inconsistency worth fixing since it currently could show stale/wrong text regardless of what the backend returns.
5. **Only 3 of the ~8 map layers implied by the reference screenshot are real map layers** — grid, boundary, and historical events. Rainfall, soil moisture, roads, and infrastructure appear only as text in side panels, not as MapLibre layers (consistent with those data sources not existing yet — see §3.1.4).
6. **No shared API client** — five components each duplicate their own `fetch()` + host-fallback array; `AlertPanel.jsx` diverges further by hardcoding `API_BASE = 'http://localhost:8000'` with no `VITE_API_URL` fallback, unlike the other four. Minor but will cause confusing behavior differences across environments.
7. **Landing-page location search is much weaker than the map's search**: it only checks whether the query string contains `"aizawl"` to decide which district to route to, rather than calling `/api/areas` like the in-map search does — so it cannot resolve most locality names typed on the landing page.
8. **Zero frontend tests**, no CI config.
9. **Minor cleanup**: unused Vite/CRA boilerplate (`App.css`, `react.svg`, `vite.svg`, `hero.png`, `public/icons.svg`), stock unedited `frontend/README.md`.

---

## 4. Suggested priority order to move toward a working demo

This follows the PRD's own Phase sequence (§84) crossed with what's actually blocking the most downstream work right now:

1. **Resolve NASA Earthdata / ASF authentication.** Everything else — live rainfall, live soil moisture, a non-dead risk engine, real alerts, real map risk colors that change over time — depends on this one unblock. The diagnostic scripts in `scratch/` already narrowed this down to a 403 on the auth redirect chain.
2. **Wire the dynamic risk engine end-to-end once #1 lands**, and confirm `/api/cells/{id}/risk` actually returns computed scores instead of `DYNAMIC_RISK_UNAVAILABLE`.
3. **Add basic routing (React Router or equivalent) and give Alerts its own real page** — the component already exists, it just needs to stop being trapped inside the map's slide-over panel, and Reports/About need at least placeholder pages instead of dead nav links.
4. **Fix the landing-page content deviations from DESIGN.md** (motto punctuation, safety-strip text, Quick Access wording, remove the extra stat strip) — these are small, fast fixes that restore fidelity to a spec the project explicitly says not to deviate from.
5. **Source at least a minimal roads/population/infrastructure exposure layer** — even a small authoritative or OSM-derived dataset would let the Exposure panels move from "no fetch attempted" to "real data, possibly partial," which is more consistent with the project's own honesty standard than leaving them as static text.
6. **Fix `AreaRiskDashboard`'s hardcoded sensor-status text** to read from the actual API response — this is the one place where hardcoded text could plausibly mislead a viewer about current data freshness, which cuts against the project's own anti-fabrication principle.
7. **Only after real dynamic data is flowing and the historical inventory has grown past ~11 events**, begin the ML phase (PU→supervised, spatial/temporal CV, calibration) — starting this earlier would contradict the PRD's own stated methodology (§18, §59-61).

---

## 5. Scientific-integrity check (PRD §82)

Spot-checked against the 13 explicit "must never" rules in PRD §82. No violations found in `backend/app`, `scripts/`, or `frontend/src`:
- No claim of 500m native GPM/SMAP resolution.
- No stale-as-live misrepresentation — freshness/staleness is surfaced everywhere it's checked.
- No zero-fill for missing rainfall/SMAP/SAR.
- No unknown-cells-as-negatives labeling.
- No uncalibrated score presented as a probability (`probability: null` / `NOT_CALIBRATED` used consistently).
- No SAR-change-as-landslide or NDVI-as-landslide claims (Sentinel-2 isn't even wired up yet, so this can't currently be violated).
- No flood-depth claims without a hydraulic basis (flood is simply `NOT_YET_IMPLEMENTED`).
- No fabricated model-accuracy claims — `NOT_COMPUTABLE_INSUFFICIENT_VERIFIED_LABELS` is used instead.
- No Cell Broadcast delivery claims — telecom gateway status correctly reports `INTEGRATION_PENDING_AUTHORIZATION`.

The one item worth flagging under this same spirit is the hardcoded "AVAILABLE — Real NASA GPM data..." text block in `AreaRiskDashboard.jsx` (§3.4.4) — not a fabrication today, but a piece of static text that could silently go stale or wrong once live data starts flowing, which is exactly the failure mode this project has otherwise been careful to design against.
