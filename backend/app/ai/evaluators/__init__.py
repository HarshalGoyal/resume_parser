"""Shared helpers for LLM-backed evaluators."""

import json
import re
from pathlib import Path

from app.core.exceptions import EvaluationFailedError

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> tuple[str, str]:
    """Load a prompt file; returns (version, prompt_text).

    Prompt files start with a 'version: N' line followed by '---'.
    """
    raw = (_PROMPTS_DIR / name).read_text(encoding="utf-8")
    header, _, body = raw.partition("---")
    version = header.replace("version:", "").strip()
    return version, body.strip()


def parse_json_response(step: str, text: str) -> dict:
    """Parse an LLM response expected to be a single JSON object. Tolerates a
    fenced ```json block; anything else unparseable is a hard error."""
    candidate = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1)
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise EvaluationFailedError(step=step, reason=f"invalid JSON: {e}") from e
    if not isinstance(result, dict):
        raise EvaluationFailedError(step=step, reason="response is not a JSON object")
    return result
