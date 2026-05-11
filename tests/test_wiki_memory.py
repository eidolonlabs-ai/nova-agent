"""Tests for WikiMemory."""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from nova.wiki_memory import WikiMemory, _excerpt, _title_similar


@pytest.fixture
def vault(tmp_path: Path) -> WikiMemory:
    return WikiMemory(tmp_path / "wiki", max_prompt_notes=5)


def test_write_creates_file(vault: WikiMemory):
    result = vault.write("Test Note", "Hello world", tags=["test"])
    assert result["status"] == "written"
    assert (vault.vault_path / "Test Note.md").exists()


def test_write_with_folder_prefix(vault: WikiMemory):
    vault.write("People/Alice", "Alice is great")
    assert (vault.vault_path / "People" / "Alice.md").exists()


def test_write_preserves_created_date(vault: WikiMemory):
    vault.write("Note", "v1")
    note1 = vault.read("Note")
    created = note1["frontmatter"]["created"]

    vault.write("Note", "v2")
    note2 = vault.read("Note")
    assert note2["frontmatter"]["created"] == created


def test_write_updates_modified_date(vault: WikiMemory):
    vault.write("Note", "v1")
    vault.write("Note", "v2")
    note2 = vault.read("Note")
    # modified may equal created on fast machines; just check it's present
    assert "modified" in note2["frontmatter"]
    assert note2["content"] == "v2"


def test_append_to_existing(vault: WikiMemory):
    vault.write("Note", "First paragraph")
    vault.append("Note", "Second paragraph")
    note = vault.read("Note")
    assert "First paragraph" in note["content"]
    assert "Second paragraph" in note["content"]


def test_append_creates_note_if_missing(vault: WikiMemory):
    result = vault.append("New Note", "Auto-created")
    assert result["status"] == "written"
    assert vault.read("New Note") is not None


def test_read_returns_none_for_missing(vault: WikiMemory):
    assert vault.read("Nonexistent") is None


def test_read_returns_frontmatter_and_content(vault: WikiMemory):
    vault.write("My Note", "Some content", tags=["foo"])
    note = vault.read("My Note")
    assert note is not None
    assert note["frontmatter"]["tags"] == ["foo"]
    assert note["content"] == "Some content"


def test_search_finds_match(vault: WikiMemory):
    vault.write("Alpha", "The quick brown fox")
    vault.write("Beta", "Lazy dog sleeps")
    results = vault.search("quick brown")
    assert len(results) == 1
    assert results[0]["title"] == "Alpha"


def test_search_case_insensitive(vault: WikiMemory):
    vault.write("Note", "Python is great")
    results = vault.search("PYTHON")
    assert len(results) == 1


def test_search_no_results(vault: WikiMemory):
    vault.write("Note", "Hello world")
    assert vault.search("zzz_no_match") == []


def test_search_includes_excerpt(vault: WikiMemory):
    vault.write("Note", "Here is some specific text to find")
    results = vault.search("specific text")
    assert results[0]["excerpt"] != ""


def test_list_notes_returns_all(vault: WikiMemory):
    vault.write("A", "content a")
    vault.write("B", "content b")
    notes = vault.list_notes()
    titles = {n["title"] for n in notes}
    assert "A" in titles
    assert "B" in titles


def test_list_notes_filter_by_tag(vault: WikiMemory):
    vault.write("Tagged", "content", tags=["important"])
    vault.write("Untagged", "content", tags=[])
    notes = vault.list_notes(tag="important")
    assert len(notes) == 1
    assert notes[0]["title"] == "Tagged"


def test_delete_removes_file(vault: WikiMemory):
    vault.write("To Delete", "bye")
    assert vault.delete("To Delete")
    assert vault.read("To Delete") is None


def test_delete_returns_false_for_missing(vault: WikiMemory):
    assert not vault.delete("Does Not Exist")


def test_format_for_prompt_empty(vault: WikiMemory):
    assert vault.format_for_prompt() == ""


def test_format_for_prompt_includes_notes(vault: WikiMemory):
    vault.write("Projects/nova", "Agent framework", tags=["project"])
    result = vault.format_for_prompt()
    assert "<wiki_memory>" in result
    assert "[[Projects/nova]]" in result
    assert "#project" in result


def test_format_for_prompt_respects_max_notes(vault: WikiMemory):
    wiki = WikiMemory(vault.vault_path, max_prompt_notes=2)
    for i in range(5):
        wiki.write(f"Note{i}", f"content {i}")
    result = wiki.format_for_prompt()
    assert result.count("[[") == 2


def test_format_for_prompt_includes_core_notes_in_full(vault: WikiMemory):
    """Notes in Core/ get their full content injected, not just an index entry."""
    vault.write("Core/Preferences", "User prefers dark mode. Uses Python 3.12.")
    vault.write("Random Note", "some other content")
    result = vault.format_for_prompt()
    assert "<wiki_core>" in result
    assert "User prefers dark mode" in result
    assert "Uses Python 3.12" in result


