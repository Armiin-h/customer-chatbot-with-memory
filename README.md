# Customer Chatbot with Memory

Multi-turn customer support chatbot that keeps conversation context across turns.
Built with FastAPI, React, LangChain, and Ollama.

## Features (planned)

- Streaming chat responses (SSE)
- Per-session conversation memory (last-N window)
- SQLite-backed history persistence
- React chat UI with live typing
- Docker Compose for API + frontend

## Stack

| Layer | Technology |
|-------|------------|
| LLM | Ollama (local) |
| Orchestration | LangChain (`RunnableWithMessageHistory`) |
| Backend | FastAPI |
| History | In-memory → SQLite |
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
backend/          FastAPI app
frontend/         React + Vite UI
docker-compose.yml
```

## License

MIT
