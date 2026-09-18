"""
Area and Locality Intelligence Service for SIH 2026.
Provides area-level aggregation of 500m cells, TSI baseline susceptibility,
and search capabilities without fabricating data.
"""

import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from collections import Counter

from ..config import (
    KOHIMA_LOCALITY_CSV,
    AIZAWL_LOCALITY_CSV,
    LOCALITY_MAPPING_CSV
)
from .data_service import data_service, DataService

logger = logging.getLogger("ner_safe.area_service")

class AreaService:
    def __init__(self, data_service: DataService):
        self.data_service = data_service
        self._localities: Dict[str, dict] = {}  # area_id -> locality dict
        self._area_cell_mapping: Dict[str, List[dict]] = {}  # area_id -> list of cell mapping dicts
        self._cell_area_mapping: Dict[str, dict] = {}  # cell_id -> locality mapping dict
        self._initialized = False

    def ensure_loaded(self):
        if not self._initialized:
            self.load_all()

    def load_all(self):
        if self._initialized:
            return

        self.data_service.ensure_loaded()
        logger.info("Initializing AreaService...")

        # 1. Load Kohima Localities
        if KOHIMA_LOCALITY_CSV.exists():
            try:
                df_k = pd.read_csv(KOHIMA_LOCALITY_CSV)
                for _, row in df_k.iterrows():
                    aid = str(row["area_id"])
                    self._localities[aid] = {
                        "area_id": aid,
                        "area_name": str(row["area_name"]),
                        "place_type": str(row["place_type"]),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "source": str(row["source"]),
                        "source_url": str(row.get("source_url", "")),
                        "source_date": str(row.get("source_date", "")),
                        "state": str(row["state"]),
                        "district": str(row["district"]),
                    }
            except Exception as e:
                logger.error(f"Failed to load Kohima locality CSV: {e}")

        # 2. Load Aizawl Localities
        if AIZAWL_LOCALITY_CSV.exists():
            try:
                df_a = pd.read_csv(AIZAWL_LOCALITY_CSV)
                for _, row in df_a.iterrows():
                    aid = str(row["area_id"])
                    self._localities[aid] = {
                        "area_id": aid,
                        "area_name": str(row["area_name"]),
                        "place_type": str(row["place_type"]),
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "source": str(row["source"]),
                        "source_url": str(row.get("source_url", "")),
                        "source_date": str(row.get("source_date", "")),
                        "state": str(row["state"]),
                        "district": str(row["district"]),
                    }
            except Exception as e:
                logger.error(f"Failed to load Aizawl locality CSV: {e}")

        # 3. Load Cell Mappings
        if LOCALITY_MAPPING_CSV.exists():
            try:
                df_map = pd.read_csv(LOCALITY_MAPPING_CSV)
                for _, row in df_map.iterrows():
                    aid = str(row["area_id"])
                    cid = str(row["cell_id"])
                    dist_m = float(row["distance_to_cell_m"])
                    assoc_meth = str(row["association_method"])
                    src = str(row["source"])

                    mapping_item = {
                        "area_id": aid,
                        "area_name": str(row["area_name"]),
                        "cell_id": cid,
                        "distance_to_cell_m": dist_m,
                        "association_method": assoc_meth,
                        "source": src
                    }

                    if aid not in self._area_cell_mapping:
                        self._area_cell_mapping[aid] = []
                    self._area_cell_mapping[aid].append(mapping_item)

                    self._cell_area_mapping[cid] = mapping_item
            except Exception as e:
                logger.error(f"Failed to load locality cell mapping CSV: {e}")

        self._initialized = True
        logger.info(f"AreaService initialized. Loaded {len(self._localities)} localities and {len(self._cell_area_mapping)} cell associations.")

    def get_areas(
        self, 
        district: Optional[str] = None, 
        search: Optional[str] = None, 
        limit: int = 100
    ) -> List[dict]:
        self.ensure_loaded()
        results = []

        district_lower = district.lower() if district else None
        search_lower = search.strip().lower() if search else None

        for aid, loc in self._localities.items():
            if district_lower and loc["district"].lower() != district_lower:
                continue

            if search_lower:
                match_name = search_lower in loc["area_name"].lower()
                match_dist = search_lower in loc["district"].lower()
                match_type = search_lower in loc["place_type"].lower()
                match_id = search_lower in aid.lower()
                if not (match_name or match_dist or match_type or match_id):
                    continue

            # Calculate basic risk metrics for summary
            associated_maps = self._area_cell_mapping.get(aid, [])
            cell_ids = [m["cell_id"] for m in associated_maps]
            cell_count = len(cell_ids)

            max_tsi = None
            dominant_class = None
            has_hist = False

            if cell_ids:
                tsi_scores = []
                tsi_classes = []
                for cid in cell_ids:
                    cell_data = self.data_service.get_cell(cid)
                    if cell_data:
                        base = cell_data.get("baseline_susceptibility", {})
                        score = base.get("tsi_score")
                        cls = base.get("tsi_class")
                        if score is not None:
                            tsi_scores.append(score)
                        if cls is not None:
                            tsi_classes.append(cls)
                        hist = cell_data.get("historical", {})
                        if hist.get("has_verified_event"):
                            has_hist = True

                if tsi_scores:
                    max_tsi = round(max(tsi_scores), 4)
                if tsi_classes:
                    counts = Counter(tsi_classes)
                    dominant_class = counts.most_common(1)[0][0]

            results.append({
                "area_id": aid,
                "area_name": loc["area_name"],
                "place_type": loc["place_type"],
                "district": loc["district"],
                "state": loc["state"],
                "latitude": loc["latitude"],
                "longitude": loc["longitude"],
                "cell_count": cell_count,
                "max_tsi": max_tsi,
                "dominant_class": dominant_class,
                "has_historical_events": has_hist
            })

            if len(results) >= limit:
                break

        return results

    def get_area_by_id(self, area_id: str) -> Optional[dict]:
        self.ensure_loaded()
        loc = self._localities.get(area_id)
        if not loc:
            return None

        associated_maps = self._area_cell_mapping.get(area_id, [])
        cell_ids = [m["cell_id"] for m in associated_maps]

        return {
            **loc,
            "cell_count": len(cell_ids),
            "associated_cells": cell_ids
        }

    def get_area_risk(self, area_id: str) -> Optional[dict]:
        self.ensure_loaded()
        loc = self._localities.get(area_id)
        if not loc:
            return None

        associated_maps = self._area_cell_mapping.get(area_id, [])
        cell_ids = [m["cell_id"] for m in associated_maps]

        highest_risk_cell_id = None
        max_tsi = -1.0
        tsi_classes = []
        historical_event_ids = []
        has_historical_events = False

        for cid in cell_ids:
            cell_data = self.data_service.get_cell(cid)
            if not cell_data:
                continue

            base = cell_data.get("baseline_susceptibility", {})
            score = base.get("tsi_score")
            cls = base.get("tsi_class")

            if score is not None:
                if score > max_tsi:
                    max_tsi = score
                    highest_risk_cell_id = cid

            if cls is not None:
                tsi_classes.append(cls)

            hist = cell_data.get("historical", {})
            if hist.get("has_verified_event"):
                has_historical_events = True
                ev_id = hist.get("historical_event_id")
                if ev_id and ev_id not in historical_event_ids:
                    historical_event_ids.append(ev_id)

        # Class distribution percentages
        total_valid = len(tsi_classes)
        class_distribution = {}
        dominant_class = None

        if total_valid > 0:
            counts = Counter(tsi_classes)
            dominant_class = counts.most_common(1)[0][0]
            for c_name, count in counts.items():
                class_distribution[c_name] = round((count / total_valid) * 100.0, 2)
        else:
            max_tsi = None

        if max_tsi == -1.0:
            max_tsi = None

        return {
            "area_id": area_id,
            "area_name": loc["area_name"],
            "district": loc["district"],
            "place_type": loc["place_type"],
            "data_source": loc["source"],
            "cell_count": len(cell_ids),
            "highest_risk_cell_id": highest_risk_cell_id,
            "max_tsi": round(max_tsi, 4) if max_tsi is not None else None,
            "dominant_class": dominant_class,
            "class_distribution": class_distribution,
            "has_historical_events": has_historical_events,
            "historical_event_ids": historical_event_ids,
            "associated_cell_ids": cell_ids,
            "notice": "Baseline susceptibility is not a live landslide prediction.",
            "dynamic_status": {
                "rainfall": "Unavailable — NASA Earthdata authentication required",
                "soil_moisture": "Unavailable — NASA Earthdata authentication required",
                "sentinel1": "Unavailable — external authentication/download pending",
                "flood": "Unavailable"
            }
        }

    def get_area_cells(self, area_id: str) -> Optional[dict]:
        self.ensure_loaded()
        loc = self._localities.get(area_id)
        if not loc:
            return None

        associated_maps = self._area_cell_mapping.get(area_id, [])
        cell_items = []

        for m in associated_maps:
            cid = m["cell_id"]
            cell_data = self.data_service.get_cell(cid)
            if cell_data:
                base = cell_data.get("baseline_susceptibility", {})
                terrain = cell_data.get("terrain", {})
                hist = cell_data.get("historical", {})
                cell_items.append({
                    "cell_id": cid,
                    "latitude": cell_data.get("latitude"),
                    "longitude": cell_data.get("longitude"),
                    "distance_to_locality_m": m["distance_to_cell_m"],
                    "elevation_mean": terrain.get("elevation_mean"),
                    "slope_mean": terrain.get("slope_mean"),
                    "aspect_mean": terrain.get("aspect_mean"),
                    "tsi_score": base.get("tsi_score"),
                    "tsi_class": base.get("tsi_class"),
                    "has_historical_event": hist.get("has_verified_event", False),
                    "historical_event_id": hist.get("historical_event_id")
                })

        return {
            "area_id": area_id,
            "area_name": loc["area_name"],
            "district": loc["district"],
            "total_cells": len(cell_items),
            "cells": cell_items
        }

    def get_cell_locality_info(self, cell_id: str) -> dict:
        """
        Returns associated locality or fallback name per Phase 8 rules:
        District + Cell ID + coordinates
        """
        self.ensure_loaded()
        cell_data = self.data_service.get_cell(cell_id)
        cell_map = self._cell_area_mapping.get(cell_id)

        if cell_map and cell_map["area_id"] in self._localities:
            loc = self._localities[cell_map["area_id"]]
            return {
                "is_associated": True,
                "area_id": loc["area_id"],
                "area_name": loc["area_name"],
                "place_type": loc["place_type"],
                "distance_m": cell_map["distance_to_cell_m"],
                "display_name": f"{loc['area_name']} ({loc['place_type']})"
            }

        # Fallback naming for unassociated cell
        if cell_data:
            dist = cell_data.get("district", "Unknown")
            lat = round(cell_data.get("latitude", 0.0), 4) if cell_data.get("latitude") else "N/A"
            lon = round(cell_data.get("longitude", 0.0), 4) if cell_data.get("longitude") else "N/A"
            fallback_name = f"{dist} Cell {cell_id} ({lat}, {lon})"
        else:
            fallback_name = f"Cell {cell_id}"

        return {
            "is_associated": False,
            "area_id": None,
            "area_name": fallback_name,
            "place_type": "Unassociated Analysis Cell",
            "distance_m": None,
            "display_name": fallback_name
        }

area_service = AreaService(data_service)
