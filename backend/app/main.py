"""Customer support chatbot API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Customer Chatbot with Memory",
    description="Multi-turn support agent with conversation history and streaming replies.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for local runs and Docker Compose."""
    return {
        "status": "ok",
        "service": "customer-chatbot-api",
        "ollama_model": settings.ollama_model,
    }
