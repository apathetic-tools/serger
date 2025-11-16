# tests/5_core/test_extract_pyproject_metadata.py
"""Tests for extract_pyproject_metadata function."""

import tempfile
from pathlib import Path

import serger.config.config_resolve as mod_config_resolve


def test_extract_pyproject_metadata_all_fields() -> None:
    """Should extract all fields from valid pyproject.toml."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.2.3"
description = "A test package"
license = "MIT"
authors = [
    {name = "Test Author", email = "test@example.com"}
]
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.name == "test-package"
        assert metadata.version == "1.2.3"
        assert metadata.description == "A test package"
        assert metadata.license_text == "MIT"
        assert metadata.authors == "Test Author <test@example.com>"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_file_format() -> None:
    """Should handle license with file format."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = "LICENSE.txt" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        expected = "See LICENSE.txt if distributed alongside this script"
        assert metadata.license_text == expected
    finally:
        path.unlink()


def test_extract_pyproject_metadata_missing_file() -> None:
    """Should return empty metadata if file doesn't exist."""
    path = Path("/nonexistent/pyproject.toml")
    metadata = mod_config_resolve.extract_pyproject_metadata(path)
    assert metadata is not None
    assert metadata.name == ""
    assert metadata.version == ""
    assert metadata.description == ""
    assert metadata.license_text == ""
    assert metadata.authors == ""
    assert not metadata.has_any()


def test_extract_pyproject_metadata_partial_fields() -> None:
    """Should extract only available fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.name == "test-package"
        assert metadata.version == "1.0.0"
        assert metadata.description == ""
        assert metadata.license_text == ""
        assert metadata.authors == ""
    finally:
        path.unlink()


def test_extract_pyproject_metadata_invalid_toml() -> None:
    """Should return empty metadata for invalid TOML."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write("invalid toml content {[}\n")
        f.flush()
        path = Path(f.name)

    try:
        # Should return empty metadata (not raise)
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert not metadata.has_any()
    finally:
        path.unlink()


def test_extract_pyproject_metadata_no_project_section() -> None:
    """Should return empty metadata if [project] section is missing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[tool.other]
some_setting = "value"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert not metadata.has_any()
    finally:
        path.unlink()


def test_extract_pyproject_metadata_authors_single() -> None:
    """Should extract single author with name only."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
authors = [
    {name = "John Doe"}
]
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.authors == "John Doe"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_authors_with_email() -> None:
    """Should extract author with name and email."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
authors = [
    {name = "Jane Smith", email = "jane@example.com"}
]
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.authors == "Jane Smith <jane@example.com>"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_authors_multiple() -> None:
    """Should extract multiple authors and format as comma-separated."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
authors = [
    {name = "Alice", email = "alice@example.com"},
    {name = "Bob"},
    {name = "Charlie", email = "charlie@example.com"}
]
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        expected = "Alice <alice@example.com>, Bob, Charlie <charlie@example.com>"
        assert metadata.authors == expected
    finally:
        path.unlink()


def test_extract_pyproject_metadata_authors_empty_list() -> None:
    """Should return empty authors string for empty authors list."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
authors = []
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.authors == ""
    finally:
        path.unlink()


def test_extract_pyproject_metadata_authors_missing() -> None:
    """Should return empty authors string when authors field is missing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.authors == ""
    finally:
        path.unlink()


# Note: Tests for missing tomli on Python 3.10 are complex to mock reliably.
# These would require mocking sys.modules or __import__, which is fragile.
# The functionality is tested indirectly through resolve_build_config tests.
