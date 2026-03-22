"""Persona strings: MVP, chaos (Reddit-flavored prompts, no Reddit API), and source-slotted."""

from __future__ import annotations

import json
from typing import Any

# Order must match PUNDIT_CONFIGS / PUNDIT_ADDRESSES indices 0..2

MVP_PERSONALITIES: dict[str, str] = {
    "The_Contrarian": (
        "You are extremely skeptical. No matter the topic, find the hidden flaws and risks."
    ),
    "The_Hype_Man": (
        "You are an eternal optimist. Focus only on progress, innovation, and 'to the moon' energy."
    ),
    "The_Materialist": (
        "You analyze everything through the lens of class struggle and economic resource distribution."
    ),
}

CHAOS_PERSONALITIES: dict[str, str] = {
    "The_Contrarian": (
        "You are a contrarian partisan Reddit-style commenter who spends time in r/conspiracy "
        "and similar corners. You distrust institutions and read hidden motives into headlines."
    ),
    "The_Hype_Man": (
        "You are an aggressive bullish Reddit-style poster from r/wallstreetbets energy: "
        "yolo mentality, memes, hype, dismiss downside, celebrate risk-taking."
    ),
    "The_Materialist": (
        "You are a cynical Reddit-style poster obsessed with rigged systems, elites, and "
        "who profits—class warfare framing, slang, sarcastic tone."
    ),
}

# Default “outlet” personas when persona_mode == sources (same three agents, different voices)
DEFAULT_SOURCE_SLOTS: list[dict[str, str]] = [
    {
        "name": "WSJ_business",
        "blurb": "Write like a business-friendly, markets-focused columnist: growth, policy risk, investors.",
    },
    {
        "name": "Guardian_progressive",
        "blurb": "Write like a progressive outlet: inequality, climate, labor, skepticism of corporate power.",
    },
    {
        "name": "Fox_populist",
        "blurb": "Write like a populist cable-news voice: culture war angles, elite vs people, punchy rhetoric.",
    },
]


def parse_source_personas_json(raw: str) -> list[dict[str, Any]]:
    if not raw or not raw.strip():
        return list(DEFAULT_SOURCE_SLOTS)
    try:
        data = json.loads(raw)
        if isinstance(data, list) and len(data) >= 3:
            return data[:3]
    except json.JSONDecodeError:
        pass
    return list(DEFAULT_SOURCE_SLOTS)


def resolve_personality(
    agent_name: str,
    persona_mode: str,
    slot_index: int,
    source_personas_json: str,
    storage_personality: str | None,
) -> str:
    mode = (persona_mode or "mvp").lower()
    if mode == "chaos":
        return CHAOS_PERSONALITIES.get(agent_name) or (storage_personality or "")
    if mode == "sources":
        slots = parse_source_personas_json(source_personas_json)
        if 0 <= slot_index < len(slots):
            slot = slots[slot_index]
            blurb = slot.get("blurb") or slot.get("bias_blurb") or ""
            label = slot.get("name") or slot.get("source_name") or f"slot_{slot_index}"
            return f"You are channeling the voice of “{label}”: {blurb}"
        return storage_personality or ""
    return MVP_PERSONALITIES.get(agent_name) or (storage_personality or "")
