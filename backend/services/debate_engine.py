"""Debate state orchestration primitives for the moderator agent."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

try:
    from ..agents.messages import Argument, DebateBrief, DebateTurn
except ImportError:
    from agents.messages import Argument, DebateBrief, DebateTurn


@dataclass
class DebateState:
    topic: str
    overview: str
    articles_json: str
    is_chaos_mode: bool
    persona_mode: str
    source_personas_json: str
    round_index: int = 1
    max_rounds: int = 2
    history: list[dict[str, Any]] = field(default_factory=list)
    pending: list[dict[str, Any]] = field(default_factory=list)


def create_state(brief: DebateBrief, overview: str, max_rounds: int) -> DebateState:
    return DebateState(
        topic=brief.topic,
        overview=overview,
        articles_json=brief.articles_json,
        is_chaos_mode=brief.is_chaos_mode,
        persona_mode=brief.persona_mode,
        source_personas_json=brief.source_personas_json or "[]",
        round_index=1,
        max_rounds=max_rounds,
    )


def build_turn_message(state: DebateState) -> DebateTurn:
    return DebateTurn(
        topic=state.topic,
        round_index=state.round_index,
        history_json=json.dumps(state.history, ensure_ascii=False),
        overview=state.overview,
        articles_json=state.articles_json,
        is_chaos_mode=state.is_chaos_mode,
        persona_mode=state.persona_mode,
        source_personas_json=state.source_personas_json,
    )


def add_argument(state: DebateState, arg: Argument) -> dict[str, Any]:
    item = {
        "speaker": arg.speaker,
        "text": arg.text,
        "source": arg.source_link,
    }
    state.pending.append(item)
    return item


def round_complete(state: DebateState, speaker_count: int) -> bool:
    return len(state.pending) >= speaker_count


def finalize_round(state: DebateState) -> None:
    state.history.extend(state.pending)
    state.pending = []


def debate_finished(state: DebateState) -> bool:
    return state.round_index >= state.max_rounds


def advance_round(state: DebateState) -> None:
    state.round_index += 1


def parse_sources(articles_json: str) -> list[dict[str, Any]]:
    try:
        raw = json.loads(articles_json) if articles_json else []
        return raw if isinstance(raw, list) else []
    except json.JSONDecodeError:
        return []
