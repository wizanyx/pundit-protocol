import json
import queue
from typing import Any

from uagents import Agent, Context

from .local_resolver import LocalResolver

from .messages import Argument, DebateBrief

if __package__:
    from ..services.briefing import articles_from_json, build_overview_from_articles
    from ..services.config import DEBATE_ROUNDS
    from ..services.debate_engine import (
        DebateState,
        add_argument,
        advance_round,
        build_turn_message,
        create_state,
        debate_finished,
        finalize_round,
        parse_sources,
        round_complete,
    )
    from ..services.events import overview_event, summary_event, turn_event
    from ..services.llm import call_llm_text
else:
    from services.briefing import articles_from_json, build_overview_from_articles
    from services.config import DEBATE_ROUNDS
    from services.debate_engine import (
        DebateState,
        add_argument,
        advance_round,
        build_turn_message,
        create_state,
        debate_finished,
        finalize_round,
        parse_sources,
        round_complete,
    )
    from services.events import overview_event, summary_event, turn_event
    from services.llm import call_llm_text

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

MAX_DEBATE_ROUNDS = DEBATE_ROUNDS

# Single active debate (hackathon MVP).
_debate_state: DebateState | None = None


def _call_moderator_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float,
    max_tokens: int,
) -> str | None:
    return call_llm_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        profile="moderator",
    )


def _article_headline_block(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "No headlines available."
    lines: list[str] = []
    for idx, art in enumerate(articles[:5], start=1):
        title = (art.get("title") or "Untitled").strip()
        source = (art.get("source") or "Unknown source").strip()
        snippet = (art.get("snippet") or "").strip()
        line = f"{idx}. {title} ({source})"
        if snippet:
            line += f" - {snippet[:220]}"
        lines.append(line)
    return "\n".join(lines)


def _generate_overview(topic: str, articles_json: str, fallback: str) -> str:
    articles = articles_from_json(articles_json)
    fallback_text = fallback or build_overview_from_articles(topic, articles)
    prompt = (
        "Create a concise neutral briefing for a live political/economic debate panel. "
        "Use only the provided headlines. Keep it factual and avoid conclusions. "
        "Output 2 short paragraphs and then 3 bullet points for what the panel should watch."
    )
    user = f"Topic: {topic.strip()}\n\nHeadlines:\n{_article_headline_block(articles)}"
    generated = _call_moderator_llm(
        prompt,
        user,
        temperature=0.25,
        max_tokens=320,
    )
    return generated or fallback_text


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    cleaned = text.replace("\n", " ").strip()
    # Remove common lead labels to keep summaries clean.
    prefixes = [
        "Investor lens:",
        "Distribution lens:",
        "Populist lens:",
        "Contrarian lens:",
        "Bull case:",
        "Class lens:",
        "Risk lens:",
        "Lens:",
        "Bottom line:",
        "Demand:",
        "Verdict:",
        "Risk:",
        "Upside:",
        "Power:",
        "Takeaway:",
        "Rebuttal:",
    ]
    for p in prefixes:
        if cleaned.startswith(p):
            cleaned = cleaned[len(p) :].strip()
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


def _generate_final_summary(
    topic: str, history: list[dict[str, Any]], articles_json: str
) -> str:
    fallback = _build_summary(topic, history, articles_json)
    articles = articles_from_json(articles_json)
    if history:
        argument_lines = []
        for item in history[-18:]:
            speaker = item.get("speaker") or "Panelist"
            text = (item.get("text") or "").strip()
            if text:
                argument_lines.append(f"- {speaker}: {text[:420]}")
        argument_block = "\n".join(argument_lines)
    else:
        argument_block = "No arguments were captured."

    prompt = (
        "You are the debate moderator writing the final summary for end users. "
        "Synthesize key agreements and disagreements from the transcript. "
        "Keep it clear and grounded in provided debate statements and headlines. "
        "Output 3 short paragraphs followed by a final line that starts with 'Net takeaway:'."
    )
    user = (
        f"Topic: {topic.strip()}\n\n"
        f"Headlines:\n{_article_headline_block(articles)}\n\n"
        f"Debate transcript:\n{argument_block}"
    )
    generated = _call_moderator_llm(
        prompt,
        user,
        temperature=0.35,
        max_tokens=420,
    )
    return generated or fallback


async def _broadcast_round(ctx: Context, state: DebateState) -> None:
    turn = build_turn_message(state)
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
    ctx.logger.info(
        f"New debate: {msg.topic} (mode={msg.persona_mode}, chaos={msg.is_chaos_mode})"
    )
    ctx.storage.set("last_topic", msg.topic)
    ctx.storage.set("last_chaos_mode", msg.is_chaos_mode)
    ctx.storage.set("last_persona_mode", msg.persona_mode)

    overview = _generate_overview(msg.topic, msg.articles_json, msg.overview)

    _debate_state = create_state(msg, overview=overview, max_rounds=MAX_DEBATE_ROUNDS)
    sources = parse_sources(msg.articles_json)
    debate_queue.put(
        overview_event(
            topic=msg.topic,
            overview=overview,
            sources=sources,
            persona_mode=msg.persona_mode,
            is_chaos_mode=msg.is_chaos_mode,
        )
    )

    await _broadcast_round(ctx, _debate_state)


@moderator.on_message(model=Argument)
async def collect_arguments(ctx: Context, sender: str, msg: Argument):
    global _debate_state
    ctx.logger.info(f"Argument received from {msg.speaker} (round)")
    if _debate_state is None:
        return

    state = _debate_state
    add_argument(state, msg)
    debate_queue.put(
        turn_event(
            round_index=state.round_index,
            speaker=msg.speaker,
            text=msg.text,
            source=msg.source_link,
        )
    )

    if not round_complete(state, len(PUNDIT_ADDRESSES)):
        return

    finalize_round(state)

    if debate_finished(state):
        conclusion = _generate_final_summary(
            state.topic,
            state.history,
            state.articles_json,
        )
        debate_queue.put(
            summary_event(
                topic=state.topic,
                conclusion=conclusion,
                arguments=state.history,
            )
        )
        _debate_state = None
        return

    advance_round(state)
    await _broadcast_round(ctx, state)


# Thread-safe bridge: FastAPI runs on the main event loop; the moderator runs in a worker thread.
debate_queue: queue.Queue[dict] = queue.Queue()
