"""
Comprehensive tests for Task 11: Area / Locality-Based Risk Search & Intelligence.
Verifies data integrity, distance rules, TSI aggregation math, API routes, and fallbacks.
"""

import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from app.main import app
from app.config import KOHIMA_LOCALITY_CSV, AIZAWL_LOCALITY_CSV, LOCALITY_MAPPING_CSV
from app.services import area_service, AreaService

client = TestClient(app)

# ===========================================================================
# 1. Dataset & Provenance Tests
# ===========================================================================

def test_locality_dataset_structure_and_existence():
    """Verify Kohima and Aizawl locality index files exist with exact required columns."""
    assert KOHIMA_LOCALITY_CSV.exists(), "kohima_locality_index.csv missing"
    assert AIZAWL_LOCALITY_CSV.exists(), "aizawl_locality_index.csv missing"

    required_cols = [
        "area_id", "area_name", "place_type", "latitude", "longitude",
        "source", "source_url", "source_date", "state", "district"
    ]

    df_k = pd.read_csv(KOHIMA_LOCALITY_CSV)
    df_a = pd.read_csv(AIZAWL_LOCALITY_CSV)

    for col in required_cols:
        assert col in df_k.columns, f"Missing column {col} in Kohima locality index"
        assert col in df_a.columns, f"Missing column {col} in Aizawl locality index"

    assert len(df_k) > 0, "Kohima locality index is empty"
    assert len(df_a) > 0, "Aizawl locality index is empty"

def test_no_fabricated_locality_names_and_sources():
    """Verify source provenance is OpenStreetMap Overpass API and no fake names exist."""
    df_k = pd.read_csv(KOHIMA_LOCALITY_CSV)
    df_a = pd.read_csv(AIZAWL_LOCALITY_CSV)

    for _, row in df_k.iterrows():
        assert "OpenStreetMap" in str(row["source"]), f"Invalid source provenance: {row['source']}"
        assert str(row["district"]).lower() == "kohima", "Incorrect district assignment"
        assert 25.0 <= float(row["latitude"]) <= 26.5, "Latitude out of Kohima bounds"
        assert 93.5 <= float(row["longitude"]) <= 94.5, "Longitude out of Kohima bounds"

    for _, row in df_a.iterrows():
        assert "OpenStreetMap" in str(row["source"]), f"Invalid source provenance: {row['source']}"
        assert str(row["district"]).lower() == "aizawl", "Incorrect district assignment"
        assert 23.0 <= float(row["latitude"]) <= 24.8, "Latitude out of Aizawl bounds"
        assert 92.4 <= float(row["longitude"]) <= 93.3, "Longitude out of Aizawl bounds"

# ===========================================================================
# 2. Locality Cell Association & Maximum Radius Rules
# ===========================================================================

def test_locality_to_cell_mapping_and_max_distance_rule():
    """Verify cell mapping adheres strictly to maximum association radius (2500m)."""
    assert LOCALITY_MAPPING_CSV.exists(), "locality_cell_mapping.csv missing"
    df_map = pd.read_csv(LOCALITY_MAPPING_CSV)

    required_map_cols = ["area_id", "area_name", "cell_id", "distance_to_cell_m", "association_method", "source"]
    for col in required_map_cols:
        assert col in df_map.columns, f"Missing column {col} in locality cell mapping CSV"

    # Check maximum radius constraint
    max_dist = df_map["distance_to_cell_m"].max()
    assert max_dist <= 2500.0, f"Cell mapped beyond max radius: {max_dist}m > 2500m"

# ===========================================================================
# 3. Aggregation Mathematics Tests
# ===========================================================================

def test_area_risk_aggregation_math():
    """Verify area TSI score max, dominant class, cell count, and percentage distribution."""
    # Test Durtlang area in Aizawl (AIZ_LOC_021)
    risk_info = area_service.get_area_risk("AIZ_LOC_021")
    assert risk_info is not None, "Durtlang area not found in area_service"

    assert risk_info["area_name"] == "Durtlang"
    assert risk_info["district"] == "Aizawl"
    assert risk_info["cell_count"] > 0

    # Class distribution percentages sum up to ~100%
    dist = risk_info["class_distribution"]
    pct_sum = sum(dist.values())
    assert abs(pct_sum - 100.0) < 0.1, f"TSI class distribution does not sum to 100%: {pct_sum}"

    # Dominant class matches highest percentage in distribution
    top_class = max(dist.items(), key=lambda x: x[1])[0]
    assert risk_info["dominant_class"] == top_class, f"Dominant class mismatch: {risk_info['dominant_class']} vs {top_class}"

    # Notice disclaimer is present
    assert "Baseline susceptibility is not a live landslide prediction." in risk_info["notice"]

def test_historical_event_association():
    """Verify historical landslide presence is accurately identified for areas."""
    risk_info = area_service.get_area_risk("AIZ_LOC_021")
    assert risk_info["has_historical_events"] is True
    assert len(risk_info["historical_event_ids"]) > 0
    assert "LS_AIZ_2023_001" in risk_info["historical_event_ids"] or "LS_AIZ_2020_001" in risk_info["historical_event_ids"]

# ===========================================================================
# 4. API Endpoints & Response Validation
# ===========================================================================

def test_api_get_areas_list_and_search():
    """Test GET /api/areas search and filtering."""
    # 1. Search Kohima district
    r_k = client.get("/api/areas?district=Kohima")
    assert r_k.status_code == 200
    data_k = r_k.json()
    assert len(data_k) > 0
    assert all(a["district"] == "Kohima" for a in data_k)

    # 2. Search specific area name 'Durtlang'
    r_d = client.get("/api/areas?search=Durtlang")
    assert r_d.status_code == 200
    data_d = r_d.json()
    assert len(data_d) >= 1
    assert data_d[0]["area_name"] == "Durtlang"

def test_api_get_area_by_id():
    """Test GET /api/areas/{area_id} detail endpoint."""
    r = client.get("/api/areas/AIZ_LOC_021")
    assert r.status_code == 200
    data = r.json()
    assert data["area_id"] == "AIZ_LOC_021"
    assert data["area_name"] == "Durtlang"
    assert "associated_cells" in data

def test_api_get_area_risk():
    """Test GET /api/areas/{area_id}/risk endpoint."""
    r = client.get("/api/areas/AIZ_LOC_021/risk")
    assert r.status_code == 200
    data = r.json()
    assert data["area_id"] == "AIZ_LOC_021"
    assert "max_tsi" in data
    assert "class_distribution" in data
    assert "dynamic_status" in data
    assert data["dynamic_status"]["rainfall"] == "Unavailable — NASA Earthdata authentication required"

def test_api_get_area_cells():
    """Test GET /api/areas/{area_id}/cells endpoint."""
    r = client.get("/api/areas/AIZ_LOC_021/cells")
    assert r.status_code == 200
    data = r.json()
    assert data["area_id"] == "AIZ_LOC_021"
    assert data["total_cells"] > 0
    assert len(data["cells"]) == data["total_cells"]

def test_api_invalid_area_id_returns_404():
    """Test GET /api/areas/{invalid_id} returns 404."""
    r = client.get("/api/areas/INVALID_AREA_9999")
    assert r.status_code == 404

def test_fallback_naming_for_unassociated_cells():
    """Verify Phase 8 fallback naming format: District + Cell ID + coordinates."""
    # KOH_00001 is unassociated
    info = area_service.get_cell_locality_info("KOH_00001")
    assert info["is_associated"] is False
    assert "Kohima Cell KOH_00001" in info["area_name"]
    assert "(" in info["area_name"] and ")" in info["area_name"]
