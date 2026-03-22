import json

from uagents import Agent, Context, Bureau

try:
    from ..services.debate_context import build_context_snippets
    from ..services.briefing import articles_from_json
    from .messages import Argument, DebateTurn
    from .personas import resolve_personality
    from .local_resolver import LocalResolver
except ImportError:
    # Allow running from backend/ with non-package imports
    from services.debate_context import build_context_snippets
    from services.briefing import articles_from_json
    from agents.messages import Argument, DebateTurn
    from agents.personas import resolve_personality
    from agents.local_resolver import LocalResolver

PUNDIT_CONFIGS = [
    {
        "name": "The_Contrarian",
        "seed": "pundit_contrarian_seed",
        "personality": "You are extremely skeptical. No matter the topic, find the hidden flaws and risks.",
    },
    {
        "name": "The_Hype_Man",
        "seed": "pundit_hype_seed",
        "personality": "You are an eternal optimist. Focus only on progress, innovation, and 'to the moon' energy.",
    },
    {
        "name": "The_Materialist",
        "seed": "pundit_materialist_seed",
        "personality": "You analyze everything through the lens of class struggle and economic resource distribution.",
    },
]

LOCAL_RESOLVER = LocalResolver(default_endpoint="http://127.0.0.1:8000/submit")

def _trim(text: str, max_len: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _pick_fact(articles: list[dict], slot_index: int, round_index: int) -> tuple[str, str, str]:
    if not articles:
        return "", "", ""
    # Rotate evidence by agent slot + round so each agent gets a different headline.
    start = (max(0, slot_index) + max(1, round_index) - 1) % len(articles)
    ordered = articles[start:] + articles[:start]
    for art in ordered:
        title = (art.get("title") or "").strip()
        snippet = (art.get("snippet") or "").strip()
        source = (art.get("source") or "").strip()
        if title or snippet:
            return title, snippet, source
    return "", "", ""


def _topic_phrase(topic: str) -> str:
    t = (topic or "").strip()
    if not t:
        return "this"
    if len(t) <= 80:
        return t
    return t[:77].rstrip() + "…"


def _style_key(agent_name: str, personality: str) -> str:
    p = (personality or "").lower()
    if "wsj_business" in p:
        return "wsj"
    if "guardian_progressive" in p:
        return "guardian"
    if "fox_populist" in p:
        return "fox"
    # fall back to agent identity
    if agent_name == "The_Contrarian":
        return "contrarian"
    if agent_name == "The_Hype_Man":
        return "hype"
    if agent_name == "The_Materialist":
        return "materialist"
    return "analytical"


def _mvp_argument(
    topic: str,
    agent_name: str,
    personality: str,
    fact_title: str,
    fact_snippet: str,
    chaos: bool,
    round_index: int,
    prior: str,
) -> str:
    style = _style_key(agent_name, personality)
    topic_phrase = _topic_phrase(topic)
    lead_map = {
        "wsj": "Investor lens:",
        "guardian": "Distribution lens:",
        "fox": "Populist lens:",
        "contrarian": "Contrarian lens:",
        "hype": "Bull case:",
        "materialist": "Class lens:",
        "analytical": "Risk lens:",
    }
    evidence_prefix_map = {
        "wsj": "Market signal:",
        "guardian": "Household reality:",
        "fox": "Kitchen-table signal:",
        "contrarian": "Hidden risk:",
        "hype": "Momentum read:",
        "materialist": "Power signal:",
        "analytical": "Signal:",
    }
    claim_map = {
        "wsj": [
            f"Markets want clarity on {topic_phrase}; stability beats theatrics and keeps risk pricing honest.",
            f"Policy credibility matters more than spectacle on {topic_phrase}; consistency helps planning and capital allocation.",
            f"On {topic_phrase}, patience signals discipline and avoids whipsaw risk."
        ],
        "guardian": [
            f"On {topic_phrase}, the burden is sliding down the ladder; households absorb costs while asset owners stay cushioned.",
            f"This stance on {topic_phrase} protects balance sheets at the top while everyone else gets squeezed.",
            f"The distributional impact of {topic_phrase} is the story—who pays and who gets shielded."
        ],
        "fox": [
            f"Elites are gaming the message on {topic_phrase}; Main Street is the one paying.",
            f"The official line on {topic_phrase} is cover while costs rise for families.",
            f"Don’t be fooled by optics on {topic_phrase}—real people carry the bill."
        ],
        "contrarian": [
            f"The consensus on {topic_phrase} masks fragility; the official line misprices risk.",
            f"Stability talk around {topic_phrase} hides weakness—the risk is being downplayed.",
            f"A steady hand on {topic_phrase} could be the wrong bet if pressures re-ignite."
        ],
        "hype": [
            f"On {topic_phrase}, the momentum is real; pessimism is overstated.",
            f"The path on {topic_phrase} is better than it looks—don’t bet against forward motion.",
            f"Patience around {topic_phrase} keeps the runway intact and preserves upside."
        ],
        "materialist": [
            f"On {topic_phrase}, capital is protected first; workers bear the squeeze.",
            f"{topic_phrase} is class policy in slow motion: debt holders win, wage earners wait.",
            f"The cost of ‘stability’ in {topic_phrase} is paid by labor, not capital."
        ],
        "analytical": [
            f"On {topic_phrase}, second-order effects matter more than headlines.",
            f"Risk management on {topic_phrase} favors patience until the trend is clearer.",
            f"The least-bad option on {topic_phrase} is to wait for data to break the tie."
        ],
    }
    rebuttal_map = {
        "wsj": [
            "Ignore the noise—watch incentives and pricing signals, not theater.",
            "Signal matters: credibility beats short-term applause.",
        ],
        "guardian": [
            "Don’t pretend this is neutral—who wins and loses is the whole story.",
            "The ‘neutral’ frame hides the transfer of pain downward.",
        ],
        "fox": [
            "Don’t buy the spin; messaging isn’t reality.",
            "Main Street doesn’t live in press releases.",
        ],
        "contrarian": [
            "Ignore the noise—the fundamentals will punish complacency.",
            "The market will punish complacency faster than officials admit.",
        ],
        "hype": [
            "The doom loop is overstated; momentum still wins.",
            "Risk is real, but upside is being ignored.",
        ],
        "materialist": [
            "The winners are clear; the rest get told to be patient.",
            "Policy always has a class bias—this one too.",
        ],
        "analytical": [
            "Data will decide; headlines won’t.",
            "The trend matters more than the noise.",
        ],
    }
    claim_list = claim_map.get(style, claim_map["analytical"])
    claim = claim_list[(max(1, round_index) - 1) % len(claim_list)]

    if chaos:
        claim = claim.replace("The Fed", "The Fed") + " This is brinkmanship dressed up as prudence."

    evidence = ""
    if fact_title:
        prefix = evidence_prefix_map.get(style, "Signal:")
        evidence = f"{prefix} {fact_title.strip()}."
    if fact_snippet:
        evidence = f"{evidence} {_trim(fact_snippet, 140)}".strip()

    rebut_list = rebuttal_map.get(style, rebuttal_map["analytical"])
    rebuttal = rebut_list[(max(1, round_index) - 1) % len(rebut_list)]
    if chaos and style not in {"fox", "guardian"}:
        rebuttal = "Don’t be fooled by the messaging—policy is chasing optics, not reality."

    if prior:
        last_line = prior.splitlines()[-1] if prior else ""
        if last_line:
            rebuttal = f"Rebuttal: {rebuttal}"

    lead = lead_map.get(style, "Lens:")
    if style == "wsj":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Bottom line: {rebuttal}"]
    elif style == "guardian":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Demand: {rebuttal}"]
    elif style == "fox":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Verdict: {rebuttal}"]
    elif style == "contrarian":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Risk: {rebuttal}"]
    elif style == "hype":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Upside: {rebuttal}"]
    elif style == "materialist":
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Power: {rebuttal}"]
    else:
        parts = [f"{lead} {claim}", f"{evidence}" if evidence else "", f"Takeaway: {rebuttal}"]

    return " ".join([p for p in parts if p])


def create_bureau() -> Bureau:
    bureau = Bureau(port=8001, endpoint=["http://127.0.0.1:8001/submit"])

    for slot_index, config in enumerate(PUNDIT_CONFIGS):
        pundit = Agent(
            name=config["name"],
            seed=config["seed"],
            resolve=LOCAL_RESOLVER,
        )

        @pundit.on_event("startup")
        async def set_personality(
            ctx: Context,
            personality: str = config["personality"],
        ):
            ctx.storage.set("personality", personality)
            ctx.logger.info(f"{ctx.agent.name} is online at {ctx.agent.address}")

        @pundit.on_message(model=DebateTurn)
        async def generate_response(
            ctx: Context,
            sender: str,
            msg: DebateTurn,
            idx: int = slot_index,
            agent_name: str = config["name"],
        ):
            base_personality = ctx.storage.get("personality")
            personality = resolve_personality(
                agent_name,
                msg.persona_mode,
                idx,
                msg.source_personas_json,
                base_personality,
            )
            ctx.logger.info(f"{ctx.agent.name} round {msg.round_index} on: {msg.topic}")
            ctx.storage.set("last_topic", msg.topic)
            ctx.storage.set("last_chaos_mode", msg.is_chaos_mode)
            ctx.storage.set("last_persona_mode", msg.persona_mode)

            articles = articles_from_json(msg.articles_json)
            context, source_link = build_context_snippets(articles)

            prior = ""
            try:
                hist = json.loads(msg.history_json) if msg.history_json else []
                if isinstance(hist, list) and hist:
                    bits = []
                    for h in hist[-8:]:
                        sp = h.get("speaker", "?")
                        tx = (h.get("text") or "")[:400]
                        bits.append(f"- {sp}: {tx}")
                    prior = "\n".join(bits)
            except json.JSONDecodeError:
                prior = ""

            chaos = msg.is_chaos_mode or (msg.persona_mode or "").lower() == "chaos"
            fact_title, fact_snippet, _ = _pick_fact(articles, idx, msg.round_index)
            reply = _mvp_argument(
                topic=msg.topic,
                agent_name=ctx.agent.name,
                personality=personality,
                fact_title=fact_title,
                fact_snippet=fact_snippet,
                chaos=chaos,
                round_index=msg.round_index,
                prior=prior,
            )

            await ctx.send(
                sender,
                Argument(speaker=ctx.agent.name, text=reply, source_link=source_link),
            )

        bureau.add(pundit)

    return bureau


if __name__ == "__main__":
    create_bureau().run()
