"""SQLite-backed chat history store with a sliding window per session."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.config import get_settings
from app.db import connect, init_db


def _role_for_message(message: BaseMessage) -> str:
    if isinstance(message, HumanMessage):
        return "human"
    if isinstance(message, AIMessage):
        return "ai"
    if isinstance(message, SystemMessage):
        return "system"
    # Fallback for generic message types
    msg_type = getattr(message, "type", "human")
    if msg_type in {"human", "ai", "system"}:
        return msg_type
    return "human"


def _message_from_row(role: str, content: str) -> BaseMessage:
    if role == "ai":
        return AIMessage(content=content)
    if role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


class SqliteWindowedChatMessageHistory(BaseChatMessageHistory):
    """Persists messages for one session and keeps only the last N turns."""

    def __init__(self, *, session_id: str, db_path: Path, max_turns: int) -> None:
        self.session_id = session_id
        self.db_path = db_path
        self.max_turns = max(1, max_turns)

    @property
    def messages(self) -> list[BaseMessage]:
        with connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (self.session_id,),
            ).fetchall()
        return [_message_from_row(row["role"], row["content"]) for row in rows]

    def add_message(self, message: BaseMessage) -> None:
        self.add_messages([message])

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        if not messages:
            return
        max_messages = self.max_turns * 2
        with connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
                (self.session_id,),
            )
            for message in messages:
                conn.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content)
                    VALUES (?, ?, ?)
                    """,
                    (self.session_id, _role_for_message(message), str(message.content)),
                )
            # Keep only the newest max_messages rows for this session
            conn.execute(
                """
                DELETE FROM chat_messages
                WHERE session_id = ?
                  AND id NOT IN (
                    SELECT id FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (self.session_id, self.session_id, max_messages),
            )
            conn.commit()

    def clear(self) -> None:
        with connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM chat_messages WHERE session_id = ?",
                (self.session_id,),
            )
            conn.commit()


class SessionMemoryStore:
    """Session registry + SQLite-backed windowed histories."""

    def __init__(self, db_path: Path | None = None, max_turns: int | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path
        self.max_turns = max_turns if max_turns is not None else settings.memory_window_size
        self._lock = threading.Lock()
        init_db(self.db_path)

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        with self._lock:
            with connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO sessions (session_id) VALUES (?)",
                    (session_id,),
                )
                conn.commit()
        return session_id

    def get_or_create(self, session_id: str) -> SqliteWindowedChatMessageHistory:
        with self._lock:
            with connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO sessions (session_id) VALUES (?)",
                    (session_id,),
                )
                conn.commit()
        return self._history(session_id)

    def get(self, session_id: str) -> SqliteWindowedChatMessageHistory | None:
        if not self.exists(session_id):
            return None
        return self._history(session_id)

    def clear(self, session_id: str) -> bool:
        if not self.exists(session_id):
            return False
        self._history(session_id).clear()
        return True

    def delete(self, session_id: str) -> bool:
        with self._lock:
            with connect(self.db_path) as conn:
                cur = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?",
                    (session_id,),
                )
                conn.execute(
                    "DELETE FROM chat_messages WHERE session_id = ?",
                    (session_id,),
                )
                conn.commit()
                return cur.rowcount > 0

    def message_count(self, session_id: str) -> int:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM chat_messages WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["n"]) if row else 0

    def exists(self, session_id: str) -> bool:
        with connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone()
        return row is not None

    def get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Factory for RunnableWithMessageHistory."""
        return self.get_or_create(session_id)

    def _history(self, session_id: str) -> SqliteWindowedChatMessageHistory:
        return SqliteWindowedChatMessageHistory(
            session_id=session_id,
            db_path=self.db_path,
            max_turns=self.max_turns,
        )


memory_store = SessionMemoryStore()


def get_store() -> SessionMemoryStore:
    """Return the current process-wide store (always look up by name)."""
    return memory_store


def get_session_history(session_id: str, **_: Any) -> BaseChatMessageHistory:
    return get_store().get_session_history(session_id)


def reset_memory_store(db_path: Path | None = None, max_turns: int | None = None) -> SessionMemoryStore:
    """Replace the process-wide store (used by tests)."""
    global memory_store
    memory_store = SessionMemoryStore(db_path=db_path, max_turns=max_turns)
    return memory_store
