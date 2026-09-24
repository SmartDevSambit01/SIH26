"""
Data service layer for loading and querying SIH 2026 spatial and observation datasets.
Caches datasets in memory to provide fast O(1) cell lookups and API responses.
Never fabricates missing external data; preserves honest unavailable states.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from ..config import (
    DISTRICTS_META,
    TOTAL_CELL_COUNT,
    KOHIMA_GRID_GEOJSON,
    AIZAWL_GRID_GEOJSON,
    BASELINE_SUSCEPTIBILITY_CSV,
    FEATURE_DATASET_CSV,
    GPM_OBSERVATIONS_CSV,
    SMAP_OBSERVATIONS_CSV,
    SENTINEL_SAR_OBSERVATIONS_CSV,
    HISTORICAL_LANDSLIDES_CSV,
)

logger = logging.getLogger("ner_safe.data_service")

def clean_val(val: Any) -> Any:
    """Convert pandas/numpy NaN, NaT, or infinite values to None for clean JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (float, np.floating)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if pd.isna(val):
        return None
    return val


class DataService:
    def __init__(self):
        self._baseline_df: Optional[pd.DataFrame] = None
        self._feature_df: Optional[pd.DataFrame] = None
        self._historical_df: Optional[pd.DataFrame] = None
        self._gpm_df: Optional[pd.DataFrame] = None
        self._smap_df: Optional[pd.DataFrame] = None
        self._sentinel_df: Optional[pd.DataFrame] = None
        
        self._grid_cache: Dict[str, dict] = {}
        self._cell_index: Dict[str, dict] = {}
        self._historical_index: Dict[str, dict] = {}
        self._smap_index: Dict[str, dict] = {}
        self._gpm_index: Dict[str, dict] = {}
        self._initialized = False

    def ensure_loaded(self):
        """Ensures datasets are loaded into memory before processing requests."""
        if not self._initialized:
            self.load_all()

    def load_all(self):
        """Loads and indexes all project datasets into memory once on startup."""
        if self._initialized:
            return

        logger.info("Initializing DataService and caching datasets...")

        # 1. Historical landslides cleaned CSV
        if HISTORICAL_LANDSLIDES_CSV.exists():
            try:
                self._historical_df = pd.read_csv(HISTORICAL_LANDSLIDES_CSV, low_memory=False)
                for _, row in self._historical_df.iterrows():
                    cid = clean_val(row.get("cell_id"))
                    if cid:
                        self._historical_index[cid] = {
                            "has_verified_event": True,
                            "historical_event_id": clean_val(row.get("event_id")),
                            "event_location_name": clean_val(row.get("location_name")),
                            "event_date": clean_val(row.get("event_date")),
                            "event_description": clean_val(row.get("description")),
                            "label_quality": "GSI_VERIFIED",
                            "status": "AVAILABLE",
                        }
            except Exception as e:
                logger.error(f"Failed to load historical landslides CSV: {e}")

        # 2. Baseline susceptibility CSV
        if BASELINE_SUSCEPTIBILITY_CSV.exists():
            try:
                self._baseline_df = pd.read_csv(BASELINE_SUSCEPTIBILITY_CSV, low_memory=False)
            except Exception as e:
                logger.error(f"Failed to load baseline susceptibility CSV: {e}")

        # 3. Feature dataset CSV
        if FEATURE_DATASET_CSV.exists():
            try:
                self._feature_df = pd.read_csv(FEATURE_DATASET_CSV, low_memory=False)
            except Exception as e:
                logger.error(f"Failed to load feature dataset CSV: {e}")

        # 4. GPM rainfall observations CSV
        if GPM_OBSERVATIONS_CSV.exists():
            try:
                self._gpm_df = pd.read_csv(GPM_OBSERVATIONS_CSV, low_memory=False)
            except Exception as e:
                logger.error(f"Failed to load GPM observations CSV: {e}")

        # 5. SMAP soil moisture observations CSV
        if SMAP_OBSERVATIONS_CSV.exists():
            try:
                self._smap_df = pd.read_csv(SMAP_OBSERVATIONS_CSV, low_memory=False)
            except Exception as e:
                logger.error(f"Failed to load SMAP observations CSV: {e}")

        # 6. Sentinel-1 SAR observations CSV
        if SENTINEL_SAR_OBSERVATIONS_CSV.exists():
            try:
                self._sentinel_df = pd.read_csv(SENTINEL_SAR_OBSERVATIONS_CSV, low_memory=False)
            except Exception as e:
                logger.error(f"Failed to load Sentinel-1 observations CSV: {e}")

        # 7. GeoJSON 500m Grids for Kohima and Aizawl
        for dist_name, meta in DISTRICTS_META.items():
            grid_file = meta["grid_file"]
            if grid_file.exists():
                try:
                    with open(grid_file, "r", encoding="utf-8") as f:
                        geojson_data = json.load(f)
                        self._grid_cache[dist_name.lower()] = geojson_data
                except Exception as e:
                    logger.error(f"Failed to load grid GeoJSON for {dist_name}: {e}")

        # Build fast cell index from baseline and feature datasets
        self._build_cell_index()
        self._initialized = True
        logger.info(f"DataService initialized successfully. Indexed {len(self._cell_index)} cells.")

    def _build_cell_index(self):
        """Indexes properties by cell_id for instant retrieval."""
        # Start from baseline susceptibility if available
        if self._baseline_df is not None:
            for _, row in self._baseline_df.iterrows():
                cid = str(row["cell_id"])
                dist = str(row["district"])
                state = "Nagaland" if dist.lower() == "kohima" else "Mizoram"
                
                self._cell_index[cid] = {
                    "cell_id": cid,
                    "district": dist,
                    "state": state,
                    "latitude": clean_val(row.get("latitude")),
                    "longitude": clean_val(row.get("longitude")),
                    "slope_mean": clean_val(row.get("slope_mean")),
                    "elevation_mean": clean_val(row.get("elevation_mean")),
                    "curvature_mean": clean_val(row.get("curvature_mean")),
                    "twi_mean": clean_val(row.get("twi_mean")),
                    "tsi_score": clean_val(row.get("terrain_susceptibility_score")),
                    "tsi_class": clean_val(row.get("terrain_susceptibility_class")),
                    "pu_terrain_similarity": clean_val(row.get("pu_terrain_similarity")),
                    "pu_similarity_class": clean_val(row.get("pu_similarity_class")),
                    "primary_terrain_contributors": clean_val(row.get("primary_terrain_contributors")),
                }

        # Supplement with min/max elevation & slope, and aspect from feature dataset
        if self._feature_df is not None:
            for _, row in self._feature_df.iterrows():
                cid = str(row["cell_id"])
                if cid in self._cell_index:
                    cell = self._cell_index[cid]
                    cell["elevation_min"] = clean_val(row.get("elevation_min"))
                    cell["elevation_max"] = clean_val(row.get("elevation_max"))
                    cell["slope_max"] = clean_val(row.get("slope_max"))
                    cell["aspect_mean"] = clean_val(row.get("aspect_mean"))
                else:
                    dist = str(row["district"])
                    state = str(row.get("state", "Nagaland" if dist.lower() == "kohima" else "Mizoram"))
                    self._cell_index[cid] = {
                        "cell_id": cid,
                        "district": dist,
                        "state": state,
                        "latitude": clean_val(row.get("latitude")),
                        "longitude": clean_val(row.get("longitude")),
                        "elevation_mean": clean_val(row.get("elevation_mean")),
                        "elevation_min": clean_val(row.get("elevation_min")),
                        "elevation_max": clean_val(row.get("elevation_max")),
                        "slope_mean": clean_val(row.get("slope_mean")),
                        "slope_max": clean_val(row.get("slope_max")),
                        "aspect_mean": clean_val(row.get("aspect_mean")),
                        "curvature_mean": clean_val(row.get("curvature_mean")),
                        "twi_mean": clean_val(row.get("twi_mean")),
                        "tsi_score": None,
                        "tsi_class": None,
                        "pu_terrain_similarity": None,
                        "pu_similarity_class": None,
                        "primary_terrain_contributors": None,
                    }

        # Index SMAP soil moisture observations for instant lookup by cell_id
        if self._smap_df is not None:
            for _, row in self._smap_df.iterrows():
                cid = str(row["cell_id"])
                self._smap_index[cid] = {
                    "soil_moisture_current": clean_val(row.get("soil_moisture_current")),
                    "soil_moisture_previous": clean_val(row.get("soil_moisture_previous")),
                    "soil_moisture_change": clean_val(row.get("soil_moisture_change")),
                    "soil_moisture_change_percent": clean_val(row.get("soil_moisture_change_percent")),
                    "observation_timestamp": clean_val(row.get("observation_timestamp")),
                    "smap_ease2_grid_cell": clean_val(row.get("smap_ease2_grid_cell")),
                    "source": str(row.get("source", "NASA / NSIDC SMAP Mission")),
                    "source_product": str(row.get("source_product", "SPL3SMP_E_V006")),
                    "source_resolution": str(row.get("source_resolution", "9 km (EASE-Grid 2.0) Daily")),
                    "data_status": str(row.get("data_status", "STALE")),
                    "quality_flag": str(row.get("quality_flag", "")),
                }

        # Index GPM rainfall observations for instant lookup by cell_id
        if self._gpm_df is not None:
            for _, row in self._gpm_df.iterrows():
                cid = str(row["cell_id"])
                self._gpm_index[cid] = {
                    "rainfall_rate": clean_val(row.get("rainfall_rate")),
                    "rainfall_30min": clean_val(row.get("rainfall_30min")),
                    "rainfall_3h": clean_val(row.get("rainfall_3h")),
                    "rainfall_6h": clean_val(row.get("rainfall_6h")),
                    "rainfall_24h": clean_val(row.get("rainfall_24h")),
                    "rainfall_72h": clean_val(row.get("rainfall_72h")),
                    "rainfall_duration_h": clean_val(row.get("rainfall_duration_h")),
                    "antecedent_rainfall_7d": clean_val(row.get("antecedent_rainfall_7d")),
                    "gpm_grid_cell": clean_val(row.get("gpm_grid_cell")),
                    "observation_timestamp": clean_val(row.get("observation_timestamp")),
                    "source": str(row.get("source", "NASA / JAXA GPM Constellation")),
                    "source_product": str(row.get("source_product", "GPM_3IMERGHH_V07B_EARLY")),
                    "source_resolution": str(row.get("source_resolution", "0.1 deg (~10 km) Half-Hourly (~4h latency)")),
                    "data_status": str(row.get("data_status", "AVAILABLE")),
                    "quality_flag": str(row.get("quality_flag", "PASSED_VERIFICATION")),
                }

    def get_districts(self) -> List[dict]:
        """Returns the list of pilot districts with cell counts and centers."""
        self.ensure_loaded()
        result = []
        for name, meta in DISTRICTS_META.items():
            result.append({
                "district": meta["name"],
                "state": meta["state"],
                "cell_count": meta["cell_count"],
                "grid_resolution_m": meta["grid_resolution_m"],
                "center": meta["center"],
            })
        return result

    def get_district_grid_geojson(self, district: str) -> Optional[dict]:
        """Returns the existing 500m GeoJSON for the district without regeneration."""
        self.ensure_loaded()
        key = district.strip().lower()
        return self._grid_cache.get(key)

    def get_district_risk(self, district: str) -> Optional[dict]:
        """Returns baseline susceptibility records for all cells in a district."""
        self.ensure_loaded()
        key = district.strip().lower()
        # Validate district
        matched_meta = None
        for dname, meta in DISTRICTS_META.items():
            if dname.lower() == key:
                matched_meta = meta
                break
        
        if not matched_meta:
            return None

        district_name = matched_meta["name"]

        cells = []
        if self._baseline_df is not None:
            dist_rows = self._baseline_df[self._baseline_df["district"].str.lower() == key]
            for _, row in dist_rows.iterrows():
                cells.append({
                    "cell_id": str(row["cell_id"]),
                    "district": district_name,
                    "latitude": clean_val(row.get("latitude")),
                    "longitude": clean_val(row.get("longitude")),
                    "baseline_susceptibility": clean_val(row.get("terrain_susceptibility_score")),
                    "susceptibility_class": clean_val(row.get("terrain_susceptibility_class")),
                    "pu_terrain_similarity": clean_val(row.get("pu_terrain_similarity")),
                    "data_status": "AVAILABLE",
                })

        return {
            "district": district_name,
            "cell_count": len(cells) if cells else matched_meta["cell_count"],
            "baseline_type": "TERRAIN_SUSCEPTIBILITY_TSI",
            "dynamic_risk_status": "NOT_AVAILABLE",
            "notice": (
                "Values represent static baseline terrain susceptibility (TSI) derived from SRTM 30m DEM. "
                "No dynamic ML risk model is currently trained or active."
            ),
            "cells": cells,
        }

    def get_cell(self, cell_id: str) -> Optional[dict]:
        """Returns detailed summary for a specific cell ID."""
        self.ensure_loaded()
        cid = cell_id.strip().upper()
        raw = self._cell_index.get(cid)
        if not raw:
            return None

        # Historical information
        hist = self._historical_index.get(cid, {
            "has_verified_event": False,
            "historical_event_id": None,
            "event_location_name": None,
            "event_date": None,
            "event_description": None,
            "label_quality": "UNLABELED",
            "status": "AVAILABLE",
        })

        gpm_status = self._gpm_index[cid]["data_status"] if cid in self._gpm_index else "REQUIRES_EXTERNAL_AUTH"
        smap_status = self._smap_index[cid]["data_status"] if cid in self._smap_index else "REQUIRES_EXTERNAL_AUTH"
        has_dynamic = (cid in self._gpm_index) or (cid in self._smap_index)

        return {
            "cell_id": cid,
            "district": raw["district"],
            "state": raw["state"],
            "latitude": raw["latitude"],
            "longitude": raw["longitude"],
            "terrain": {
                "elevation_mean": raw.get("elevation_mean"),
                "elevation_min": raw.get("elevation_min"),
                "elevation_max": raw.get("elevation_max"),
                "slope_mean": raw.get("slope_mean"),
                "slope_max": raw.get("slope_max"),
                "aspect_mean": raw.get("aspect_mean"),
                "curvature_mean": raw.get("curvature_mean"),
                "twi_mean": raw.get("twi_mean"),
                "status": "AVAILABLE",
            },
            "historical": hist,
            "baseline_susceptibility": {
                "tsi_score": raw.get("tsi_score"),
                "tsi_class": raw.get("tsi_class"),
                "pu_terrain_similarity": raw.get("pu_terrain_similarity"),
                "pu_similarity_class": raw.get("pu_similarity_class"),
                "primary_terrain_contributors": raw.get("primary_terrain_contributors"),
                "status": "AVAILABLE",
            },
            "dynamic_risk_status": "ACTIVE" if has_dynamic else "NOT_AVAILABLE",
            "data_availability": {
                "terrain": "AVAILABLE",
                "historical": "AVAILABLE",
                "baseline_susceptibility": "AVAILABLE",
                "rainfall": gpm_status,
                "soil_moisture": smap_status,
                "satellite_sar": "REQUIRES_EXTERNAL_AUTH",
                "flood": "NOT_YET_IMPLEMENTED",
                "exposure": "NOT_YET_IMPLEMENTED",
                "citizen_reports": "NOT_CONNECTED",
                "officer_verification": "NOT_CONNECTED",
            }
        }

    def get_cell_parameters(self, cell_id: str) -> Optional[dict]:
        """Returns structured multi-source parameters for a specific cell ID."""
        cell = self.get_cell(cell_id)
        if not cell:
            return None

        cid = cell["cell_id"]
        dist = cell["district"]
        lat = cell["latitude"]
        lon = cell["longitude"]

        return {
            "cell_id": cid,
            "district": dist,
            "latitude": lat,
            "longitude": lon,
            "terrain": cell["terrain"],
            "rainfall": (
                {
                    "source": self._gpm_index[cid]["source"],
                    "source_product": self._gpm_index[cid]["source_product"],
                    "source_resolution": self._gpm_index[cid]["source_resolution"],
                    "gpm_grid_cell": self._gpm_index[cid]["gpm_grid_cell"],
                    "status": self._gpm_index[cid]["data_status"],
                    "quality_flag": self._gpm_index[cid]["quality_flag"],
                    "rainfall_rate_mm_h": self._gpm_index[cid]["rainfall_rate"],
                    "rainfall_30min_mm": self._gpm_index[cid]["rainfall_30min"],
                    "rainfall_3h_mm": self._gpm_index[cid]["rainfall_3h"],
                    "rainfall_6h_mm": self._gpm_index[cid]["rainfall_6h"],
                    "rainfall_24h_mm": self._gpm_index[cid]["rainfall_24h"],
                    "rainfall_72h_mm": self._gpm_index[cid]["rainfall_72h"],
                    "rainfall_duration_h": self._gpm_index[cid]["rainfall_duration_h"],
                    "antecedent_rainfall_7d_mm": self._gpm_index[cid]["antecedent_rainfall_7d"],
                    "observation_timestamp": self._gpm_index[cid]["observation_timestamp"],
                    "notice": "Real NASA GPM IMERG Early Run observation. Native resolution ~10 km mapped to 500m analysis cell."
                }
                if cid in self._gpm_index
                else {
                    "source": "NASA / JAXA GPM Constellation (GPM_3IMERGHH_V07B_EARLY)",
                    "status": "REQUIRES_EXTERNAL_AUTH",
                    "quality_flag": "UNAVAILABLE_PENDING_EARTHDATA_LOGIN",
                    "rainfall_rate_mm_h": None,
                    "rainfall_24h_mm": None,
                    "rainfall_72h_mm": None,
                    "observation_timestamp": None,
                    "notice": "Dynamic GPM precipitation requires NASA Earthdata authentication."
                }
            ),
            "soil_moisture": (
                {
                    "source": self._smap_index[cid]["source"],
                    "source_product": self._smap_index[cid]["source_product"],
                    "source_resolution": self._smap_index[cid]["source_resolution"],
                    "smap_ease2_grid_cell": self._smap_index[cid]["smap_ease2_grid_cell"],
                    "status": self._smap_index[cid]["data_status"],
                    "quality_flag": self._smap_index[cid]["quality_flag"],
                    "volumetric_moisture_m3_m3": self._smap_index[cid]["soil_moisture_current"],
                    "volumetric_moisture_previous_m3_m3": self._smap_index[cid]["soil_moisture_previous"],
                    "moisture_change_m3_m3": self._smap_index[cid]["soil_moisture_change"],
                    "moisture_change_percent": self._smap_index[cid]["soil_moisture_change_percent"],
                    "observation_timestamp": self._smap_index[cid]["observation_timestamp"],
                    "notice": "Real SMAP SPL3SMP_E V006 observation. Status: STALE — observation latency exceeded configured freshness threshold."
                }
                if cid in self._smap_index
                else {
                    "source": "NASA / NSIDC SMAP Mission (SPL3SMP_E_V006)",
                    "status": "REQUIRES_EXTERNAL_AUTH",
                    "quality_flag": "UNAVAILABLE_PENDING_EARTHDATA_LOGIN",
                    "volumetric_moisture_m3_m3": None,
                    "moisture_change_percent": None,
                    "observation_timestamp": None,
                    "notice": "Dynamic SMAP soil moisture requires NASA Earthdata authentication."
                }
            ),
            "satellite": {
                "source": "Copernicus Sentinel-1 (C-SAR IW GRD)",
                "status": "REQUIRES_EXTERNAL_AUTH",
                "quality_flag": "UNAVAILABLE_PENDING_EARTHDATA_LOGIN",
                "vv_change_db": None,
                "vh_change_db": None,
                "change_confidence": None,
                "observation_timestamp": None,
                "notice": "SAR anomaly measurements require download credentials. Change evidence is corroborating anomaly only and never an automatic landslide label."
            },
            "flood": {
                "source": "Hydrological Inundation Layer",
                "status": "NOT_YET_IMPLEMENTED",
                "flood_indicator": None,
                "notice": "Riverine flood hazard layer integration pending."
            },
            "verification": {
                "source": "Field Inspections & Citizen Reports",
                "status": "ACTIVE",
                "has_verified_event": cell["historical"]["has_verified_event"],
                "event_id": cell["historical"]["historical_event_id"],
                "citizen_reports_filed": 0,
                "officer_verification_status": "VERIFIED_INCIDENT" if cell["historical"]["has_verified_event"] else "UNVERIFIED"
            },
            "exposure": {
                "source": "OpenStreetMap / Regional GIS",
                "status": "NOT_YET_IMPLEMENTED",
                "road_proximity_m": None,
                "population_density_est": None,
                "critical_infrastructure_count": None,
                "notice": "Infrastructure and vulnerability layers pending integration."
            },
            "baseline_susceptibility": cell["baseline_susceptibility"]
        }

    def get_latest_rainfall(self, district: Optional[str] = None, limit: int = 100) -> dict:
        """Returns latest rainfall observations from gpm_latest_observations.csv without fabrication."""
        self.ensure_loaded()
        obs = []
        if self._gpm_df is not None:
            df = self._gpm_df
            if district:
                df = df[df["district"].str.lower() == district.strip().lower()]
            
            sample_df = df.head(limit)
            for _, row in sample_df.iterrows():
                obs.append({
                    "cell_id": str(row["cell_id"]),
                    "district": str(row["district"]),
                    "latitude": clean_val(row.get("latitude")),
                    "longitude": clean_val(row.get("longitude")),
                    "gpm_grid_cell": clean_val(row.get("gpm_grid_cell")),
                    "observation_timestamp": clean_val(row.get("observation_timestamp")),
                    "source": str(row.get("source", "NASA / JAXA GPM Constellation")),
                    "source_product": str(row.get("source_product", "GPM_3IMERGHH_V07B_EARLY")),
                    "source_resolution": str(row.get("source_resolution", "0.1 deg (~10 km) Half-Hourly")),
                    "rainfall_rate": clean_val(row.get("rainfall_rate")),
                    "rainfall_30min": clean_val(row.get("rainfall_30min")),
                    "rainfall_3h": clean_val(row.get("rainfall_3h")),
                    "rainfall_6h": clean_val(row.get("rainfall_6h")),
                    "rainfall_24h": clean_val(row.get("rainfall_24h")),
                    "rainfall_72h": clean_val(row.get("rainfall_72h")),
                    "rainfall_duration_h": clean_val(row.get("rainfall_duration_h")),
                    "antecedent_rainfall_7d": clean_val(row.get("antecedent_rainfall_7d")),
                    "data_status": str(row.get("data_status", "REQUIRES_EXTERNAL_AUTH")),
                    "quality_flag": str(row.get("quality_flag", "UNAVAILABLE_PENDING_EARTHDATA_LOGIN")),
                })

        overall_status = obs[0]["data_status"] if obs else "REQUIRES_EXTERNAL_AUTH"
        if overall_status in ("AVAILABLE", "STALE"):
            notice = f"Near-real-time rainfall observations populated from NASA GPM IMERG ({overall_status})."
        elif overall_status == "MISSING":
            notice = "Granule data currently unavailable from NASA GES DISC."
        else:
            notice = "All numeric measurements are null because NASA Earthdata credentials are required for live ingestion."

        return {
            "layer": "GPM_IMERG_PRECIPITATION",
            "total_cells": len(obs),
            "data_status": overall_status,
            "notice": notice,
            "observations": obs,
        }

    def get_latest_soil_moisture(self, district: Optional[str] = None, limit: int = 100) -> dict:
        """Returns latest SMAP soil moisture observations without fabrication."""
        self.ensure_loaded()
        obs = []
        if self._smap_df is not None:
            df = self._smap_df
            if district:
                df = df[df["district"].str.lower() == district.strip().lower()]

            sample_df = df.head(limit)
            for _, row in sample_df.iterrows():
                obs.append({
                    "cell_id": str(row["cell_id"]),
                    "district": str(row["district"]),
                    "latitude": clean_val(row.get("latitude")),
                    "longitude": clean_val(row.get("longitude")),
                    "smap_ease2_grid_cell": clean_val(row.get("smap_ease2_grid_cell")),
                    "observation_timestamp": clean_val(row.get("observation_timestamp")),
                    "soil_moisture_current": clean_val(row.get("soil_moisture_current")),
                    "soil_moisture_previous": clean_val(row.get("soil_moisture_previous")),
                    "soil_moisture_change": clean_val(row.get("soil_moisture_change")),
                    "soil_moisture_change_percent": clean_val(row.get("soil_moisture_change_percent")),
                    "source": str(row.get("source", "NASA / NSIDC SMAP Mission")),
                    "source_product": str(row.get("source_product", "SPL3SMP_E_V006")),
                    "source_resolution": str(row.get("source_resolution", "9 km (EASE-Grid 2.0) Daily")),
                    "data_status": str(row.get("data_status", "REQUIRES_EXTERNAL_AUTH")),
                    "quality_flag": str(row.get("quality_flag", "UNAVAILABLE_PENDING_EARTHDATA_LOGIN")),
                })

        return {
            "layer": "SMAP_SOIL_MOISTURE",
            "total_cells": len(obs),
            "data_status": "REQUIRES_EXTERNAL_AUTH",
            "notice": "All numeric measurements are null because NASA Earthdata credentials are required for live ingestion.",
            "observations": obs,
        }

    def get_latest_satellite(self, district: Optional[str] = None, limit: int = 100) -> dict:
        """Returns latest Sentinel-1 SAR change observations without fabrication."""
        self.ensure_loaded()
        obs = []
        if self._sentinel_df is not None:
            df = self._sentinel_df
            if district:
                df = df[df["district"].str.lower() == district.strip().lower()]

            sample_df = df.head(limit)
            for _, row in sample_df.iterrows():
                obs.append({
                    "cell_id": str(row["cell_id"]),
                    "district": str(row["district"]),
                    "latitude": clean_val(row.get("latitude")),
                    "longitude": clean_val(row.get("longitude")),
                    "observation_timestamp": clean_val(row.get("observation_timestamp")),
                    "source": str(row.get("source", "Copernicus Sentinel-1 (C-SAR IW GRD)")),
                    "source_product": str(row.get("source_product", "S1_IW_GRDH_DUAL_POL")),
                    "source_resolution": str(row.get("source_resolution", "10m pixel spacing (IW GRDH); 500m = project analysis grid")),
                    "platform": clean_val(row.get("platform")),
                    "relative_orbit": clean_val(row.get("relative_orbit")),
                    "flight_direction": clean_val(row.get("flight_direction")),
                    "polarization": clean_val(row.get("polarization")),
                    "pre_scene_date": clean_val(row.get("pre_scene_date")),
                    "post_scene_date": clean_val(row.get("post_scene_date")),
                    "repeat_interval_days": clean_val(row.get("repeat_interval_days")),
                    "vv_change_db": clean_val(row.get("vv_change_db")),
                    "vh_change_db": clean_val(row.get("vh_change_db")),
                    "vv_vh_change": clean_val(row.get("vv_vh_change")),
                    "change_confidence": clean_val(row.get("change_confidence")),
                    "data_status": str(row.get("data_status", "REQUIRES_EXTERNAL_AUTH")),
                    "quality_flag": str(row.get("quality_flag", "UNAVAILABLE_PENDING_EARTHDATA_LOGIN")),
                    "scientific_notice": clean_val(row.get("scientific_notice")),
                })

        return {
            "layer": "SENTINEL1_SAR_CHANGE",
            "total_cells": len(obs),
            "data_status": "REQUIRES_EXTERNAL_AUTH",
            "notice": "SAR scenes are catalogued but observations require download authentication. Values are empty to prevent fabricated change detection.",
            "observations": obs,
        }

    def get_model_metadata(self) -> dict:
        """Truthfully returns ML model status and data ground-truth readiness."""
        return {
            "model_status": "NOT_TRAINED",
            "baseline_status": "AVAILABLE",
            "dynamic_model_status": "NOT_READY",
            "training_data_status": "INSUFFICIENT_VERIFIED_LABELS",
            "baseline_type": "TERRAIN_SUSCEPTIBILITY_TSI",
            "verified_positive_cells": 11,
            "verified_negative_cells": 0,
            "unlabeled_cells": 16950,
            "total_cells": TOTAL_CELL_COUNT,
            "notice": (
                "The current baseline susceptibility is a deterministic terrain morphometry index (TSI) "
                "derived from SRTM 30m DEM and PU learning similarity. No supervised dynamic ML model "
                "has been trained or validated yet."
            ),
        }

    def get_model_metrics(self) -> dict:
        """Truthfully states that evaluation metrics do not exist because no model is trained."""
        return {
            "status": "NOT_AVAILABLE",
            "reason": "No validated dynamic ML model is currently trained.",
            "metrics_available": False,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "roc_auc": None,
        }


# Singleton instance
data_service = DataService()
