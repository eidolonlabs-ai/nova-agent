"""Tests for session storage."""

import tempfile
from pathlib import Path

from nova.session import SessionStore


def test_create_and_get_session():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session(model="test-model", title="Test Session")
        assert sid is not None

        info = store.get_session_info(sid)
        assert info is not None
        assert info["model"] == "test-model"
        assert info["title"] == "Test Session"
        assert info["message_count"] == 0


def test_add_and_get_messages():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()
        store.add_message(sid, "user", "Hello")
        store.add_message(sid, "assistant", "Hi there!")

        msgs = store.get_messages(sid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant"


def test_get_messages_with_limit():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()
        for i in range(10):
            store.add_message(sid, "user", f"Message {i}")

        # Get last 3 messages
        msgs = store.get_messages(sid, limit=3)
        assert len(msgs) == 3
        assert msgs[0]["content"] == "Message 7"
        assert msgs[2]["content"] == "Message 9"


def test_list_sessions():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        store.create_session(title="Session A")
        store.create_session(title="Session B")

        sessions = store.list_sessions()
        assert len(sessions) == 2
        titles = {s["title"] for s in sessions}
        assert titles == {"Session A", "Session B"}


def test_update_system_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()
        store.update_system_prompt(sid, "You are a test agent.")

        info = store.get_session_info(sid)
        assert info["system_prompt"] == "You are a test agent."
