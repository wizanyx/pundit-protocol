"""Pydantic v2 models for FastAPI HTTP layer (not uAgents)."""

from typing import Literal

from pydantic import BaseModel, Field


class DebateStartBody(BaseModel):
    topic: str = Field(..., min_length=1)
    is_chaos_mode: bool = False
    persona_mode: Literal["mvp", "chaos", "sources"] = "mvp"


class DebateStartResponse(BaseModel):
    status: str = "success"
    overview: str
    sources: list[dict]
    persona_mode: str
