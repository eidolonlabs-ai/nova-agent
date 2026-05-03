"""SQLite session storage with FTS5 search.

Stores conversation sessions with message history, system prompts, and metadata.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionStore:
    """SQLite-backed session storage."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    model TEXT,
                    system_prompt TEXT,
                    title TEXT,
                    message_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    idx INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, idx);

                CREATE TABLE IF NOT EXISTS session_fts (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );

                -- Standalone FTS5 table with session_id for search
                CREATE VIRTUAL TABLE IF NOT EXISTS session_search
                    USING fts5(session_id, title, content);

                CREATE TRIGGER IF NOT EXISTS session_fts_insert
                    AFTER INSERT ON session_fts
                BEGIN
                    INSERT INTO session_search(session_id, title, content)
                    VALUES (new.session_id, new.title, new.content);
                END;

                CREATE TRIGGER IF NOT EXISTS session_fts_update
                    AFTER UPDATE ON session_fts
                BEGIN
                    UPDATE session_search
                    SET title = new.title, content = new.content
                    WHERE session_id = new.session_id;
                END;
            """)

    def create_session(
        self,
        session_id: str | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        title: str | None = None,
    ) -> str:
        """Create a new session."""
        if session_id is None:
            session_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, created_at, updated_at, model, system_prompt, title, message_count) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (session_id, now, now, model, system_prompt, title),
            )
            conn.execute(
                "INSERT OR IGNORE INTO session_fts (session_id, title, content) VALUES (?, ?, ?)",
                (session_id, title, ""),
            )

        logger.info("Created session %s", session_id)
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: list | None = None,
    ) -> int:
        """Add a message to a session. Returns the message index."""
        now = datetime.now().isoformat()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None

        with sqlite3.connect(self.db_path) as conn:
            # Atomic: get max idx and insert in one transaction to avoid TOCTOU race
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                "SELECT COALESCE(MAX(idx), -1) FROM messages WHERE session_id = ?",
                (session_id,),
            )
            idx = cursor.fetchone()[0] + 1

            conn.execute(
                "INSERT INTO messages (session_id, idx, role, content, tool_calls, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, idx, role, content, tool_calls_json, now),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ?, message_count = message_count + 1 WHERE session_id = ?",
                (now, session_id),
            )
            # Keep FTS content in sync so search_sessions actually finds messages
            if role in ("user", "assistant") and content:
                conn.execute(
                    "UPDATE session_fts SET content = content || ' ' || ? WHERE session_id = ?",
                    (content, session_id),
                )

        return idx

    def get_messages(self, session_id: str, limit: int | None = None) -> list[dict]:
        """Get all messages for a session, optionally limited."""
        with sqlite3.connect(self.db_path) as conn:
            if limit:
                # Use parameterized query to prevent SQL injection
                query = (
                    "SELECT role, content, tool_calls FROM messages "
                    "WHERE session_id = ? ORDER BY idx DESC LIMIT ?"
                )
                cursor = conn.execute(query, (session_id, limit))
            else:
                query = (
                    "SELECT role, content, tool_calls FROM messages "
                    "WHERE session_id = ? ORDER BY idx"
                )
                cursor = conn.execute(query, (session_id,))
            messages = []
            for row in cursor.fetchall():
                msg = {
                    "role": row[0],
                    "content": row[1],
                }
                if row[2]:
                    msg["tool_calls"] = json.loads(row[2])
                messages.append(msg)

            if limit:
                messages.reverse()

            return messages

    def get_session_info(self, session_id: str) -> dict | None:
        """Get session metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id, created_at, updated_at, model, system_prompt, title, message_count "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "session_id": row[0],
                "created_at": row[1],
                "updated_at": row[2],
                "model": row[3],
                "system_prompt": row[4],
                "title": row[5],
                "message_count": row[6],
            }

    def update_system_prompt(self, session_id: str, system_prompt: str):
        """Update the system prompt for a session."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET system_prompt = ?, updated_at = ? WHERE session_id = ?",
                (system_prompt, datetime.now().isoformat(), session_id),
            )

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id, created_at, updated_at, model, title, message_count "
                "FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            return [
                {
                    "session_id": row[0],
                    "created_at": row[1],
                    "updated_at": row[2],
                    "model": row[3],
                    "title": row[4],
                    "message_count": row[5],
                }
                for row in cursor.fetchall()
            ]

    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?", (session_id,)
            )
            if not cursor.fetchone():
                return False
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM session_fts WHERE session_id = ?", (session_id,))
            conn.execute(
                "DELETE FROM session_search WHERE session_id = ?", (session_id,)
            )
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        logger.info("Deleted session %s", session_id)
        return True

    def prune_sessions(self, older_than_days: int) -> int:
        """Delete sessions older than N days. Returns count deleted."""
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=older_than_days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT session_id FROM sessions WHERE updated_at < ?", (cutoff,)
            )
            old_ids = [row[0] for row in cursor.fetchall()]
            for sid in old_ids:
                conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
                conn.execute("DELETE FROM session_fts WHERE session_id = ?", (sid,))
                conn.execute(
                    "DELETE FROM session_search WHERE session_id = ?", (sid,)
                )
            conn.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        logger.info("Pruned %d sessions older than %d days", len(old_ids), older_than_days)
        return len(old_ids)

    def search_sessions(self, query: str, limit: int = 10) -> list[dict]:
        """Search sessions using FTS5."""
        # Escape FTS5 special characters for safe querying
        safe_query = query.replace('"', '""')
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT s.session_id, s.title, s.updated_at, s.message_count "
                "FROM sessions s "
                "JOIN session_search fs ON s.session_id = fs.session_id "
                "WHERE session_search MATCH ? "
                "ORDER BY rank LIMIT ?",
                (f'"{safe_query}"*', limit),
            )
            return [
                {
                    "session_id": row[0],
                    "title": row[1],
                    "updated_at": row[2],
                    "message_count": row[3],
                }
                for row in cursor.fetchall()
            ]
