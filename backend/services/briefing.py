"""Build moderator overview and safe NewsAPI fetch for the debate pipeline."""

from __future__ import annotations

import json
from typing import Any

from .news_fetcher import search_news


def fetch_articles_for_topic(topic: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return normalized articles; empty list if topic blank or NewsAPI unavailable."""
    if not topic.strip():
        return []
    try:
        return search_news(topic, limit=limit)
    except (ValueError, RuntimeError, OSError):
        return []


def build_overview_from_articles(topic: str, articles: list[dict[str, Any]]) -> str:
    """Deterministic overview string (no LLM) for POST/WS and moderator brief."""
    if not articles:
        return (
            f"No live headlines retrieved for “{topic.strip()}”. "
            "Pundits should reason from the topic and general knowledge."
        )
    lines = [
        f"- {(a.get('title') or 'Untitled').strip()}" for a in articles[:5]
    ]
    return (
        f"Topic: {topic.strip()}\n\n"
        f"Recent headlines (shared brief):\n" + "\n".join(lines)
    )


def articles_to_json(articles: list[dict[str, Any]]) -> str:
    return json.dumps(articles, ensure_ascii=False)


def articles_from_json(raw: str) -> list[dict[str, Any]]:
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []
