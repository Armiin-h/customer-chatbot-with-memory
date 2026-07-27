"""Customer support chatbot API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import chat, sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(get_settings().sqlite_path)
    yield


app = FastAPI(
    title="Customer Chatbot with Memory",
    description="Multi-turn support agent with conversation history and streaming replies.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(chat.router)


@app.get("/health")
def health() -> dict[str, str | int]:
    """Liveness check for local runs and Docker Compose."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": "customer-chatbot-api",
        "ollama_model": settings.ollama_model,
        "memory_window_size": settings.memory_window_size,
        "database": str(settings.sqlite_path.name),
    }
