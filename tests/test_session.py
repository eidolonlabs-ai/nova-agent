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


def test_delete_session_exists():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session(title="To Delete")
        store.add_message(sid, "user", "Test message")

        assert store.delete_session(sid) is True

        info = store.get_session_info(sid)
        assert info is None

        msgs = store.get_messages(sid)
        assert len(msgs) == 0


def test_delete_session_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        assert store.delete_session("nonexistent") is False


def test_prune_sessions():
    from datetime import datetime, timedelta
    import sqlite3

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        # Create old session by directly updating timestamps
        sid_old = store.create_session(title="Old Session")
        store.add_message(sid_old, "user", "old message")

        sid_new = store.create_session(title="New Session")
        store.add_message(sid_new, "user", "new message")

        # Manually set old session to 40 days ago
        cutoff = (datetime.now() - timedelta(days=40)).isoformat()
        with sqlite3.connect(db) as conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                (cutoff, sid_old),
            )

        # Prune sessions older than 30 days
        deleted_count = store.prune_sessions(30)
        assert deleted_count == 1

        # Old session should be gone
        assert store.get_session_info(sid_old) is None

        # New session should still exist
        assert store.get_session_info(sid_new) is not None


def test_prune_sessions_zero_deleted():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        store.create_session(title="Recent")

        deleted_count = store.prune_sessions(30)
        assert deleted_count == 0


def test_search_sessions():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid1 = store.create_session(title="Python Workshop")
        store.add_message(sid1, "user", "How to learn Python")
        store.add_message(sid1, "assistant", "Python is great for beginners")

        sid2 = store.create_session(title="JavaScript Course")
        store.add_message(sid2, "user", "JavaScript syntax")
        store.add_message(sid2, "assistant", "JS is different from Python")

        sid3 = store.create_session(title="Random Chat")
        store.add_message(sid3, "user", "Hello world")

        # Search for Python
        results = store.search_sessions("Python")
        session_ids = [r["session_id"] for r in results]
        assert sid1 in session_ids
        assert sid2 in session_ids

        # Search for JavaScript
        results = store.search_sessions("JavaScript")
        session_ids = [r["session_id"] for r in results]
        assert sid2 in session_ids


def test_search_sessions_empty_query():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session(title="Test")
        store.add_message(sid, "user", "content")

        results = store.search_sessions("")
        assert isinstance(results, list)


def test_add_message_with_tool_calls():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()
        tool_calls = [{"id": "1", "function": "test_func", "args": {}}]

        idx = store.add_message(sid, "assistant", "Calling function", tool_calls=tool_calls)
        assert idx == 0

        msgs = store.get_messages(sid)
        assert len(msgs) == 1
        assert msgs[0]["tool_calls"] == tool_calls


def test_add_message_indexes():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()

        idx0 = store.add_message(sid, "user", "First")
        idx1 = store.add_message(sid, "assistant", "Second")
        idx2 = store.add_message(sid, "user", "Third")

        assert idx0 == 0
        assert idx1 == 1
        assert idx2 == 2

        msgs = store.get_messages(sid)
        assert len(msgs) == 3


def test_create_session_custom_id():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        custom_id = "custom_session_123"
        sid = store.create_session(session_id=custom_id, title="Custom")

        assert sid == custom_id
        info = store.get_session_info(sid)
        assert info["session_id"] == custom_id


def test_get_session_info_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        info = store.get_session_info("nonexistent")
        assert info is None


def test_list_sessions_limit():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        for i in range(25):
            store.create_session(title=f"Session {i}")

        sessions = store.list_sessions(limit=10)
        assert len(sessions) == 10


def test_list_sessions_empty():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sessions = store.list_sessions()
        assert len(sessions) == 0


def test_session_message_count_increments():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "test.db"
        store = SessionStore(db)

        sid = store.create_session()
        assert store.get_session_info(sid)["message_count"] == 0

        store.add_message(sid, "user", "msg1")
        assert store.get_session_info(sid)["message_count"] == 1

        store.add_message(sid, "assistant", "msg2")
        assert store.get_session_info(sid)["message_count"] == 2
