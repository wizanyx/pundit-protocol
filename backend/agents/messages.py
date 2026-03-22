from uagents import Model


class DebateBrief(Model):
    """Orchestrator → moderator: kick off a debate with a shared news brief."""

    topic: str
    is_chaos_mode: bool
    persona_mode: str  # mvp | chaos | sources
    overview: str
    articles_json: str
    source_personas_json: str = "[]"


class DebateTurn(Model):
    """Moderator → pundit: one turn in a round with shared context and history."""

    topic: str
    round_index: int
    history_json: str
    overview: str
    articles_json: str
    is_chaos_mode: bool
    persona_mode: str
    source_personas_json: str = "[]"


class Argument(Model):
    """Pundit -> moderator: one debate turn text with optional citation link."""

    speaker: str
    text: str
    source_link: str | None = None
