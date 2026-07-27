"""Chat endpoints (JSON and SSE streaming)."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.chat_service import chat, stream_chat
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


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


@router.post("/chat/stream")
async def post_chat_stream(body: ChatRequest) -> StreamingResponse:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    return StreamingResponse(
        stream_chat(message=message, session_id=body.session_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
