import json
import os
import queue
from typing import Any

from uagents import Agent, Context

from .local_resolver import LocalResolver

from .messages import Argument, DebateBrief, DebateTurn

MODERATOR_SEED = "beachhacks_pundit_moderator_2026"
moderator = Agent(
    name="moderator",
    seed=MODERATOR_SEED,
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"],
    resolve=LocalResolver(default_endpoint="http://127.0.0.1:8001/submit"),
)

PUNDIT_ADDRESSES = [
    "agent1q2s3982hlxqn5mv60aw9lj5k9jqyf34t7sklaxrwy0dzzfvua5s5s2cx58c",
    "agent1qggjtjmwxdlxv2k2a290fn3e4ke7787lgjgnn92rusv88tnd29k6udp0y57",
    "agent1qt0twdy5lw6wfmj7dg2gpg5hg2q8lrz4c5uwgapqfprdtthvq0pmyts3ex9",
]

MAX_DEBATE_ROUNDS = max(1, int(os.getenv("DEBATE_ROUNDS", "2")))

# Single active debate (hackathon MVP).
_debate_state: dict[str, Any] | None = None


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\n", " ").strip()
    # Remove common lead labels to keep summaries clean.
    prefixes = [
        "Investor lens:", "Distribution lens:", "Populist lens:", "Contrarian lens:",
        "Bull case:", "Class lens:", "Risk lens:", "Lens:", "Bottom line:", "Demand:",
        "Verdict:", "Risk:", "Upside:", "Power:", "Takeaway:", "Rebuttal:"
    ]
    for p in prefixes:
        if cleaned.startswith(p):
            cleaned = cleaned[len(p):].strip()
            break
    parts = cleaned.split(".")
    return parts[0].strip() if parts else cleaned


def _theme_from_text(text: str) -> str | None:
    t = (text or "").lower()
    if "investor lens:" in t or "market" in t or "capital allocation" in t:
        return "Market-focused view emphasized stability and credibility."
    if "distribution lens:" in t or "household" in t or "burden" in t:
        return "Distributional view stressed who bears the costs."
    if "populist lens:" in t or "main street" in t or "elite" in t:
        return "Populist view framed it as elite spin versus families."
    if "contrarian lens:" in t or "fragility" in t or "misprice" in t:
        return "Contrarian view warned hidden risks are being masked."
    if "bull case:" in t or "momentum" in t or "upside" in t:
        return "Bull case argued momentum and upside are underestimated."
    if "class lens:" in t or "labor" in t or "workers" in t:
        return "Class view focused on power dynamics and labor costs."
    if "risk lens:" in t or "second-order" in t or "risk management" in t:
        return "Analytical view highlighted second‑order effects and risk management."
    return None


def _build_summary(
    topic: str,
    history: list[dict[str, Any]],
    articles_json: str,
) -> str:
    # Pull 2 headline anchors if available
    headlines: list[str] = []
    try:
        sources = json.loads(articles_json) if articles_json else []
        if isinstance(sources, list):
            for item in sources[:2]:
                title = (item.get("title") or "").strip()
                if title:
                    headlines.append(title)
    except json.JSONDecodeError:
        headlines = []

    # Extract themes from up to 3 unique speakers (most recent round)
    seen = set()
    takes: list[str] = []
    themes: list[str] = []
    for h in reversed(history):
        sp = h.get("speaker") or "Panelist"
        if sp in seen:
            continue
        seen.add(sp)
        raw = h.get("text") or ""
        tx = _first_sentence(raw)
        if tx:
            takes.append(tx)
        theme = _theme_from_text(raw)
        if theme and theme not in themes:
            themes.append(theme)
        if len(takes) >= 3:
            break
    takes.reverse()

    topic_clean = (topic or "").strip()
    topic_phrase = topic_clean if topic_clean else "the topic"

    intro_templates = [
        f"Panel snapshot on “{topic_phrase}”:",
        f"Debate summary — “{topic_phrase}”:",
        f"Where the panel landed on “{topic_phrase}”:",
    ]
    intro = intro_templates[abs(hash(topic_phrase)) % len(intro_templates)]

    parts: list[str] = [intro]
    if themes:
        parts.append(" ".join(themes[:3]))
    elif takes:
        joined_takes = ". ".join(takes)
        if not joined_takes.endswith("."):
            joined_takes += "."
        parts.append(joined_takes)
    else:
        parts.append("The panel debated divergent risks and incentives.")
    if headlines:
        parts.append("News anchors: " + "; ".join(headlines) + ".")

    takeaway_templates = [
        f"Net takeaway: {topic_phrase} is contested; watch incentives, second‑order effects, and credibility signals.",
        f"Net takeaway: on {topic_phrase}, near‑term headlines matter less than structural signals and follow‑through.",
        f"Net takeaway: the debate on {topic_phrase} splits on risk vs. upside; expect volatility around key signals.",
        f"Net takeaway: {topic_phrase} hinges on execution and trust, not just messaging.",
    ]
    idx = abs(hash(topic_phrase)) % len(takeaway_templates)
    parts.append(takeaway_templates[idx])
    return " ".join(parts)


