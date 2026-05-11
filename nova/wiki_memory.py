"""Obsidian-compatible wiki memory.

Notes are stored as markdown files with YAML frontmatter in a configurable
vault directory. Supports wikilinks ([[title]]) and #tags natively.
"""

import contextlib
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_INVALID_CHARS = re.compile(r'[\\:*?"<>|]')


class WikiMemory:
    """File-based wiki memory backed by an Obsidian-compatible vault."""

    def __init__(self, vault_path: Path, max_prompt_notes: int = 10):
        self.vault_path = vault_path
        self.max_prompt_notes = max_prompt_notes
        vault_path.mkdir(parents=True, exist_ok=True)

    def _note_path(self, title: str) -> Path:
        """Convert a title (optionally with path prefix) to an absolute .md path.

        Rejects empty titles, dot-only titles, and titles that would escape
        the vault directory (e.g. via '..').
        """
        sanitized = _INVALID_CHARS.sub("_", title.strip())
        if not sanitized or sanitized in (".", "/"):
            raise ValueError(f"Invalid note title (empty or dot-only): {title!r}")
        parts = Path(sanitized)
        if parts.is_absolute() or any(p == ".." for p in parts.parts):
            raise ValueError(f"Invalid note title (path traversal): {title!r}")
        if not parts.name or parts.name == ".":
            raise ValueError(f"Invalid note title (no filename): {title!r}")
        path = self.vault_path / parts.parent / (parts.name + ".md")
        vault_resolved = self.vault_path.resolve()
        if (
            not str(path.resolve()).startswith(str(vault_resolved) + os.sep)
            and path.resolve() != vault_resolved
        ):
            raise ValueError(f"Invalid note title (escapes vault): {title!r}")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _parse_note(self, path: Path) -> dict:
        text = path.read_text(encoding="utf-8")
        frontmatter: dict = {}
        content = text
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                with contextlib.suppress(yaml.YAMLError):
                    frontmatter = yaml.safe_load(text[4:end]) or {}
                content = text[end + 5 :]
        return {"frontmatter": frontmatter, "content": content.lstrip("\n")}

    def _format_note(self, frontmatter: dict, content: str) -> str:
        fm_str = yaml.dump(
            frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        return f"---\n{fm_str}---\n\n{content}"

    def _write_atomic(self, path: Path, text: str) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, path)
        except Exception:
            os.unlink(tmp)
            raise

    def write(self, title: str, content: str, tags: list[str] | None = None) -> dict:
        """Create or overwrite a note."""
        path = self._note_path(title)
        now = datetime.now().isoformat(timespec="seconds")
        frontmatter: dict = {
            "title": title,
            "tags": tags or [],
            "created": now,
            "modified": now,
        }
        if path.exists():
            existing = self._parse_note(path)
            frontmatter["created"] = existing["frontmatter"].get("created", now)
        self._write_atomic(path, self._format_note(frontmatter, content))
        return {"status": "written", "path": str(path.relative_to(self.vault_path))}

    def append(self, title: str, content: str) -> dict:
        """Append content to an existing note, or create it if absent."""
        path = self._note_path(title)
        if not path.exists():
            return self.write(title, content)
        parsed = self._parse_note(path)
        parsed["frontmatter"]["modified"] = datetime.now().isoformat(timespec="seconds")
        new_content = parsed["content"].rstrip() + "\n\n" + content
        self._write_atomic(path, self._format_note(parsed["frontmatter"], new_content))
        return {"status": "appended", "path": str(path.relative_to(self.vault_path))}

    def read(self, title: str) -> dict | None:
        """Return parsed note or None if not found."""
        path = self._note_path(title)
        if not path.exists():
            return None
        return self._parse_note(path)

    def search(self, query: str) -> list[dict]:
        """Case-insensitive full-text search across all notes."""
        query_lower = query.lower()
        results = []
        for md_file in sorted(self.vault_path.rglob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if query_lower not in text.lower():
                continue
            parsed = self._parse_note(md_file)
            results.append(
                {
                    "title": parsed["frontmatter"].get("title", md_file.stem),
                    "path": str(md_file.relative_to(self.vault_path)),
                    "tags": parsed["frontmatter"].get("tags", []),
                    "excerpt": _excerpt(text, query_lower),
                }
            )
        return results

    def list_notes(self, tag: str | None = None) -> list[dict]:
        """List notes sorted by most recently modified, optionally filtered by tag."""
        notes = []
        for md_file in sorted(
            self.vault_path.rglob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        ):
            try:
                parsed = self._parse_note(md_file)
            except OSError:
                continue
            note_tags = parsed["frontmatter"].get("tags") or []
            if tag and tag not in note_tags:
                continue
            first_line = parsed["content"].split("\n")[0][:120] if parsed["content"] else ""
            notes.append(
                {
                    "title": parsed["frontmatter"].get("title", md_file.stem),
                    "path": str(md_file.relative_to(self.vault_path)),
                    "tags": note_tags,
                    "modified": parsed["frontmatter"].get("modified", ""),
                    "first_line": first_line,
                }
            )
        return notes

    def delete(self, title: str) -> bool:
        """Delete a note by title. Returns True if deleted."""
        path = self._note_path(title)
        if path.exists():
            path.unlink()
            return True
        return False

    def maintenance(self, stale_days: int = 90) -> dict:
        """Read-only analysis of the vault.

        Returns a report of duplicate candidates, orphan notes (no wikilinks
        in or out), and stale notes (not modified in stale_days days). Does
        not modify anything — the agent decides what action to take.
        """
        notes_data = []
        for md_file in self.vault_path.rglob("*.md"):
            try:
                parsed = self._parse_note(md_file)
            except OSError:
                continue
            title = parsed["frontmatter"].get("title", md_file.stem)
            content = parsed["content"]
            wikilinks = re.findall(r"\[\[([^\]]+)\]\]", content)
            modified_str = parsed["frontmatter"].get("modified", "")
            try:
                modified = datetime.fromisoformat(modified_str)
            except (ValueError, TypeError):
                modified = datetime.fromtimestamp(md_file.stat().st_mtime)
            notes_data.append(
                {
                    "title": title,
                    "path": str(md_file.relative_to(self.vault_path)),
                    "wikilinks": wikilinks,
                    "modified": modified,
                    "tags": parsed["frontmatter"].get("tags") or [],
                }
            )

        duplicates = _find_title_duplicates(notes_data)

        referenced: set[str] = set()
        for note in notes_data:
            for link in note["wikilinks"]:
                referenced.add(link.lower())
        orphans = [
            {"title": n["title"], "path": n["path"]}
            for n in notes_data
            if n["title"].lower() not in referenced and not n["wikilinks"]
        ]

        cutoff = datetime.now() - timedelta(days=stale_days)
        stale = [
            {
                "title": n["title"],
                "path": n["path"],
                "days_old": (datetime.now() - n["modified"]).days,
            }
            for n in notes_data
            if n["modified"] < cutoff
        ]

        tag_counts: dict[str, int] = {}
        for n in notes_data:
            for tag in n["tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_notes": len(notes_data),
            "duplicate_candidates": duplicates,
            "orphans": orphans,
            "stale": stale,
            "tag_counts": tag_counts,
        }

    def format_for_prompt(self, max_chars: int = 3000, core_max_chars: int = 2000) -> str:
        """Compose the wiki section of the system prompt.

        Two parts:
        1. Full content of notes in Core/ — always-in-context facts (user
           preferences, identity, environment) that the agent should know
           every turn without searching.
        2. Compact index of recent notes elsewhere — searchable handles.
        """
        core_block = self._format_core_notes(max_chars=core_max_chars)
        index_block = self._format_recent_index()

        if not core_block and not index_block:
            return ""

        parts = []
        if core_block:
            parts.append(core_block)
        if index_block:
            parts.append(index_block)
        result = "\n\n".join(parts)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n[...truncated]"
        return result

    def _format_core_notes(self, max_chars: int) -> str:
        """Inject full content of notes in the Core/ folder."""
        core_dir = self.vault_path / "Core"
        if not core_dir.exists():
            return ""
        sections = []
        total = 0
        for md_file in sorted(core_dir.rglob("*.md")):
            try:
                parsed = self._parse_note(md_file)
            except OSError:
                continue
            title = parsed["frontmatter"].get("title", md_file.stem)
            content = parsed["content"].strip()
            if not content:
                continue
            section = f"### [[{title}]]\n{content}"
            if total + len(section) > max_chars:
                break
            sections.append(section)
            total += len(section)
        if not sections:
            return ""
        return (
            "<wiki_core>\nAlways-in-context facts:\n\n" + "\n\n".join(sections) + "\n</wiki_core>"
        )

    def _format_recent_index(self) -> str:
        """Compact index of recent notes (excluding Core/)."""
        notes = [n for n in self.list_notes() if not n["path"].startswith("Core/")]
        notes = notes[: self.max_prompt_notes]
        if not notes:
            return ""
        lines = ["<wiki_memory>", "Recent knowledge notes (use wiki tool to read or search):"]
        for note in notes:
            tags_str = " ".join(f"#{t}" for t in note["tags"]) if note["tags"] else ""
            line = f"- [[{note['title']}]]"
            if tags_str:
                line += f" {tags_str}"
            if note["first_line"]:
                line += f" — {note['first_line']}"
            lines.append(line)
        lines.append("</wiki_memory>")
        return "\n".join(lines)


def _find_title_duplicates(notes: list[dict]) -> list[dict]:
    """Find pairs of notes with very similar titles."""
    duplicates = []
    for i, a in enumerate(notes):
        for b in notes[i + 1 :]:
            if _title_similar(a["title"], b["title"]):
                duplicates.append(
                    {
                        "titles": [a["title"], b["title"]],
                        "paths": [a["path"], b["path"]],
                    }
                )
    return duplicates


def _title_similar(a: str, b: str) -> bool:
    """Heuristic for flagging duplicate candidates.

    True if: titles match exactly, share a basename (Obsidian wikilinks
    resolve by basename), one contains the other, or word overlap >=60%.
    """
    a_low = a.lower().strip()
    b_low = b.lower().strip()
    if a_low == b_low:
        return True
    if a_low.rsplit("/", 1)[-1] == b_low.rsplit("/", 1)[-1]:
        return True
    if a_low in b_low or b_low in a_low:
        return True
    a_words = set(re.findall(r"\w+", a_low))
    b_words = set(re.findall(r"\w+", b_low))
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words)
    min_len = min(len(a_words), len(b_words))
    return overlap / min_len >= 0.6


def _excerpt(text: str, query: str, window: int = 120) -> str:
    """Return a short excerpt around the first match of query in text."""
    idx = text.lower().find(query)
    if idx == -1:
        return text[:window]
    start = max(0, idx - window // 2)
    end = min(len(text), idx + window // 2)
    snippet = text[start:end].replace("\n", " ")
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet += "…"
    return snippet
