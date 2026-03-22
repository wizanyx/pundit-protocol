"""Centralized runtime configuration for backend services and agents."""

from __future__ import annotations

import os


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _as_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def llm_provider() -> str:
    value = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    return value if value in {"gemini", "openai"} else "gemini"


DEBATE_ROUNDS = max(1, _as_int("DEBATE_ROUNDS", 2))
DEBATE_QUEUE_TIMEOUT = _as_float("DEBATE_QUEUE_TIMEOUT", 120.0)

PUNDIT_OPENAI_MODEL = os.getenv("PUNDIT_OPENAI_MODEL", "gpt-4o-mini")
PUNDIT_GEMINI_MODEL = os.getenv("PUNDIT_GEMINI_MODEL", "models/gemini-2.5-flash-lite")

MODERATOR_OPENAI_MODEL = os.getenv("MODERATOR_OPENAI_MODEL", "gpt-4o-mini")
MODERATOR_GEMINI_MODEL = os.getenv(
    "MODERATOR_GEMINI_MODEL", "models/gemini-2.5-flash-lite"
)
