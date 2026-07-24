"""Session lifecycle endpoints."""

from fastapi import APIRouter, HTTPException

from app.memory import memory_store
from app.schemas import SessionCreateResponse, SessionInfoResponse, SessionResetResponse

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session() -> SessionCreateResponse:
    session_id = memory_store.create_session()
    return SessionCreateResponse(session_id=session_id)


@router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
def get_session(session_id: str) -> SessionInfoResponse:
    exists = memory_store.exists(session_id)
    return SessionInfoResponse(
        session_id=session_id,
        message_count=memory_store.message_count(session_id) if exists else 0,
        exists=exists,
    )


@router.delete("/sessions/{session_id}", response_model=SessionResetResponse)
def reset_session(session_id: str) -> SessionResetResponse:
    if not memory_store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    memory_store.clear(session_id)
    return SessionResetResponse(session_id=session_id, cleared=True)
