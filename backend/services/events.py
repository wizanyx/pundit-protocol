"""Event payload helpers for websocket/UI contract consistency."""

from __future__ import annotations

from typing import Any


def overview_event(
    *,
    topic: str,
    overview: str,
    sources: list[dict[str, Any]],
    persona_mode: str,
    is_chaos_mode: bool,
) -> dict[str, Any]:
    return {
        "type": "overview",
        "overview": overview,
        "sources": sources,
        "topic": topic,
        "persona_mode": persona_mode,
        "is_chaos_mode": is_chaos_mode,
    }


def turn_event(
    *,
    round_index: int,
    speaker: str,
    text: str,
    source: str | None,
) -> dict[str, Any]:
    return {
        "type": "turn",
        "round": round_index,
        "speaker": speaker,
        "text": text,
        "source": source,
    }


def summary_event(
    *,
    topic: str,
    conclusion: str,
    arguments: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "type": "summary",
        "topic": topic,
        "conclusion": conclusion,
        "arguments": arguments,
    }


def error_event(*, detail: str, status_code: int) -> dict[str, Any]:
    return {
        "type": "error",
        "error": detail,
        "status_code": status_code,
    }
