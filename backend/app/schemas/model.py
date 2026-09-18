"""
Schemas for model metadata and model performance metrics.
Truthfully reports that no trained dynamic ML model exists yet.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ModelMetadata(BaseModel):
    model_status: str = Field("NOT_TRAINED", description="Dynamic ML model training status")
    baseline_status: str = Field("AVAILABLE", description="Static baseline terrain susceptibility status")
    dynamic_model_status: str = Field("NOT_READY", description="Dynamic multi-source inference status")
    training_data_status: str = Field("INSUFFICIENT_VERIFIED_LABELS", description="Ground truth readiness")
    baseline_type: str = Field("TERRAIN_SUSCEPTIBILITY_TSI", description="Active baseline method")
    verified_positive_cells: int = Field(11, description="Verified historical landslide cells")
    verified_negative_cells: int = Field(0, description="Confirmed non-landslide ground truth cells")
    unlabeled_cells: int = Field(16950, description="Unlabeled pilot grid cells")
    total_cells: int = Field(16961, description="Total analysis cells (Kohima 6055 + Aizawl 10906)")
    notice: str = Field(
        "The current baseline susceptibility is a deterministic terrain morphometry index (TSI) "
        "derived from SRTM 30m DEM and PU learning similarity. No supervised dynamic ML model "
        "has been trained or validated yet."
    )


class ModelMetrics(BaseModel):
    status: str = Field("NOT_AVAILABLE", description="Metrics availability status")
    reason: str = Field(
        "No validated dynamic ML model is currently trained.",
        description="Reason why evaluation metrics are not available"
    )
    metrics_available: bool = Field(False, description="Whether validation metrics exist")
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1: Optional[float] = None
    roc_auc: Optional[float] = None
