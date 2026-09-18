"""
Routes package initialization and router aggregation.
"""

from fastapi import APIRouter
from .health import router as health_router
from .districts import router as districts_router
from .cells import router as cells_router
from .observations import router as observations_router
from .model import router as model_router
from .alerts import router as alerts_router
from .areas import router as areas_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(districts_router)
api_router.include_router(cells_router)
api_router.include_router(observations_router)
api_router.include_router(model_router)
api_router.include_router(alerts_router)
api_router.include_router(areas_router)

__all__ = ["api_router"]
