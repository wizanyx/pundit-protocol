import json

from uagents import Agent, Context, Bureau

from ..services.debate_context import build_context_snippets
from ..services.briefing import articles_from_json
from .messages import Argument, DebateTurn
from .personas import resolve_personality

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


def create_bureau() -> Bureau:
    bureau = Bureau(port=8001, endpoint=["http://127.0.0.1:8001/submit"])

    for slot_index, config in enumerate(PUNDIT_CONFIGS):
        pundit = Agent(
            name=config["name"],
            seed=config["seed"],
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

            parts = [
                f"[{ctx.agent.name} | round {msg.round_index}]",
                f"Persona lens: {personality}",
                "",
                "Moderator overview:",
                msg.overview,
            ]
            if context:
                parts.extend(["", "Article snippets:", context])
            if prior:
                parts.extend(["", "Prior debate (respond / rebut):", prior])
            parts.extend(
                [
                    "",
                    f"Your move: argue about “{msg.topic}” from your persona. "
                    "Be sharp and distinct from the other pundits.",
                ]
            )
            reply = "\n".join(parts)

            await ctx.send(
                sender,
                Argument(speaker=ctx.agent.name, text=reply, source_link=source_link),
            )

        bureau.add(pundit)

    return bureau


if __name__ == "__main__":
    create_bureau().run()
