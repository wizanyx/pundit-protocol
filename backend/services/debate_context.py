from typing import Any


def build_context_snippets(
    items: list[dict[str, Any]], max_chars: int = 1500
) -> tuple[str, str | None]:
    """Turn normalized article dicts into a short prompt block and primary citation URL."""
    if not items:
        return "", None
    source_link = items[0].get("url")
    lines: list[str] = []
    for it in items[:5]:
        title = (it.get("title") or "").strip()[:220]
        snip = (it.get("snippet") or "").strip()[:400]
        lines.append(f"- {title}: {snip}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return text, source_link
