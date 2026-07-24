"""LangChain chat chain with per-session message history."""

from __future__ import annotations

from functools import lru_cache

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

from app.config import Settings, get_settings
from app.memory import get_session_history, memory_store
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


def chat(message: str, session_id: str | None = None) -> tuple[str, str, int]:
    """
    Run a non-streaming turn.

    Returns (session_id, reply, message_count_after).
    """
    if not session_id:
        session_id = memory_store.create_session()
    else:
        memory_store.get_or_create(session_id)

    chain = get_chat_chain()
    reply = chain.invoke(
        {"input": message},
        config={"configurable": {"session_id": session_id}},
    )
    count = memory_store.message_count(session_id)
    return session_id, reply, count
