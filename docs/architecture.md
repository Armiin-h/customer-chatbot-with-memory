# Architecture

## Overview

NovaDesk Support is a multi-turn customer chatbot. The browser talks to a FastAPI
service that wraps a LangChain runnable with per-session message history. History
is stored in SQLite with a last-N turn window. Tokens stream back over SSE.

```text
┌────────────────────┐     SSE / JSON      ┌──────────────────────────┐
│  React (Vite) UI   │ ──────────────────► │  FastAPI                 │
│  bubbles + stream  │ ◄────────────────── │  /chat, /chat/stream     │
└────────────────────┘                     │  /sessions, /health      │
                                           └────────────┬─────────────┘
                                                        │
                         ┌──────────────────────────────┼──────────────────────────────┐
                         │                              ▼                              │
                         │                 RunnableWithMessageHistory                  │
                         │                              │                              │
                         │              ┌───────────────┴───────────────┐              │
                         │              ▼                               ▼              │
                         │     SQLite windowed store              ChatOllama           │
                         │     (sessions + messages)              (local Ollama)       │
                         └─────────────────────────────────────────────────────────────┘
```

## Request path (streaming)

1. UI `POST /chat/stream` with `{ session_id?, message }`.
2. API ensures a session row exists, then runs `chain.astream(...)`.
3. `RunnableWithMessageHistory` loads prior turns from SQLite into the prompt.
4. Each model token is emitted as an SSE `token` event.
5. After completion, human + AI messages are persisted and older turns beyond
   `MEMORY_WINDOW_SIZE` are trimmed.

## Docker topology

- `api` container: FastAPI on `:8000`, volume `chat_data` for SQLite.
- `frontend` container: nginx serves the Vite build on `:3000` and proxies
  `/api/*` → `api:8000` (SSE buffering disabled).
- Ollama stays on the host; the API reaches it at `host.docker.internal:11434`.

## Memory choices

| Concern | Choice |
|---------|--------|
| Session isolation | UUID `session_id` per chat thread |
| Context bound | Last N turns (`MEMORY_WINDOW_SIZE`) |
| Persistence | SQLite `sessions` + `chat_messages` |
| Scale note | Swap SQLite for Redis/Postgres for multi-instance deploys |