def test_format_for_prompt_excludes_core_from_recent_index(vault: WikiMemory):
    """Core/ notes should not appear in the recent index — they're already injected in full."""
    vault.write("Core/Identity", "User name is Mark")
    vault.write("Other Note", "regular content")
    result = vault.format_for_prompt()
    wiki_memory_section = result.split("<wiki_memory>", 1)
    if len(wiki_memory_section) > 1:
        assert "Core/Identity" not in wiki_memory_section[1]


def test_format_for_prompt_no_core_section_when_empty(vault: WikiMemory):
    """No <wiki_core> section if Core/ doesn't exist or is empty."""
    vault.write("Just a note", "content")
    result = vault.format_for_prompt()
    assert "<wiki_core>" not in result


def test_format_for_prompt_core_respects_char_budget(vault: WikiMemory):
    """Core injection truncates at core_max_chars."""
    vault.write("Core/Big", "X" * 5000)
    result = vault.format_for_prompt(core_max_chars=500)
    assert "X" * 5000 not in result


def test_invalid_chars_in_title_sanitized(vault: WikiMemory):
    result = vault.write("My:Note*", "content")
    assert result["status"] == "written"
    # Should not raise


def test_path_traversal_with_dotdot_rejected(vault: WikiMemory):
    with pytest.raises(ValueError, match="path traversal"):
        vault.write("../../etc/passwd", "evil")


def test_absolute_path_title_rejected(vault: WikiMemory):
    with pytest.raises(ValueError, match="path traversal"):
        vault.write("/etc/passwd", "evil")


def test_empty_title_rejected(vault: WikiMemory):
    with pytest.raises(ValueError, match="empty or dot-only"):
        vault.write("", "content")


def test_whitespace_only_title_rejected(vault: WikiMemory):
    with pytest.raises(ValueError, match="empty or dot-only"):
        vault.write("   ", "content")


def test_dot_only_title_rejected(vault: WikiMemory):
    with pytest.raises(ValueError, match="empty or dot-only"):
        vault.write(".", "content")


def test_excerpt_helper():
    text = "The quick brown fox jumps over the lazy dog"
    snippet = _excerpt(text, "brown fox")
    assert "brown fox" in snippet.lower()


# --- Maintenance tests ---


def test_maintenance_empty_vault(vault: WikiMemory):
    report = vault.maintenance()
    assert report["total_notes"] == 0
    assert report["duplicate_candidates"] == []
    assert report["orphans"] == []
    assert report["stale"] == []


def test_maintenance_counts_notes(vault: WikiMemory):
    vault.write("A", "content")
    vault.write("B", "content")
    report = vault.maintenance()
    assert report["total_notes"] == 2


def test_maintenance_finds_duplicate_titles(vault: WikiMemory):
    vault.write("People/Mark", "context A")
    vault.write("Projects/Mark", "context B")
    report = vault.maintenance()
    assert len(report["duplicate_candidates"]) == 1
    titles = report["duplicate_candidates"][0]["titles"]
    assert "People/Mark" in titles
    assert "Projects/Mark" in titles


def test_maintenance_no_duplicates_for_distinct_titles(vault: WikiMemory):
    vault.write("Alpha", "x")
    vault.write("Zebra", "y")
    report = vault.maintenance()
    assert report["duplicate_candidates"] == []


def test_maintenance_identifies_orphans(vault: WikiMemory):
    # 'Lonely' has no links in or out → orphan
    # 'Linker' references 'Target', so 'Target' is referenced; 'Linker' has links out so not orphan
    vault.write("Lonely", "no links")
    vault.write("Linker", "see [[Target]]")
    vault.write("Target", "linked from elsewhere")
    report = vault.maintenance()
    orphan_titles = {o["title"] for o in report["orphans"]}
    assert "Lonely" in orphan_titles
    assert "Target" not in orphan_titles
    assert "Linker" not in orphan_titles


def test_maintenance_flags_stale_notes(vault: WikiMemory):
    vault.write("Old Note", "content")
    # Backdate the file's modification time to 200 days ago
    old_path = vault.vault_path / "Old Note.md"
    old_time = (datetime.now() - timedelta(days=200)).timestamp()
    # Also rewrite frontmatter to reflect old modified date
    parsed = vault._parse_note(old_path)
    parsed["frontmatter"]["modified"] = (datetime.now() - timedelta(days=200)).isoformat(
        timespec="seconds"
    )
    old_path.write_text(vault._format_note(parsed["frontmatter"], parsed["content"]))
    os.utime(old_path, (old_time, old_time))

    vault.write("Fresh Note", "content")
    report = vault.maintenance(stale_days=90)
    stale_titles = {s["title"] for s in report["stale"]}
    assert "Old Note" in stale_titles
    assert "Fresh Note" not in stale_titles


def test_maintenance_tag_counts(vault: WikiMemory):
    vault.write("A", "x", tags=["python", "api"])
    vault.write("B", "y", tags=["python"])
    report = vault.maintenance()
    assert report["tag_counts"]["python"] == 2
    assert report["tag_counts"]["api"] == 1


def test_title_similar_exact_match():
    assert _title_similar("Mark", "Mark")


def test_title_similar_substring():
    assert _title_similar("Mark", "People/Mark")


def test_title_similar_word_overlap():
    assert _title_similar("Python web scraping", "Python scraping notes")


def test_title_similar_unrelated():
    assert not _title_similar("Python", "JavaScript")
