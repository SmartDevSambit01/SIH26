"""
Common schemas for SIH 2026 API responses.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status", examples=["ok"])
    service: str = Field(..., description="Service name", examples=["SIH 2026 Landslide Risk Backend"])
    version: str = Field(..., description="API version", examples=["0.1.0"])


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Detailed error description")
    error_type: Optional[str] = Field(None, description="Error classification")
