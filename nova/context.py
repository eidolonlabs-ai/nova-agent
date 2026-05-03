"""Context file discovery, budgeting, and truncation.

Discovers project context files (AGENTS.md, SOUL.md, etc.) with:
- Explicit character budgets per file and total
- Head/tail truncation (70/20 ratio) preserving beginning and end
- Prompt injection scanning with unicode normalization
"""

import logging
import re
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)

# Threat patterns for prompt injection scanning
# Patterns are checked against unicode-normalized content (NFKC form)
_CONTEXT_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above|prior)\s+instructions', "prompt_injection"),
    (r'do\s+not\s+tell\s+the\s+user', "deception_hide"),
    (r'system\s+prompt\s+override', "sys_prompt_override"),
    (r'disregard\s+(your|all|any)\s+(instructions|rules|guidelines)', "disregard_rules"),
    (
        r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'t\s+have)\s+'
        r'(restrictions|limits|rules)',
        "bypass_restrictions",
    ),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)', "exfil_curl"),
    (r'cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass)', "read_secrets"),
    # Additional patterns for common injection techniques
    (r'forget\s+(all\s+)?(previous|prior|above)\s+(instructions|context)', "forget_instructions"),
    (r'you\s+are\s+now\s+(in\s+)?(developer|debug|unrestricted)\s+mode', "mode_switch"),
    (r'output\s+(only|just)\s+(the\s+)?(raw|full)\s+(response|answer)', "output_manipulation"),
    (r'base64\s*:\s*[A-Za-z0-9+/=]{20,}', "base64_payload"),
    (r'&#x[0-9a-fA-F]+;', "html_entity_encoding"),
    (r'\\u[0-9a-fA-F]{4}', "unicode_escape"),
]

# Invisible/zero-width characters that can be used to hide injection payloads
_CONTEXT_INVISIBLE_CHARS = {
    '\u200b', '\u200c', '\u200d', '\u2060', '\ufeff',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
    '\u200e', '\u200f', '\u2066', '\u2067', '\u2068', '\u2069',
    '\u00ad', '\u034f', '\u180e', '\u2000', '\u2001', '\u2002',
    '\u2003', '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
    '\u2009', '\u200a', '\u2061', '\u2062', '\u2063', '\u2064',
    '\u206a', '\u206b', '\u206c', '\u206d', '\u206e', '\u206f',
    '\u3164', '\uf8ff', '\uffa0',
}

# Truncation ratios (from OpenClaw)
_HEAD_RATIO = 0.70
_TAIL_RATIO = 0.20


def _normalize_for_scanning(content: str) -> str:
    """Normalize content for injection scanning.

    - Unicode NFKC normalization (converts homoglyphs to canonical form)
    - Strips invisible/zero-width characters
    - Lowercases for pattern matching
    """
    # NFKC normalization: converts compatibility characters to canonical form
    normalized = unicodedata.normalize("NFKC", content)
    # Remove invisible/zero-width characters
    normalized = "".join(
        ch for ch in normalized if ch not in _CONTEXT_INVISIBLE_CHARS
    )
    return normalized.lower()


def scan_context_content(content: str, filename: str) -> str | None:
    """Scan context file for injection patterns. Returns sanitized content or blocked message."""
    findings = []

    # Normalize content for scanning (NFKC + strip invisible chars)
    normalized = _normalize_for_scanning(content)

    for char in _CONTEXT_INVISIBLE_CHARS:
        if char in content:
            findings.append(f"invisible unicode U+{ord(char):04X}")

    for pattern, pid in _CONTEXT_THREAT_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            findings.append(pid)

    if findings:
        logger.warning("Context file %s blocked: %s", filename, ", ".join(findings))
        return f"[BLOCKED: {filename} contained potential prompt injection ({', '.join(findings)})]"

    return content


def truncate_with_head_tail(content: str, max_chars: int) -> str:
    """Truncate content preserving head (70%) and tail (20%) with a marker in between.

    This preserves the beginning (usually important setup/intro) and end
    (usually recent updates/current state) while dropping the middle.
    """
    if len(content) <= max_chars:
        return content

    head_chars = int(max_chars * _HEAD_RATIO)
    tail_chars = int(max_chars * _TAIL_RATIO)
    middle_chars = max_chars - head_chars - tail_chars

    if middle_chars <= 0:
        # Fallback: just take the head
        return content[:max_chars] + "\n\n[...truncated...]"

    head = content[:head_chars]
    tail = content[-tail_chars:]

    truncated_len = len(content) - head_chars - tail_chars
    marker = f"[...{truncated_len:,} chars truncated, read file for full content...]"
    return f"{head}\n\n{marker}\n\n{tail}"


def _find_git_root(start: Path) -> Path | None:
    """Walk up from start to find the git root."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def discover_context_files(
    cwd: Path | None = None,
    file_names: list[str] | None = None,
    max_chars_per_file: int = 10000,
    max_total_chars: int = 50000,
) -> list[tuple[str, str]]:
    """Discover and load context files from the workspace.

    Returns list of (filename, content) tuples, respecting budgets.
    Files are loaded in priority order until the total budget is exhausted.
    """
    if cwd is None:
        cwd = Path.cwd()
    if file_names is None:
        file_names = [".nova.md", "NOVA.md", "AGENTS.md", "SOUL.md", "CLAUDE.md", ".cursorrules"]

    cwd = cwd.resolve()
    git_root = _find_git_root(cwd)
    results = []
    total_chars = 0

    for filename in file_names:
        if total_chars >= max_total_chars:
            logger.info("Context file budget exhausted (%d/%d chars)", total_chars, max_total_chars)
            break

        # Search from cwd up to git root (inclusive)
        search_dirs = [cwd]
        if git_root and git_root != cwd:
            for parent in cwd.parents:
                search_dirs.append(parent)
                if parent == git_root:
                    break

        found = False
        for search_dir in search_dirs:
            candidate = search_dir / filename
            if candidate.exists() and candidate.is_file():
                try:
                    content = candidate.read_text(encoding="utf-8").strip()
                    if not content:
                        continue

                    # Scan for injection
                    content = scan_context_content(content, filename) or ""
                    if content.startswith("[BLOCKED:"):
                        results.append((filename, content))
                        found = True
                        break

                    # Truncate to per-file budget
                    content = truncate_with_head_tail(content, max_chars_per_file)

                    # Check total budget
                    remaining = max_total_chars - total_chars
                    if len(content) > remaining:
                        content = truncate_with_head_tail(content, remaining)

                    results.append((filename, content))
                    total_chars += len(content)
                    found = True
                    break
                except Exception as e:
                    logger.debug("Could not read %s: %s", candidate, e)

        if found:
            # Only load the first match (priority-based)
            continue

    return results


def build_context_prompt(
    cwd: Path | None = None,
    file_names: list[str] | None = None,
    max_chars_per_file: int = 10000,
    max_total_chars: int = 50000,
) -> str:
    """Build a formatted context block from discovered files."""
    files = discover_context_files(
        cwd=cwd,
        file_names=file_names,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
    )

    if not files:
        return ""

    sections = []
    for filename, content in files:
        sections.append(f"## {filename}\n\n{content}")

    return "# Project Context\n\n" + "\n\n".join(sections)
