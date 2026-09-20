"""
Schema for the LLM-generated risk-explanation endpoints.
"""

from typing import Optional
from pydantic import BaseModel, Field


class AIExplanationResponse(BaseModel):
    status: str = Field(..., description="AVAILABLE or AI_UNAVAILABLE")
    explanation: Optional[str] = Field(None, description="Plain-language explanation grounded only in real computed data")
    recommended_action: Optional[str] = Field(None, description="One of the fixed operational-action vocabulary values")
    action_reason: Optional[str] = Field(None, description="One-sentence justification for the recommended action")
    model: Optional[str] = Field(None, description="NVIDIA NIM model identifier used to generate this response")
    notice: str = Field(..., description="Transparency notice, including why the AI is unavailable if applicable")