async def _broadcast_round(ctx: Context, state: dict[str, Any]) -> None:
    history_json = json.dumps(state["history"], ensure_ascii=False)
    turn = DebateTurn(
        topic=state["topic"],
        round_index=state["round_index"],
        history_json=history_json,
        overview=state["overview"],
        articles_json=state["articles_json"],
        is_chaos_mode=state["is_chaos_mode"],
        persona_mode=state["persona_mode"],
        source_personas_json=state["source_personas_json"],
    )
    for addr in PUNDIT_ADDRESSES:
        await ctx.send(addr, turn)


@moderator.on_event("startup")
async def introduce(ctx: Context):
    ctx.logger.info(f"Moderator is online at {moderator.address}")
    ctx.logger.info(
        "Almanac: uAgents registers this address with the resolver on startup when "
        "network/ledger access is available; use Agentverse mailbox for remote discovery."
    )


@moderator.on_message(model=DebateBrief)
async def handle_debate_brief(ctx: Context, sender: str, msg: DebateBrief):
    global _debate_state
    ctx.logger.info(f"New debate: {msg.topic} (mode={msg.persona_mode}, chaos={msg.is_chaos_mode})")
    ctx.storage.set("last_topic", msg.topic)
    ctx.storage.set("last_chaos_mode", msg.is_chaos_mode)
    ctx.storage.set("last_persona_mode", msg.persona_mode)

    _debate_state = {
        "topic": msg.topic,
        "overview": msg.overview,
        "articles_json": msg.articles_json,
        "is_chaos_mode": msg.is_chaos_mode,
        "persona_mode": msg.persona_mode,
        "source_personas_json": msg.source_personas_json or "[]",
        "round_index": 1,
        "history": [],
        "pending": [],
        "max_rounds": MAX_DEBATE_ROUNDS,
    }

    try:
        sources = json.loads(msg.articles_json) if msg.articles_json else []
    except json.JSONDecodeError:
        sources = []
    debate_queue.put(
        {
            "type": "overview",
            "overview": msg.overview,
            "sources": sources if isinstance(sources, list) else [],
            "topic": msg.topic,
            "persona_mode": msg.persona_mode,
            "is_chaos_mode": msg.is_chaos_mode,
        }
    )

    await _broadcast_round(ctx, _debate_state)


@moderator.on_message(model=Argument)
async def collect_arguments(ctx: Context, sender: str, msg: Argument):
    global _debate_state
    ctx.logger.info(f"Argument received from {msg.speaker} (round)")
    if _debate_state is None:
        return

    state = _debate_state
    state["pending"].append(
        {
            "speaker": msg.speaker,
            "text": msg.text,
            "source": msg.source_link,
        }
    )
    debate_queue.put(
        {
            "type": "turn",
            "round": state["round_index"],
            "speaker": msg.speaker,
            "text": msg.text,
            "source": msg.source_link,
        }
    )

    if len(state["pending"]) < len(PUNDIT_ADDRESSES):
        return

    state["history"].extend(state["pending"])
    state["pending"] = []

    if state["round_index"] >= state["max_rounds"]:
        conclusion = _build_summary(state["topic"], state["history"], state["articles_json"])
        debate_queue.put(
            {
                "type": "summary",
                "topic": state["topic"],
                "conclusion": conclusion,
                "arguments": state["history"],
            }
        )
        _debate_state = None
        return

    state["round_index"] += 1
    await _broadcast_round(ctx, state)


# Thread-safe bridge: FastAPI runs on the main event loop; the moderator runs in a worker thread.
debate_queue: queue.Queue[dict] = queue.Queue()
