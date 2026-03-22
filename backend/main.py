"""FastAPI bridge for Pundit Protocol.

Run the API on port 8080 so it does not collide with uAgents: moderator on 8000,
pundit bureau on 8001.

    uvicorn backend.main:app --reload --port 8080
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from uagents.communication import send_message

from .agents.moderator import moderator, debate_queue
from .agents.pundit import create_bureau
from .agents.messages import DebateBrief
from .agents.personas import DEFAULT_SOURCE_SLOTS
from .schemas import DebateStartBody, DebateStartResponse
from .services.briefing import (
    articles_to_json,
    build_overview_from_articles,
    fetch_articles_for_topic,
)

DEBATE_GET_TIMEOUT = float(os.getenv("DEBATE_QUEUE_TIMEOUT", "120"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _drain_debate_queue_sync() -> None:
    while True:
        try:
            debate_queue.get_nowait()
        except queue.Empty:
            break


async def _drain_debate_queue() -> None:
    await asyncio.to_thread(_drain_debate_queue_sync)


async def _get_next_event() -> dict:
    def _get() -> dict:
        return debate_queue.get(timeout=DEBATE_GET_TIMEOUT)

    try:
        return await asyncio.to_thread(_get)
    except queue.Empty:
        raise HTTPException(
            status_code=504,
            detail="Timed out waiting for debate events.",
        )


def _build_debate_brief(body: DebateStartBody) -> tuple[DebateBrief, str, list]:
    articles = fetch_articles_for_topic(body.topic.strip())
    overview = build_overview_from_articles(body.topic, articles)
    source_json = (
        json.dumps(DEFAULT_SOURCE_SLOTS, ensure_ascii=False)
        if body.persona_mode == "sources"
        else "[]"
    )
    brief = DebateBrief(
        topic=body.topic.strip(),
        is_chaos_mode=body.is_chaos_mode,
        persona_mode=body.persona_mode,
        overview=overview,
        articles_json=articles_to_json(articles),
        source_personas_json=source_json,
    )
    return brief, overview, articles


def _run_moderator() -> None:
    moderator.run()


def _run_bureau() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        create_bureau().run()
    finally:
        if not loop.is_closed():
            loop.close()
        asyncio.set_event_loop(None)


@app.on_event("startup")
def startup_event():
    threading.Thread(target=_run_moderator, daemon=True).start()
    threading.Thread(target=_run_bureau, daemon=True).start()


@app.post("/debate", response_model=DebateStartResponse)
async def start_debate(body: DebateStartBody):
    await _drain_debate_queue()
    brief, overview, articles = await asyncio.to_thread(_build_debate_brief, body)
    await send_message(moderator.address, brief)
    return DebateStartResponse(
        overview=overview,
        sources=articles,
        persona_mode=body.persona_mode,
    )


@app.websocket("/ws/debate")
async def websocket_debate(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_json()
            try:
                body = DebateStartBody.model_validate(
                    {
                        "topic": raw.get("topic"),
                        "is_chaos_mode": raw.get("is_chaos_mode", False),
                        "persona_mode": raw.get("persona_mode", "mvp"),
                    }
                )
            except ValidationError as exc:
                await websocket.send_json({"type": "error", "error": exc.errors()})
                continue

            await _drain_debate_queue()
            brief, _, _ = await asyncio.to_thread(_build_debate_brief, body)
            await send_message(moderator.address, brief)

            while True:
                try:
                    event = await _get_next_event()
                except HTTPException as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": exc.detail,
                            "status_code": exc.status_code,
                        }
                    )
                    break
                await websocket.send_json(event)
                if event.get("type") == "summary":
                    break

    except WebSocketDisconnect:
        print("Client disconnected")
