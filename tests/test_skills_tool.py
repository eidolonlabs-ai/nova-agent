"""Tests for the skills tool."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from nova.tools.skills_tool import _skill_manage, _skill_view, _skills_list


@pytest.fixture
def temp_skills_dir():
    tmpdir = tempfile.mkdtemp()
    return Path(tmpdir)


@pytest.fixture
def skills_config(temp_skills_dir):
    return {
        "skills": {
            "directory": str(temp_skills_dir),
        }
    }


def test_skills_list_no_skills(skills_config):
    result = _skills_list({}, config=skills_config)
    assert "No skills found" in result


def test_skills_list_with_skills(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: test_skill\ndescription: Test\n---\nContent here")

    with patch("nova.tools.skills_tool.discover_skills") as mock_discover, \
         patch("nova.tools.skills_tool.build_skills_prompt") as mock_build:
        mock_discover.return_value = [{"name": "test_skill"}]
        mock_build.return_value = "Found: test_skill"
        result = _skills_list({}, config=skills_config)

    assert "Found: test_skill" in result


def test_skill_view_success(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "my_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: my_skill\n---\nSkill content")

    result = _skill_view({"name": "my_skill"}, config=skills_config)
    assert "Skill content" in result


def test_skill_view_not_found(temp_skills_dir, skills_config):
    with patch("nova.tools.skills_tool.load_skill_content") as mock_load:
        mock_load.return_value = None
        result = _skill_view({"name": "nonexistent"}, config=skills_config)
    assert "not found" in result


def test_skill_manage_create_success(temp_skills_dir, skills_config):
    result = _skill_manage(
        {
            "action": "create",
            "name": "new_skill",
            "category": "test",
            "description": "A test skill",
            "content": "# New Skill\nThis is new.",
        },
        config=skills_config,
    )
    assert "Created skill" in result
    skill_file = temp_skills_dir / "new_skill" / "SKILL.md"
    assert skill_file.exists()
    content = skill_file.read_text()
    assert "new_skill" in content
    assert "A test skill" in content
    assert "# New Skill" in content


def test_skill_manage_create_already_exists(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "existing"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: existing\n---\nContent")

    result = _skill_manage(
        {
            "action": "create",
            "name": "existing",
            "content": "new content",
        },
        config=skills_config,
    )
    assert "already exists" in result


def test_skill_manage_create_missing_name(temp_skills_dir, skills_config):
    result = _skill_manage(
        {
            "action": "create",
            "name": "",
            "content": "content",
        },
        config=skills_config,
    )
    assert "Error" in result
    assert "name" in result


def test_skill_manage_patch_success(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "existing"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: existing\ncategory: test\n---\nOld content")

    result = _skill_manage(
        {
            "action": "patch",
            "name": "existing",
            "content": "Updated content",
        },
        config=skills_config,
    )
    assert "Updated skill" in result
    updated = skill_file.read_text()
    assert "Updated content" in updated
    assert "name: existing" in updated  # frontmatter preserved


def test_skill_manage_patch_not_found(temp_skills_dir, skills_config):
    result = _skill_manage(
        {
            "action": "patch",
            "name": "nonexistent",
            "content": "content",
        },
        config=skills_config,
    )
    assert "not found" in result


def test_skill_manage_patch_missing_content(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "existing"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: existing\n---\nContent")

    result = _skill_manage(
        {
            "action": "patch",
            "name": "existing",
            "content": "",
        },
        config=skills_config,
    )
    assert "Error" in result
    assert "content" in result


def test_skill_manage_delete_success(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "to_delete"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: to_delete\n---\nContent")

    result = _skill_manage(
        {"action": "delete", "name": "to_delete"},
        config=skills_config,
    )
    assert "Deleted skill" in result
    assert not skill_file.exists()
    assert not skill_dir.exists()


def test_skill_manage_delete_not_found(temp_skills_dir, skills_config):
    result = _skill_manage(
        {"action": "delete", "name": "nonexistent"},
        config=skills_config,
    )
    assert "not found" in result


def test_skill_manage_delete_preserves_non_empty_dir(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "partial_delete"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: partial_delete\n---\nContent")
    other_file = skill_dir / "other.txt"
    other_file.write_text("keep this")

    result = _skill_manage(
        {"action": "delete", "name": "partial_delete"},
        config=skills_config,
    )
    assert "Deleted skill" in result
    assert not skill_file.exists()
    assert skill_dir.exists()  # Dir preserved because it's not empty
    assert other_file.exists()


def test_skill_manage_unknown_action(temp_skills_dir, skills_config):
    result = _skill_manage(
        {"action": "invalid_action", "name": "test"},
        config=skills_config,
    )
    assert "Error" in result
    assert "Unknown action" in result


def test_skill_manage_patch_with_list_in_frontmatter(temp_skills_dir, skills_config):
    skill_dir = temp_skills_dir / "with_list"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    # Frontmatter with a list field
    skill_file.write_text('---\nname: with_list\ntags: ["python", "data"]\n---\nContent')

    result = _skill_manage(
        {
            "action": "patch",
            "name": "with_list",
            "content": "New content",
        },
        config=skills_config,
    )
    assert "Updated skill" in result
    updated = skill_file.read_text()
    assert "New content" in updated
    assert "with_list" in updated


def test_skill_manage_create_default_category(temp_skills_dir, skills_config):
    result = _skill_manage(
        {
            "action": "create",
            "name": "default_cat",
            "content": "content",
        },
        config=skills_config,
    )
    assert "Created skill" in result
    skill_file = temp_skills_dir / "default_cat" / "SKILL.md"
    content = skill_file.read_text()
    assert "category: general" in content
