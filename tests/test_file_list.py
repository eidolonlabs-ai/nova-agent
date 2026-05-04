"""Tests for file_list tool."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from nova.tools.file_list import _list_files


@pytest.fixture
def temp_project():
    """Create a temporary project structure."""
    with TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create some files
        (root / "main.py").write_text("def main(): pass")
        (root / "test.py").write_text("def test(): pass")
        (root / "config.yaml").write_text("key: value")

        # Create nested structure
        (root / "src").mkdir()
        (root / "src" / "module.py").write_text("def module_fn(): pass")
        (root / "src" / "helper.py").write_text("def helper(): pass")

        # Create excluded directories
        (root / ".git").mkdir()
        (root / ".git" / "config").write_text("")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "main.cpython-39.pyc").write_text("")

        yield root


class TestListFiles:
    """Tests for list_files tool."""

    def test_list_python_files(self, temp_project):
        """Test listing Python files."""
        result = _list_files({"pattern": "*.py", "root": str(temp_project)})
        assert "main.py" in result
        assert "test.py" in result

    def test_list_recursive(self, temp_project):
        """Test recursive glob pattern."""
        result = _list_files(
            {
                "pattern": "**/*.py",
                "root": str(temp_project),
            }
        )
        assert "main.py" in result
        assert "module.py" in result
        assert "helper.py" in result

    def test_list_with_limit(self, temp_project):
        """Test result limit."""
        result = _list_files(
            {
                "pattern": "*.py",
                "root": str(temp_project),
                "limit": 1,
            }
        )
        # Should show at most 1 file
        lines = result.split("\n")
        file_lines = [line for line in lines if line.strip().endswith(".py")]
        assert len(file_lines) <= 1

    def test_list_absolute_paths(self, temp_project):
        """Test absolute path output."""
        result = _list_files(
            {
                "pattern": "*.py",
                "root": str(temp_project),
                "absolute": True,
            }
        )
        # Should contain full path
        assert str(temp_project) in result

    def test_list_excludes_git(self, temp_project):
        """Test that .git is excluded."""
        result = _list_files(
            {
                "pattern": "**/*",
                "root": str(temp_project),
            }
        )
        assert ".git" not in result
        # Verify .git/config is excluded (but config.yaml is ok)
        assert ".git/config" not in result and "/.git/" not in result

    def test_list_excludes_pycache(self, temp_project):
        """Test that __pycache__ is excluded."""
        result = _list_files(
            {
                "pattern": "**/*.pyc",
                "root": str(temp_project),
            }
        )
        # Should not find .pyc files in __pycache__
        assert "pycache" not in result or "__pycache__" not in result

    def test_list_no_matches(self, temp_project):
        """Test pattern with no matches."""
        result = _list_files(
            {
                "pattern": "*.nonexistent",
                "root": str(temp_project),
            }
        )
        assert "No files found" in result

    def test_list_invalid_pattern(self, temp_project):
        """Test empty pattern."""
        result = _list_files({"pattern": "", "root": str(temp_project)})
        assert "Error:" in result

    def test_list_invalid_root(self):
        """Test invalid root directory."""
        result = _list_files(
            {
                "pattern": "*.py",
                "root": "/nonexistent/directory",
            }
        )
        assert "Error:" in result
        assert "not found" in result.lower()

    def test_list_root_not_directory(self, temp_project):
        """Test root that is a file, not directory."""
        file_path = temp_project / "main.py"
        result = _list_files(
            {
                "pattern": "*.py",
                "root": str(file_path),
            }
        )
        assert "Error:" in result
        assert "not a directory" in result.lower()

    def test_list_large_result_truncation(self, temp_project):
        """Test that large results show truncation."""
        # Create many files
        for i in range(150):
            (temp_project / f"file_{i}.txt").write_text(f"content {i}")

        result = _list_files(
            {
                "pattern": "*.txt",
                "root": str(temp_project),
                "limit": 100,
            }
        )
        assert "Truncated at 100" in result

    def test_list_yaml_files(self, temp_project):
        """Test filtering specific file type."""
        result = _list_files(
            {
                "pattern": "*.yaml",
                "root": str(temp_project),
            }
        )
        assert "config.yaml" in result
        assert "py" not in result  # Should not have .py files
