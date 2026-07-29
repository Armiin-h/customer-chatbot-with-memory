# Customer Chatbot with Memory

Multi-turn customer support chatbot for a fictional SaaS product (**NovaDesk**).
The agent keeps conversation context across turns, streams replies token-by-token,
and persists history in SQLite.

## Features

- Per-session memory via LangChain `RunnableWithMessageHistory` (last-N turns)
- SQLite-backed history that survives restarts
- NovaDesk support system prompt (plans, billing, refunds, export)
- JSON `POST /chat` and SSE `POST /chat/stream`
- React UI: bubbles, markdown, typing indicator, stop/retry, new-chat session reset
- Docker Compose (API + nginx frontend; Ollama on the host)

## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (local, default `llama3.2`) |
| Orchestration | LangChain LCEL + `RunnableWithMessageHistory` |
| Backend | FastAPI |
| History | SQLite (windowed per session) |
| Frontend | React + Vite |
| Deploy | Docker Compose |

See [docs/architecture.md](docs/architecture.md) for the request path and Docker topology.

## Prerequisites

- Python 3.11+
- Node.js 20+ (local UI)
- [Ollama](https://ollama.com/) with a chat model
- Docker Desktop (optional)

```bash
ollama pull llama3.2
```

## Quick start (local)

```bash
cp .env.example .env

# Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| UI (Vite) | http://localhost:5173 |

Keep `OLLAMA_BASE_URL=http://localhost:11434` for host runs. Compose forces
`host.docker.internal` inside the API container.

## Docker Compose

```bash
cp .env.example .env
# Ensure Ollama is running on the host
docker compose up --build
```

| Service | URL |
|---------|-----|
| UI | http://localhost:3000 |
| API | http://localhost:8000 |

The frontend build uses `VITE_API_BASE_URL=/api`. Nginx proxies `/api/*` to the
API container with buffering disabled so SSE stays live.

## Demo script

With the API running:

```bash
# From repo root
python scripts/demo_multiturn.py
python scripts/demo_multiturn.py --stream
```

The script creates a session, mentions the **Pro** plan, then asks what **that**
plan costs — the follow-up should answer **$12/user** if memory is working.

## Tests

```bash
cd backend
pytest -q
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + model + DB name |
| POST | `/sessions` | Create empty session |
| GET | `/sessions/{id}` | Session info + message count |
| DELETE | `/sessions/{id}` | Clear session history |
| POST | `/chat` | One chat turn (JSON `reply`) |
| POST | `/chat/stream` | One chat turn (SSE tokens) |

### SSE event shape

| `type` | Fields | Meaning |
|--------|--------|---------|
| `session` | `session_id` | Session used for this turn |
| `token` | `content` | Next text chunk |
| `done` | `session_id`, `message_count` | Stream finished |
| `error` | `detail` | Upstream failure |

## Project layout

```
backend/app/          FastAPI + LangChain + SQLite memory
backend/tests/        Memory and API unit tests
frontend/src/         React chat UI (api, markdown, App)
scripts/demo_multiturn.py
docs/architecture.md
docker-compose.yml
```

## License

MIT
