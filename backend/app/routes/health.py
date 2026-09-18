"""
Health check route.
"""

from fastapi import APIRouter
from ..schemas.common import HealthResponse

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health():
    """Returns the operational health status of the SIH 2026 Landslide Risk backend."""
    return HealthResponse(
        status="ok",
        service="SIH 2026 Landslide Risk Backend",
        version="0.1.0"
    )
