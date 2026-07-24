"""Chat endpoints (non-streaming for Day 2)."""

from fastapi import APIRouter, HTTPException

from app.chat_service import chat
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    try:
        session_id, reply, message_count = chat(
            message=body.message.strip(),
            session_id=body.session_id,
        )
    except Exception as exc:  # noqa: BLE001 — surface Ollama/connectivity failures cleanly
        raise HTTPException(
            status_code=503,
            detail=f"Chat backend unavailable: {exc}",
        ) from exc

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        message_count=message_count,
    )
