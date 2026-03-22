import json
import os
import queue
from typing import Any

from uagents import Agent, Context

from .messages import Argument, DebateBrief, DebateTurn

MODERATOR_SEED = "beachhacks_pundit_moderator_2026"
moderator = Agent(
    name="moderator",
    seed=MODERATOR_SEED,
    port=8000,
    endpoint=["http://127.0.0.1:8000/submit"],
)

PUNDIT_ADDRESSES = [
    "agent1q2s3982hlxqn5mv60aw9lj5k9jqyf34t7sklaxrwy0dzzfvua5s5s2cx58c",
    "agent1qggjtjmwxdlxv2k2a290fn3e4ke7787lgjgnn92rusv88tnd29k6udp0y57",
    "agent1qt0twdy5lw6wfmj7dg2gpg5hg2q8lrz4c5uwgapqfprdtthvq0pmyts3ex9",
]

MAX_DEBATE_ROUNDS = max(1, int(os.getenv("DEBATE_ROUNDS", "2")))

# Single active debate (hackathon MVP).
_debate_state: dict[str, Any] | None = None


def _stub_conclusion(topic: str, history: list[dict[str, Any]]) -> str:
    speakers = [h.get("speaker", "?") for h in history[-6:]]
    return (
        f"Synthesis for “{topic}”: the panel surfaced competing frames from {', '.join(speakers)}. "
        "No single narrative dominated; readers should weigh evidence and incentives across rounds."
    )


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
        conclusion = _stub_conclusion(state["topic"], state["history"])
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
