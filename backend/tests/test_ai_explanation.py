"""
Tests for the LLM-based AI explanation service and endpoints.
Verifies:
1. A missing NVIDIA_API_KEY yields an honest AI_UNAVAILABLE status, never fabricated text.
2. Markdown-fenced JSON from the model is parsed correctly.
3. An invalid recommended_action from the model is dropped rather than trusted blindly.
4. The endpoints 404 on an unknown cell/area and return the expected shape on success.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_explanation_service import AIExplanationService

client = TestClient(app)


def test_unavailable_when_no_api_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    service = AIExplanationService()
    result = service.generate({"cell_id": "KOH_00001"})
    assert result["status"] == "AI_UNAVAILABLE"
    assert result["explanation"] is None
    assert "NVIDIA_API_KEY" in result["notice"]


def test_parses_markdown_fenced_json():
    service = AIExplanationService()
    content = '```json\n{"explanation": "test", "recommended_action": "MONITOR", "action_reason": "why"}\n```'
    parsed = service._parse_model_json(content)
    assert parsed == {"explanation": "test", "recommended_action": "MONITOR", "action_reason": "why"}


def test_parses_final_json_marker_after_reasoning_trace():
    """The default model is a reasoning model that thinks out loud before answering;
    the real content field looks like '<chain of thought> FINAL_JSON: {...}'."""
    service = AIExplanationService()
    content = (
        "We need to decide the action. High TSI, historical event present. "
        'FINAL_JSON: {"explanation": "test", "recommended_action": "MONITOR", "action_reason": "why"}'
    )
    parsed = service._parse_model_json(content)
    assert parsed == {"explanation": "test", "recommended_action": "MONITOR", "action_reason": "why"}


def test_invalid_recommended_action_is_dropped(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key-for-test")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {"message": {"content": '{"explanation": "ok", "recommended_action": "NUKE_THE_HILL", "action_reason": "why"}'}}
                ]
            }

    monkeypatch.setattr("app.services.ai_explanation_service.httpx.post", lambda *a, **k: FakeResponse())

    service = AIExplanationService()
    result = service.generate({"cell_id": "KOH_00001"})
    assert result["status"] == "AVAILABLE"
    assert result["recommended_action"] is None  # invalid action must not pass through
    assert result["explanation"] == "ok"


def test_cell_ai_explanation_404_unknown_cell():
    response = client.get("/api/cells/NOT_A_REAL_CELL/ai-explanation")
    assert response.status_code == 404


def test_cell_ai_explanation_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    response = client.get("/api/cells/KOH_00001/ai-explanation")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "AI_UNAVAILABLE"
    assert data["recommended_action"] is None


def test_area_ai_explanation_404_unknown_area():
    response = client.get("/api/areas/NOT_A_REAL_AREA/ai-explanation")
    assert response.status_code == 404
