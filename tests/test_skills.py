"""Tests for skills system — discovery, loading, and prompt generation."""

import tempfile
from pathlib import Path

from nova.skills import (
    build_skills_prompt,
    discover_skills,
    extract_skill_description,
    load_skill_content,
    parse_frontmatter,
)


def _create_skill_dir(tmpdir: Path, name: str, content: str) -> Path:
    """Create a skill directory with a SKILL.md file."""
    skill_dir = tmpdir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


def test_parse_frontmatter_basic():
    """Test parsing simple YAML frontmatter."""
    content = """---
name: test-skill
category: testing
description: A test skill
---
This is the body."""
    fm, body = parse_frontmatter(content)
    assert fm["name"] == "test-skill"
    assert fm["category"] == "testing"
    assert fm["description"] == "A test skill"
    assert body.strip() == "This is the body."


def test_parse_frontmatter_with_list():
    """Test parsing frontmatter with list values."""
    content = """---
name: list-skill
tags: [python, testing, unit]
---
Body content here."""
    fm, body = parse_frontmatter(content)
    assert fm["name"] == "list-skill"
    assert fm["tags"] == ["python", "testing", "unit"]


def test_parse_frontmatter_no_frontmatter():
    """Test parsing content without frontmatter."""
    content = "Just plain text, no frontmatter."
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_parse_frontmatter_unclosed():
    """Test parsing content with unclosed frontmatter."""
    content = """---
name: broken
This frontmatter is not closed.
Some body text."""
    fm, body = parse_frontmatter(content)
    assert fm == {}
    assert body == content


def test_extract_description_from_frontmatter():
    """Test that description is extracted from frontmatter first."""
    fm = {"description": "This is the description."}
    body = "This is the body which is different."
    desc = extract_skill_description(fm, body)
    assert desc == "This is the description."


def test_extract_description_fallback_to_body():
    """Test that description falls back to body if not in frontmatter."""
    fm = {}
    body = "This is the first paragraph.\n\nSecond paragraph."
    desc = extract_skill_description(fm, body)
    assert "first paragraph" in desc


def test_extract_description_strips_markdown_heading():
    """Test that markdown headings are stripped from body description."""
    fm = {}
    body = "# My Skill\n\nThis is a great skill."
    desc = extract_skill_description(fm, body)
    assert "#" not in desc
    assert "My Skill" in desc


def test_extract_description_max_chars():
    """Test that description is truncated to max_chars."""
    fm = {"description": "A" * 500}
    desc = extract_skill_description(fm, "", max_chars=100)
    assert len(desc) <= 100


def test_discover_skills_empty_dir():
    """Test discovering skills in an empty directory."""
    tmpdir = Path(tempfile.mkdtemp())
    skills = discover_skills(tmpdir)
    assert skills == []


def test_discover_skills_nonexistent_dir():
    """Test discovering skills in a nonexistent directory."""
    skills = discover_skills(Path("/nonexistent/path/xyz"))
    assert skills == []


def test_discover_skills_single_skill():
    """Test discovering a single skill."""
    tmpdir = Path(tempfile.mkdtemp())
    _create_skill_dir(
        tmpdir,
        "test-skill",
        """---
name: test-skill
category: testing
description: A test skill for unit tests
---
This is the skill body with detailed instructions.
""",
    )

    skills = discover_skills(tmpdir)
    assert len(skills) == 1
    assert skills[0]["name"] == "test-skill"
    assert skills[0]["category"] == "testing"
    assert "test skill" in skills[0]["description"]


def test_discover_skills_multiple_sorted():
    """Test that skills are sorted by category then name."""
    tmpdir = Path(tempfile.mkdtemp())
    _create_skill_dir(tmpdir, "beta", "---\nname: beta\ncategory: z-category\ndescription: Beta skill\n---\nBody")
    _create_skill_dir(tmpdir, "alpha", "---\nname: alpha\ncategory: a-category\ndescription: Alpha skill\n---\nBody")
    _create_skill_dir(tmpdir, "gamma", "---\nname: gamma\ncategory: a-category\ndescription: Gamma skill\n---\nBody")

    skills = discover_skills(tmpdir)
    assert len(skills) == 3
    # Sorted by category first, then name
    assert skills[0]["name"] == "alpha"
    assert skills[1]["name"] == "gamma"
    assert skills[2]["name"] == "beta"


def test_discover_skills_max_count():
    """Test that max_count limits the number of skills returned."""
    tmpdir = Path(tempfile.mkdtemp())
    for i in range(10):
        _create_skill_dir(
            tmpdir,
            f"skill-{i}",
            f"---\nname: skill-{i}\ncategory: general\ndescription: Skill {i}\n---\nBody",
        )

    skills = discover_skills(tmpdir, max_count=5)
    assert len(skills) == 5


def test_discover_skills_ignores_non_dirs():
    """Test that non-directory entries are ignored."""
    tmpdir = Path(tempfile.mkdtemp())
    # Create a file (not a directory) with SKILL.md
    (tmpdir / "not-a-dir.md").write_text("---\nname: fake\n---\nBody")

    skills = discover_skills(tmpdir)
    assert skills == []


def test_discover_skills_ignores_dirs_without_skill_md():
    """Test that directories without SKILL.md are ignored."""
    tmpdir = Path(tempfile.mkdtemp())
    (tmpdir / "no-skill-file").mkdir()

    skills = discover_skills(tmpdir)
    assert skills == []


def test_build_skills_prompt_empty():
    """Test that empty skills list returns empty string."""
    result = build_skills_prompt([])
    assert result == ""


def test_build_skills_prompt_basic():
    """Test building a basic skills prompt."""
    skills = [
        {"name": "python-coding", "category": "coding", "description": "Python best practices"},
        {"name": "git-workflow", "category": "workflow", "description": "Git commands and workflows"},
    ]

    result = build_skills_prompt(skills)
    assert "<skills>" in result
    assert "</skills>" in result
    assert "python-coding" in result
    assert "git-workflow" in result
    assert "<category name=\"coding\">" in result
    assert "<category name=\"workflow\">" in result


def test_build_skills_prompt_groups_by_category():
    """Test that skills are grouped by category."""
    skills = [
        {"name": "skill-a", "category": "cat1", "description": "A"},
        {"name": "skill-b", "category": "cat1", "description": "B"},
        {"name": "skill-c", "category": "cat2", "description": "C"},
    ]

    result = build_skills_prompt(skills)
    # cat1 should appear once with two skills
    assert result.count("<category name=\"cat1\">") == 1
    assert result.count("skill-a") == 1
    assert result.count("skill-b") == 1
    assert result.count("skill-c") == 1


def test_build_skills_prompt_max_chars():
    """Test that skills prompt is truncated when exceeding max_chars."""
    skills = [
        {"name": f"skill-{i}", "category": "general", "description": f"Description {i} " * 20}
        for i in range(50)
    ]

    result = build_skills_prompt(skills, max_chars=500)
    assert len(result) <= 550  # Allow tolerance for truncation marker
    assert "truncated" in result


def test_load_skill_content():
    """Test loading skill content from a file."""
    tmpdir = Path(tempfile.mkdtemp())
    skill_file = tmpdir / "SKILL.md"
    skill_file.write_text("# Test Skill\n\nSome content.", encoding="utf-8")

    result = load_skill_content(str(skill_file))
    assert result is not None
    assert "Test Skill" in result


def test_load_skill_content_nonexistent():
    """Test loading content from a nonexistent file."""
    result = load_skill_content("/nonexistent/path/SKILL.md")
    assert result is None
