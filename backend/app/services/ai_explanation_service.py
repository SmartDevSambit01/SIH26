"""
AI narrative explanation service (NVIDIA NIM free-tier endpoint, build.nvidia.com).

Turns real, already-computed hazard data (TSI, dynamic risk factors, status flags)
into a plain-language explanation and a recommended operational action. The model
is only ever shown numbers this backend already computed or verified — it never
receives permission to invent sensor readings, and a missing/failed API call
returns an honest AI_UNAVAILABLE status rather than fabricated text.
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("ner_safe.ai_explanation_service")

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
# nvidia/nemotron-3-super-120b-a12b is a reasoning model: it always thinks before
# answering, so the prompt asks it to end with a "FINAL_JSON:" marker line and we
# parse from there, discarding the chain-of-thought rather than fighting the model
# to suppress it (that reliably failed; see _parse_model_json).
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
FINAL_JSON_MARKER = "FINAL_JSON:"

# Fixed operational-action vocabulary from the project's technical approach (PRD §74).
VALID_ACTIONS = [
    "MONITOR",
    "INSPECT",
    "VERIFY",
    "RESTRICT_ACCESS",
    "ISSUE_WARNING",
    "PRE_POSITION_RESPONSE_TEAMS",
    "PREPARE_EVACUATION",
    "EVACUATE",
]

SYSTEM_PROMPT = (
    "You are a disaster-risk assistant for SARVAS/NER Safe, a landslide early-warning system for "
    "Kohima (Nagaland) and Aizawl (Mizoram), India. You will be given ONLY real, already-computed "
    "data for one location as JSON. Some fields may be null or carry a status such as UNAVAILABLE, "
    "STALE, or REQUIRES_EXTERNAL_AUTH. Never invent a number that was not given to you, and never "
    "claim a stale or unavailable feed is live or current. If dynamic risk data is unavailable, say "
    "so plainly and base your explanation on whatever static terrain susceptibility is available. "
    "Think it through, then end your reply with a line starting with exactly 'FINAL_JSON:' "
    "followed by strict JSON only (no markdown fences, no extra keys) matching this shape: "
    '{"explanation": "2-4 plain-language sentences", "recommended_action": one of '
    + json.dumps(VALID_ACTIONS)
    + ', "action_reason": "one sentence justifying the action"}'
)


class AIExplanationService:
    """Thin client around an NVIDIA NIM chat-completions endpoint with an in-memory cache."""

    def __init__(self):
        self._cache: Dict[str, dict] = {}

    def _api_key(self) -> Optional[str]:
        return os.environ.get("NVIDIA_API_KEY")

    def _model(self) -> str:
        return os.environ.get("NVIDIA_MODEL", DEFAULT_MODEL)

    def _cache_key(self, context: Dict[str, Any]) -> str:
        blob = json.dumps(context, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        context: real, already-computed values for one cell/area (scores, status
        flags, terrain figures, etc). Returns a dict describing the outcome;
        never fabricates a result when the key/API/response is unavailable.
        """
        api_key = self._api_key()
        if not api_key:
            return {
                "status": "AI_UNAVAILABLE",
                "explanation": None,
                "recommended_action": None,
                "action_reason": None,
                "model": None,
                "notice": "NVIDIA_API_KEY is not configured on the server.",
            }

        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            return self._cache[cache_key]

        model = self._model()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, default=str)},
            ],
            "temperature": 0.2,
            "max_tokens": 800,  # generous headroom for the reasoning trace preceding FINAL_JSON
        }

        try:
            response = httpx.post(
                NVIDIA_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=20.0,
            )
            response.raise_for_status()
            raw_content = response.json()["choices"][0]["message"]["content"]
            parsed = self._parse_model_json(raw_content)
        except Exception as e:
            logger.error(f"NVIDIA AI explanation request failed: {e}")
            return {
                "status": "AI_UNAVAILABLE",
                "explanation": None,
                "recommended_action": None,
                "action_reason": None,
                "model": model,
                "notice": f"AI explanation service temporarily unavailable ({type(e).__name__}).",
            }

        if not parsed or not parsed.get("explanation"):
            return {
                "status": "AI_UNAVAILABLE",
                "explanation": None,
                "recommended_action": None,
                "action_reason": None,
                "model": model,
                "notice": "AI model returned an unparseable response.",
            }

        action = parsed.get("recommended_action")
        if action not in VALID_ACTIONS:
            action = None

        result = {
            "status": "AVAILABLE",
            "explanation": parsed.get("explanation"),
            "recommended_action": action,
            "action_reason": parsed.get("action_reason"),
            "model": model,
            "notice": "Generated by an LLM from real computed hazard data. This is a narrative aid, not a calibrated prediction.",
        }
        self._cache[cache_key] = result
        return result

    def _parse_model_json(self, content: str) -> Optional[dict]:
        content = content.strip()
        if FINAL_JSON_MARKER in content:
            content = content.rsplit(FINAL_JSON_MARKER, 1)[1].strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return None


# Singleton instance
ai_explanation_service = AIExplanationService()
