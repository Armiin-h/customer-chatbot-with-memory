"""In-memory chat history store with a sliding window per session."""

from __future__ import annotations

import threading
import uuid
from typing import Any, Sequence

from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage

from app.config import get_settings


class WindowedChatMessageHistory(BaseChatMessageHistory):
    """Keeps only the last N conversation turns (human + AI pairs)."""

    def __init__(self, *, max_turns: int) -> None:
        self._inner = InMemoryChatMessageHistory()
        self.max_turns = max(1, max_turns)

    @property
    def messages(self) -> list[BaseMessage]:
        return list(self._inner.messages)

    def add_message(self, message: BaseMessage) -> None:
        self._inner.add_message(message)
        self._trim()

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        self._inner.add_messages(list(messages))
        self._trim()

    def clear(self) -> None:
        self._inner.clear()

    def _trim(self) -> None:
        max_messages = self.max_turns * 2
        stored = self._inner.messages
        if len(stored) > max_messages:
            # InMemoryChatMessageHistory.messages is a mutable list
            stored[:] = stored[-max_messages:]


class SessionMemoryStore:
    """Thread-safe map of session_id → windowed chat history."""

    def __init__(self) -> None:
        self._sessions: dict[str, WindowedChatMessageHistory] = {}
        self._lock = threading.Lock()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            self._sessions[session_id] = self._new_history()
        return session_id

    def get_or_create(self, session_id: str) -> WindowedChatMessageHistory:
        with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                history = self._new_history()
                self._sessions[session_id] = history
            return history

    def get(self, session_id: str) -> WindowedChatMessageHistory | None:
        with self._lock:
            return self._sessions.get(session_id)

    def clear(self, session_id: str) -> bool:
        with self._lock:
            history = self._sessions.get(session_id)
            if history is None:
                return False
            history.clear()
            return True

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def message_count(self, session_id: str) -> int:
        with self._lock:
            history = self._sessions.get(session_id)
            return len(history.messages) if history else 0

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Factory for RunnableWithMessageHistory."""
        return self.get_or_create(session_id)

    def _new_history(self) -> WindowedChatMessageHistory:
        settings = get_settings()
        return WindowedChatMessageHistory(max_turns=settings.memory_window_size)


# Process-wide store (Day 3 will swap persistence behind the same interface)
memory_store = SessionMemoryStore()


def get_session_history(session_id: str, **_: Any) -> BaseChatMessageHistory:
    return memory_store.get_session_history(session_id)
