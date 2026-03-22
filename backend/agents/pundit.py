import json

from uagents import Agent, Context, Bureau

try:
    from ..services.debate_context import build_context_snippets
    from ..services.briefing import articles_from_json
    from ..services.llm import call_llm_text
    from .messages import Argument, DebateTurn
    from .personas import resolve_personality
    from .local_resolver import LocalResolver
except ImportError:
    # Allow running from backend/ with non-package imports
    from services.debate_context import build_context_snippets
    from services.briefing import articles_from_json
    from services.llm import call_llm_text
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


def _fallback_argument(
    agent_name: str, topic: str, personality: str, context: str, prior: str
) -> str:
    topic_clean = (topic or "this topic").strip()
    context_line = ""
    if context:
        lines = [ln.strip("- ").strip() for ln in context.splitlines() if ln.strip()]
        if lines:
            context_line = lines[0][:220]

    rebut = ""
    if prior:
        prior_lines = [ln.strip() for ln in prior.splitlines() if ln.strip()]
        if prior_lines:
            rebut = prior_lines[-1][:180]

    persona_lower = (personality or "").lower()
    if "skept" in persona_lower or "contrarian" in agent_name.lower():
        opener = f"I am not buying the easy story on {topic_clean}."
        stance = "The hidden downside is being ignored, and the consensus is too comfortable."
    elif "optim" in persona_lower or "hype" in agent_name.lower():
        opener = f"There is more upside in {topic_clean} than people are admitting."
        stance = "The momentum case is stronger than the fear cycle, and over-caution is the bigger risk."
    else:
        opener = f"The core issue in {topic_clean} is who carries the cost and who captures the gain."
        stance = (
            "Power and incentives shape the outcome more than surface-level narratives."
        )

    evidence = (
        f"Evidence anchor: {context_line}."
        if context_line
        else "Evidence anchor: limited context, so weight incentives and behavior signals."
    )
    rebuttal = (
        f"Direct rebuttal: {rebut}."
        if rebut
        else "Direct rebuttal: the previous turn underestimates second-order effects."
    )
    return f"{opener} {stance} {evidence} {rebuttal}"


def _generate_argument_with_llm(
    *,
    agent_name: str,
    topic: str,
    personality: str,
    overview: str,
    context: str,
    prior: str,
    round_index: int,
) -> str:
    system_prompt = (
        "You are a debate pundit. "
        "Stay in persona and produce one sharp turn for a live panel debate. "
        "The topic may be serious, absurd, or a gag prompt, so adapt tone without breaking persona. "
        "Be specific, persuasive, and concise. "
        "Use available context, rebut prior claims if present, and avoid meta commentary. "
        "Return only the debate message text."
    )
    user_prompt = (
        f"Agent name: {agent_name}\n"
        f"Round: {round_index}\n"
        f"Topic: {topic}\n\n"
        f"Persona:\n{personality}\n\n"
        f"Moderator overview:\n{overview}\n\n"
        f"Article snippets:\n{context or 'None'}\n\n"
        f"Prior debate (for rebuttal):\n{prior or 'None'}\n\n"
        "Write 1 compact paragraph (2-5 sentences). If the topic is playful, witty language is allowed."
    )

    text = call_llm_text(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.8,
        max_tokens=220,
        profile="pundit",
    )
    if text:
        return text

    return _fallback_argument(agent_name, topic, personality, context, prior)


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

            reply = _generate_argument_with_llm(
                agent_name=ctx.agent.name,
                topic=msg.topic,
                personality=personality,
                overview=msg.overview,
                context=context,
                prior=prior,
                round_index=msg.round_index,
            )

            await ctx.send(
                sender,
                Argument(speaker=ctx.agent.name, text=reply, source_link=source_link),
            )

        bureau.add(pundit)

    return bureau


if __name__ == "__main__":
    create_bureau().run()
