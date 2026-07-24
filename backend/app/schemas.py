"""Request and response models for the chat API."""

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str
    message: str = "Session created"


class SessionInfoResponse(BaseModel):
    session_id: str
    message_count: int
    exists: bool


class SessionResetResponse(BaseModel):
    session_id: str
    cleared: bool
    message: str = "Session history cleared"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = Field(
        default=None,
        description="Existing session id. If omitted, a new session is created.",
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    message_count: int
