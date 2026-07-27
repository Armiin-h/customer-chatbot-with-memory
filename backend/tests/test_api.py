"""API tests that do not require a live Ollama process."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.memory import get_store, reset_memory_store


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "api.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    from app import chat_service
    from app.config import get_settings

    get_settings.cache_clear()
    chat_service.get_chat_chain.cache_clear()
    reset_memory_store(db_path=db_path, max_turns=10)

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()
    chat_service.get_chat_chain.cache_clear()


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "database" in body


def test_session_lifecycle(client: TestClient) -> None:
    created = client.post("/sessions")
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    info = client.get(f"/sessions/{session_id}")
    assert info.status_code == 200
    assert info.json() == {
        "session_id": session_id,
        "message_count": 0,
        "exists": True,
    }

    get_store().get_or_create(session_id).add_messages(
        [HumanMessage(content="hi"), AIMessage(content="hello")]
    )
    assert client.get(f"/sessions/{session_id}").json()["message_count"] == 2

    cleared = client.delete(f"/sessions/{session_id}")
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] is True
    assert client.get(f"/sessions/{session_id}").json()["message_count"] == 0
