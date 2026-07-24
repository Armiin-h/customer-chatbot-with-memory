# Customer Chatbot with Memory

Multi-turn customer support chatbot that keeps conversation context across turns.
Built with FastAPI, React, LangChain, and Ollama.

## Features

- Per-session conversation memory (`RunnableWithMessageHistory`, last-N turns)
- NovaDesk support-agent system prompt
- Session create / inspect / reset endpoints
- Non-streaming `POST /chat` (streaming lands next)
- React chat UI with live typing (upcoming)
- SQLite-backed history (upcoming)
- Docker Compose for API + frontend

## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (local) |
| Orchestration | LangChain (`RunnableWithMessageHistory`) |
| Backend | FastAPI |
| History | In-memory (SQLite next) |
| Frontend | React + Vite |
| Deploy | Docker Compose |

## Prerequisites

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) with a chat model (default: `llama3.2`)
- Docker Desktop (optional, for compose)

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

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  
- UI: http://localhost:5173  

For local runs, keep `OLLAMA_BASE_URL=http://localhost:11434` in `.env`.
Compose overrides that to `host.docker.internal` inside the API container.

## Try multi-turn memory (curl)

```bash
# Create a session
curl -s -X POST http://localhost:8000/sessions

# Chat (reuse session_id from the response)
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"YOUR_SESSION_ID\", \"message\": \"I upgraded to the Pro plan yesterday.\"}"

curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"YOUR_SESSION_ID\", \"message\": \"What does that plan cost per user?\"}"

# Inspect / clear
curl -s http://localhost:8000/sessions/YOUR_SESSION_ID
curl -s -X DELETE http://localhost:8000/sessions/YOUR_SESSION_ID
```

PowerShell equivalent:

```powershell
$session = Invoke-RestMethod -Method Post http://localhost:8000/sessions
Invoke-RestMethod -Method Post http://localhost:8000/chat -ContentType "application/json" `
  -Body (@{ session_id = $session.session_id; message = "I upgraded to the Pro plan yesterday." } | ConvertTo-Json)
Invoke-RestMethod -Method Post http://localhost:8000/chat -ContentType "application/json" `
  -Body (@{ session_id = $session.session_id; message = "What does that plan cost per user?" } | ConvertTo-Json)
```

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + model name |
| POST | `/sessions` | Create empty session |
| GET | `/sessions/{id}` | Session info + message count |
| DELETE | `/sessions/{id}` | Clear session history |
| POST | `/chat` | One chat turn (returns `reply`) |

## Docker

Ollama runs on the host. The API container reaches it via `host.docker.internal`.

```bash
cp .env.example .env
docker compose up --build
```

- API: http://localhost:8000  
- UI: http://localhost:3000  

## Project layout

```
backend/app/
  chat_service.py   LangChain chain + memory wiring
  memory.py         Windowed in-memory session store
  prompts.py        NovaDesk support system prompt
  routers/          sessions + chat routes
frontend/           React + Vite UI
docker-compose.yml
```

## License

MIT
