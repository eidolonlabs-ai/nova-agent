"""Simple file-based memory system.

Stores durable facts as JSON entries. Supports append, search, and delete.
Inspired by Hermes-Agent's memory provider pattern but simplified.
"""

import json
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryStore:
    """File-based memory store with LRU eviction."""

    def __init__(self, file_path: Path, max_entries: int = 100):
        self.file_path = file_path
        self.max_entries = max_entries
        self._entries: list[dict] = []
        self._load()

    def _load(self):
        """Load entries from disk."""
        if self.file_path.exists():
            try:
                with open(self.file_path, encoding="utf-8") as f:
                    self._entries = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load memory file: %s", e)
                self._entries = []

    def _save(self):
        """Persist entries to disk atomically."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to temp file, then rename
        fd, tmp_path = tempfile.mkstemp(dir=self.file_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.file_path)
        except Exception:
            os.unlink(tmp_path)
            raise

    def add(self, content: str, category: str = "general") -> dict:
        """Add a memory entry."""
        import uuid as _uuid

        entry = {
            "id": f"mem_{_uuid.uuid4().hex[:8]}",
            "content": content,
            "category": category,
            "created_at": datetime.now().isoformat(),
        }
        self._entries.append(entry)

        # Enforce max entries (LRU eviction)
        if len(self._entries) > self.max_entries:
            removed = self._entries.pop(0)
            logger.debug("Evicted old memory entry: %s", removed["id"])

        self._save()
        return entry

    def search(self, query: str) -> list[dict]:
        """Search memory entries by keyword matching."""
        query_lower = query.lower()
        results = []
        for entry in self._entries:
            if query_lower in entry["content"].lower():
                results.append(entry)
        return results

    def get_all(self) -> list[dict]:
        """Get all memory entries."""
        return list(self._entries)

    def delete(self, entry_id: str) -> bool:
        """Delete a memory entry by ID."""
        for i, entry in enumerate(self._entries):
            if entry["id"] == entry_id:
                self._entries.pop(i)
                self._save()
                return True
        return False

    def clear(self):
        """Clear all memory entries."""
        self._entries = []
        self._save()

    def format_for_prompt(self, max_chars: int = 3000) -> str:
        """Format memory entries for injection into system prompt."""
        if not self._entries:
            return ""

        lines = ["<memory>"]
        lines.append("The following are persistent facts about the user and environment.")
        lines.append("Use them to personalize responses and avoid asking repeated questions.")

        for entry in self._entries:
            lines.append(f"- [{entry['category']}] {entry['content']}")

        result = "\n".join(lines) + "\n</memory>"

        if len(result) > max_chars:
            # Truncate from the middle, keeping recent entries
            result = result[:max_chars] + "\n[...older memory truncated...]"

        return result
