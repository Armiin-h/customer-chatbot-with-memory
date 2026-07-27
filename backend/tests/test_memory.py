"""Unit tests for SQLite session memory (isolation + window trim)."""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from app.memory import SessionMemoryStore


def test_session_isolation(tmp_path: Path) -> None:
    store = SessionMemoryStore(db_path=tmp_path / "iso.db", max_turns=10)
    a = store.create_session()
    b = store.create_session()

    store.get_or_create(a).add_messages(
        [HumanMessage(content="My plan is Pro"), AIMessage(content="Got it")]
    )
    store.get_or_create(b).add_messages(
        [HumanMessage(content="My plan is Free"), AIMessage(content="Noted")]
    )

    texts_a = [m.content for m in store.get_or_create(a).messages]
    texts_b = [m.content for m in store.get_or_create(b).messages]

    assert "Pro" in texts_a[0]
    assert "Free" not in "".join(texts_a)
    assert "Free" in texts_b[0]
    assert "Pro" not in "".join(texts_b)


def test_window_trims_oldest_turns(tmp_path: Path) -> None:
    store = SessionMemoryStore(db_path=tmp_path / "window.db", max_turns=2)
    sid = store.create_session()
    history = store.get_or_create(sid)

    for i in range(3):
        history.add_messages(
            [
                HumanMessage(content=f"user-{i}"),
                AIMessage(content=f"ai-{i}"),
            ]
        )

    messages = history.messages
    assert len(messages) == 4  # 2 turns × 2 messages
    contents = [m.content for m in messages]
    assert contents == ["user-1", "ai-1", "user-2", "ai-2"]
    assert "user-0" not in contents


def test_persistence_across_store_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "persist.db"
    first = SessionMemoryStore(db_path=db_path, max_turns=5)
    sid = first.create_session()
    first.get_or_create(sid).add_messages(
        [HumanMessage(content="remember me"), AIMessage(content="ok")]
    )

    second = SessionMemoryStore(db_path=db_path, max_turns=5)
    assert second.exists(sid)
    assert second.message_count(sid) == 2
    assert second.get_or_create(sid).messages[0].content == "remember me"


def test_clear_session_history(tmp_path: Path) -> None:
    store = SessionMemoryStore(db_path=tmp_path / "clear.db", max_turns=5)
    sid = store.create_session()
    store.get_or_create(sid).add_message(HumanMessage(content="hello"))
    assert store.message_count(sid) == 1

    assert store.clear(sid) is True
    assert store.exists(sid) is True
    assert store.message_count(sid) == 0
    assert store.get_or_create(sid).messages == []
