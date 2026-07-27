"""LangChain chat chain with per-session message history."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

from app.config import Settings, get_settings
from app.memory import get_session_history, get_store
from app.prompts import SUPPORT_SYSTEM_PROMPT


def build_chat_model(settings: Settings | None = None) -> ChatOllama:
    settings = settings or get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.3,
    )


def build_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("system", SUPPORT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )


def build_chain(settings: Settings | None = None) -> RunnableWithMessageHistory:
    settings = settings or get_settings()
    runnable = build_prompt() | build_chat_model(settings) | StrOutputParser()
    return RunnableWithMessageHistory(
        runnable,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )


@lru_cache
def get_chat_chain() -> RunnableWithMessageHistory:
    return build_chain()


def ensure_session(session_id: str | None) -> str:
    store = get_store()
    if not session_id:
        return store.create_session()
    store.get_or_create(session_id)
    return session_id


def chat(message: str, session_id: str | None = None) -> tuple[str, str, int]:
    """
    Run a non-streaming turn.

    Returns (session_id, reply, message_count_after).
    """
    session_id = ensure_session(session_id)
    chain = get_chat_chain()
    reply = chain.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    count = get_store().message_count(session_id)
    return session_id, reply, count


async def stream_chat(
    message: str,
    session_id: str | None = None,
) -> AsyncIterator[str]:
    """
    Yield Server-Sent Event lines for one chat turn.

    Event payloads are JSON with a `type` field:
    - session: {session_id}
    - token: {content}
    - done: {message_count}
    - error: {detail}
    """
    session_id = ensure_session(session_id)
    yield _sse({"type": "session", "session_id": session_id})

    chain = get_chat_chain()
    try:
        async for chunk in chain.astream(
            {"input": message},
            config={"configurable": {"session_id": session_id}},
        ):
            if chunk:
                yield _sse({"type": "token", "content": chunk})
    except Exception as exc:  # noqa: BLE001
        yield _sse({"type": "error", "detail": str(exc)})
        return

    count = get_store().message_count(session_id)
    yield _sse({"type": "done", "message_count": count, "session_id": session_id})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
