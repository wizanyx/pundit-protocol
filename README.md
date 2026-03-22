# Pundit Protocol (BeachHacks Build)

Pundit Protocol is a multi-agent debate app that turns a topic into a fast, opinionated panel discussion.
A FastAPI + uAgents backend orchestrates the debate, and a Next.js frontend streams each turn in real time.

## What It Does

- Accepts a topic from the UI.
- Fetches fresh context (NewsAPI) for grounding.
- Runs a moderator + three pundit agents:
  - The Contrarian
  - The Hype Man
  - The Materialist
- Streams events over WebSocket (`overview` -> `turn` -> `summary`).
- Uses LLM generation for pundit turns and moderator synthesis, with safe fallback text if providers fail.

## Stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
- Backend: FastAPI, uAgents, Pydantic
- LLM Providers: Gemini (default) or OpenAI
- Data Source: NewsAPI

## Project Layout

```text
backend/
  main.py                  # FastAPI bridge + WS endpoint on :8080
  requirements.txt
  .env.example
  agents/
    moderator.py
    pundit.py
    messages.py
    personas.py
  services/
    llm.py
    briefing.py
    news_fetcher.py
    config.py
    events.py
    debate_engine.py

frontend/
  app/page.tsx             # Main debate UI + WebSocket client
  package.json
```

## Prerequisites

- Python 3.11+
- Node.js 20+
- npm

## Setup

### 1) Clone and create Python env

```bash
git clone https://github.com/wizanyx/pundit-protocol.git
cd pundit-protocol
python -m venv .venv
source .venv/bin/activate
```

### 2) Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

### 3) Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4) Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set real keys:

- `NEWSAPI_KEY`
- `GOOGLE_API_KEY` (for Gemini)
- `OPENAI_API_KEY` (optional unless using OpenAI provider)
- `LLM_PROVIDER=gemini` or `LLM_PROVIDER=openai`

## Run (Two Terminals)

### Terminal 1: Backend

```bash
cd /home/wizanyx/Documents/dev/pundit-protocol
source .venv/bin/activate
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

### Terminal 2: Frontend

```bash
cd /home/wizanyx/Documents/dev/pundit-protocol/frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

- Frontend: http://127.0.0.1:3000
- Backend docs: http://127.0.0.1:8080/docs

## How The Debate Flow Works

1. Frontend opens `ws://localhost:8080/ws/debate`.
2. Backend creates a `DebateBrief` with topic + article context.
3. Moderator emits initial `overview` event.
4. Pundits generate per-round arguments.
5. Backend streams `turn` events to frontend.
6. Moderator emits final `summary` event.

## API Contract (WebSocket Events)

- `overview`
  - Includes debate brief and sources.
- `turn`
  - Includes `speaker`, `text`, and `round`.
- `summary`
  - Includes final synthesis and optional sources.
- `error`
  - Includes a descriptive backend error payload.

## BeachHacks Demo Script (Quick)

1. Enter a current-events topic in the UI.
2. Show live streamed pundit turns arriving one by one.
3. Toggle persona mode/source mode to demonstrate behavior shifts.
4. End with moderator synthesis and cited source list.

## Troubleshooting

### I only see fallback/template responses

Likely causes:

- Gemini quota exhausted or key invalid.
- OpenAI key missing/invalid when fallback to OpenAI is attempted.
- `LLM_PROVIDER` set to a provider without a valid key.

Checks:

- Verify `backend/.env` keys are real values (not placeholders).
- Confirm backend logs during a run for provider/auth/quota failures.

### Import errors when starting backend

Run backend from repo root as a package module:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8080
```

Do not run from `backend/` with `uvicorn main:app` unless local import mode is specifically desired.

## Team Notes

Built for BeachHacks as a real-time AI debate experience with a multi-agent architecture and live streaming UI.
