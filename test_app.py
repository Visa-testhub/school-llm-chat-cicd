from unittest.mock import Mock

import pytest
import requests

import app as app_module
import db


@pytest.fixture
def fake_ollama(monkeypatch):
    response = Mock()

    response.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Hello!"
        }
    }

    fake_post = Mock(return_value=response)

    monkeypatch.setattr(
        app_module.requests, "post", fake_post
    )

    return fake_post


@pytest.fixture
def client(monkeypatch, fake_ollama):
    # Force in-memory storage instead of MySQL
    monkeypatch.delenv("DB_NAME", raising=False)

    # Start every test with an empty database
    monkeypatch.setattr(db, "_memory", {})

    monkeypatch.setitem(
        app_module.app.config, "TESTING", True
    )

    return app_module.app.test_client()


def test_index(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b'id="chat-form"' in response.data


def test_chat_rejects_missing_message(client, fake_ollama):
    response = client.post("/api/chat", json={
        "session_id": "test-session-1"
    })

    assert response.status_code == 400
    fake_ollama.assert_not_called()


def test_chat_rejects_invalid_session(client):
    response = client.post("/api/chat", json={
        "session_id": "../invalid",
        "message": "Hello"
    })

    assert response.status_code == 400


def test_chat_rejects_long_message(client):
    response = client.post("/api/chat", json={
        "session_id": "test-session-1",
        "message": "x" * (app_module.MAX_MESSAGE_LEN + 1)
    })

    assert response.status_code == 400


def test_chat_returns_reply_and_saves_history(client):
    response = client.post("/api/chat", json={
        "session_id": "test-session-1",
        "message": "Hi!"
    })

    assert response.status_code == 200
    assert response.get_json()["reply"] == "Hello!"

    assert db.get_history("test-session-1") == [
        {"role": "user", "content": "Hi!"},
        {"role": "assistant", "content": "Hello!"}
    ]


def test_chat_sends_previous_messages(client, fake_ollama):
    session_id = "test-session-1"

    db.save_message(
        session_id, "user", "My favorite color is purple."
    )

    db.save_message(
        session_id, "assistant", "Understood."
    )

    response = client.post("/api/chat", json={
        "session_id": session_id,
        "message": "What is my favorite color?"
    })

    assert response.status_code == 200

    payload = fake_ollama.call_args.kwargs["json"]

    assert payload["messages"] == [
        {
            "role": "system",
            "content": app_module.SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": "My favorite color is purple."
        },
        {
            "role": "assistant",
            "content": "Understood."
        },
        {
            "role": "user",
            "content": "What is my favorite color?"
        }
    ]


def test_history_separates_sessions(client):
    db.save_message(
        "test-session-1", "user", "Conversation A"
    )

    db.save_message(
        "test-session-2", "user", "Conversation B"
    )

    response = client.get("/api/history/test-session-1")

    assert response.status_code == 200

    assert response.get_json() == [
        {"role": "user", "content": "Conversation A"}
    ]


def test_empty_history(client):
    response = client.get("/api/history/test-session-1")

    assert response.status_code == 200
    assert response.get_json() == []


def test_chat_handles_ollama_failure(client, fake_ollama):
    fake_ollama.side_effect = requests.ConnectionError(
        "Connection refused"
    )

    response = client.post("/api/chat", json={
        "session_id": "test-session-1",
        "message": "Hello"
    })

    assert response.status_code == 502


def test_chat_handles_database_failure(client, monkeypatch):
    broken_database = Mock(
        side_effect=db.DatabaseError("Database unavailable")
    )

    monkeypatch.setattr(
        db, "get_history", broken_database
    )

    response = client.post("/api/chat", json={
        "session_id": "test-session-1",
        "message": "Hello"
    })

    assert response.status_code == 503
