"""
Services package initialization.
"""

from .data_service import data_service, DataService
from .risk_engine import risk_engine, RiskEngine
from .alert_service import alert_service, AlertService
from .area_service import area_service, AreaService
from .ml_model_service import MLModelService

ml_model_service = MLModelService(data_service)

__all__ = ["data_service", "DataService", "risk_engine", "RiskEngine", "alert_service", "AlertService", "area_service", "AreaService", "ml_model_service", "MLModelService"]
