"""
FastAPI router for LLM-generated risk explanations and recommended actions.
Built on top of the existing risk engine / TSI baseline / area-service outputs —
the LLM only narrates real, already-computed data, it does not compute risk itself.
"""

from fastapi import APIRouter, HTTPException, status

from ..schemas.ai import AIExplanationResponse
from ..services import data_service, risk_engine, area_service, ml_model_service
from ..services.ai_explanation_service import ai_explanation_service

router = APIRouter(prefix="/api", tags=["AI"])


@router.get("/cells/{cell_id}/ai-explanation", response_model=AIExplanationResponse)
def get_cell_ai_explanation(cell_id: str):
    """
    Returns an LLM-generated plain-language explanation and recommended action
    for a 500m cell, grounded only in the cell's real static/dynamic risk data.
    """
    cell = data_service.get_cell(cell_id)
    if not cell:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cell ID '{cell_id}' not found in Kohima or Aizawl pilot grids.",
        )

    risk = risk_engine.evaluate_cell_risk(cell_id)
    prediction = ml_model_service.get_cell_prediction(cell_id)
    baseline = cell.get("baseline_susceptibility", {})
    historical = cell.get("historical", {})

    context = {
        "location_type": "500m analysis cell",
        "cell_id": cell_id,
        "district": cell.get("district"),
        "static_terrain_susceptibility_tsi_0_to_100": baseline.get("tsi_score"),
        "tsi_class": baseline.get("tsi_class"),
        "primary_terrain_contributors": baseline.get("primary_terrain_contributors"),
        "has_verified_historical_landslide": historical.get("has_verified_event"),
        "historical_event_description": historical.get("event_description"),
        "dynamic_risk_status": risk.risk_status if risk else "UNAVAILABLE",
        "combined_risk_score_0_to_100": risk.combined_risk_score if risk else None,
        "risk_level": risk.risk_level if risk else None,
        "dynamic_factor_statuses": (
            {f.factor: f.status for f in risk.factors} if risk else {}
        ),
        "top_contributing_factors": prediction.get("top_contributing_factors") if prediction else [],
        "missing_data_feeds": prediction.get("missing_features") if prediction else [],
        "existing_rule_based_recommendation": risk.recommendation if risk else None,
    }

    result = ai_explanation_service.generate(context)
    return AIExplanationResponse(**result)


@router.get("/areas/{area_id}/ai-explanation", response_model=AIExplanationResponse)
def get_area_ai_explanation(area_id: str):
    """
    Returns an LLM-generated plain-language explanation and recommended action
    for a named locality, grounded only in its real aggregated cell-risk data.
    """
    area_service.ensure_loaded()
    area_risk = area_service.get_area_risk(area_id)
    if not area_risk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Area '{area_id}' not found.",
        )

    context = {
        "location_type": "named locality (aggregated 500m cells)",
        "area_name": area_risk.get("area_name"),
        "district": area_risk.get("district"),
        "place_type": area_risk.get("place_type"),
        "cell_count": area_risk.get("cell_count"),
        "max_static_tsi_0_to_100": area_risk.get("max_tsi"),
        "dominant_tsi_class": area_risk.get("dominant_class"),
        "tsi_class_distribution_percent": area_risk.get("class_distribution"),
        "has_verified_historical_landslide": area_risk.get("has_historical_events"),
        "historical_event_ids": area_risk.get("historical_event_ids"),
        "dynamic_feed_status": area_risk.get("dynamic_status"),
    }

    result = ai_explanation_service.generate(context)
    return AIExplanationResponse(**result)
