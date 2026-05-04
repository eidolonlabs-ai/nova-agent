"""Skills system — discovery, loading, and prompt generation.

Skills are directories containing SKILL.md files with YAML frontmatter.
Inspired by both Hermes-Agent (snapshot caching) and OpenClaw (compact XML format).
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns (frontmatter_dict, body_text).
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("\n---", 3)
    if end == -1:
        return {}, content

    body = content[end + 4 :].lstrip("\n")
    frontmatter_text = content[3:end].strip()

    # Simple YAML parsing (avoid pyyaml dependency for frontmatter)
    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value.startswith("[") and value.endswith("]"):
                # Parse list
                items = [item.strip().strip('"').strip("'") for item in value[1:-1].split(",")]
                frontmatter[key] = [i for i in items if i]
            else:
                frontmatter[key] = value  # type: ignore[assignment]

    return frontmatter, body


def extract_skill_description(frontmatter: dict, body: str, max_chars: int = 200) -> str:
    """Extract a short description for the skill index."""
    desc = frontmatter.get("description", "")
    if desc:
        return desc[:max_chars]

    # Fall back to first paragraph of body
    first_para = body.split("\n\n")[0].strip()
    # Strip markdown heading
    if first_para.startswith("#"):
        first_para = first_para.lstrip("#").strip()
    return first_para[:max_chars]


def discover_skills(
    skills_dir: Path,
    max_count: int = 50,
    max_chars: int = 15000,
) -> list[dict]:
    """Discover skills in a directory.

    Returns list of skill metadata dicts, sorted by category then name.
    """
    if not skills_dir.exists():
        return []

    skills = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        try:
            content = skill_file.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)

            name = frontmatter.get("name", skill_dir.name)
            category = frontmatter.get("category", "general")
            description = extract_skill_description(frontmatter, body)

            skills.append(
                {
                    "name": name,
                    "category": category,
                    "description": description,
                    "path": str(skill_file),
                }
            )
        except Exception as e:
            logger.debug("Failed to parse skill %s: %s", skill_dir, e)

    # Sort by category then name
    skills.sort(key=lambda s: (s["category"], s["name"]))

    # Apply limits
    return skills[:max_count]


def build_skills_prompt(
    skills: list[dict],
    max_chars: int = 15000,
) -> str:
    """Build a compact skills index for the system prompt.

    Uses XML-style format (inspired by OpenClaw) for efficient tokenization.
    """
    if not skills:
        return ""

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for skill in skills:
        by_category.setdefault(skill["category"], []).append(skill)

    lines = ["<skills>"]
    lines.append(
        "Before replying, check if any skill is directly relevant to the task. "
        "If so, load it with skill_view(name) and follow its instructions. "
        "Skills contain project-specific conventions and patterns that take precedence over general approaches. "
        "Only load a skill when it clearly applies \u2014 do not load skills speculatively."
    )

    for category in sorted(by_category.keys()):
        lines.append(f'  <category name="{category}">')
        for skill in by_category[category]:
            lines.append(f'    <skill name="{skill["name"]}">{skill["description"]}</skill>')
        lines.append("  </category>")

    lines.append("</skills>")

    result = "\n".join(lines)

    # Enforce character limit
    if len(result) > max_chars:
        result = result[:max_chars] + "\n  [...skills truncated...]"

    return result


def load_skill_content(skill_path: str) -> str | None:
    """Load the full content of a SKILL.md file."""
    path = Path(skill_path)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8")
        _, body = parse_frontmatter(content)
        return body
    except Exception as e:
        logger.error("Failed to load skill %s: %s", skill_path, e)
        return None
