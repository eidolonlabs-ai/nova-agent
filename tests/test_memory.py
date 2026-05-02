"""Tests for memory store."""

import tempfile
from pathlib import Path

from nova.memory import MemoryStore


def test_add_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db, max_entries=10)

        store.add("User prefers dark mode", category="preferences")
        store.add("Project uses pytest", category="project")

        results = store.search("dark mode")
        assert len(results) == 1
        assert "dark mode" in results[0]["content"]


def test_lru_eviction():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db, max_entries=3)

        store.add("Memory 1")
        store.add("Memory 2")
        store.add("Memory 3")
        store.add("Memory 4")  # Should evict Memory 1

        entries = store.get_all()
        assert len(entries) == 3
        assert entries[0]["content"] == "Memory 2"


def test_delete():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db)

        entry = store.add("Test memory")
        assert store.delete(entry["id"])
        assert len(store.get_all()) == 0
        assert not store.delete("nonexistent")


def test_clear():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db)

        store.add("Memory 1")
        store.add("Memory 2")
        store.clear()
        assert len(store.get_all()) == 0


def test_format_for_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db)

        store.add("User prefers concise responses", category="preferences")
        store.add("Project uses Python 3.12", category="project")

        formatted = store.format_for_prompt()
        assert "<memory>" in formatted
        assert "</memory>" in formatted
        assert "preferences" in formatted
        assert "project" in formatted


def test_format_for_prompt_empty():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "memory.json"
        store = MemoryStore(db)

        assert store.format_for_prompt() == ""
