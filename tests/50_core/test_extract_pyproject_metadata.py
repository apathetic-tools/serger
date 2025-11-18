# tests/50_core/test_extract_pyproject_metadata.py
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
    """Should read license file content when license points to a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license_path = Path(tmpdir) / "LICENSE.txt"

        # Create pyproject.toml
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = "LICENSE.txt" }
"""
        )

        # Create license file
        license_content = "MIT License\n\nCopyright (c) 2024 Test Author"
        license_path.write_text(license_content)

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        assert metadata.license_text == license_content


def test_extract_pyproject_metadata_license_file_missing() -> None:
    """Should fall back to message when license file doesn't exist."""
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
        # Should contain warning message for missing file
        assert "See LICENSE.txt" in metadata.license_text
        assert "distributed alongside this file" in metadata.license_text
        assert "for additional terms" in metadata.license_text
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


def test_extract_pyproject_metadata_license_text_key() -> None:
    """Should use text key from license dict."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { text = "MIT License" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_text == "MIT License"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_expression_key() -> None:
    """Should use expression key from license dict (alias for text)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { expression = "MIT OR Apache-2.0" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_text == "MIT OR Apache-2.0"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_priority_text_over_file() -> None:
    """Should prioritize text key over file key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license_path = Path(tmpdir) / "LICENSE.txt"

        # Create pyproject.toml with both text and file keys
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { text = "MIT License", file = "LICENSE.txt" }
"""
        )

        # Create license file (should be ignored due to priority)
        license_path.write_text("This should be ignored")

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        assert metadata.license_text == "MIT License"


def test_extract_pyproject_metadata_license_priority_expression_over_file() -> None:
    """Should prioritize expression key over file key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license_path = Path(tmpdir) / "LICENSE.txt"

        # Create pyproject.toml with both expression and file keys
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { expression = "MIT", file = "LICENSE.txt" }
"""
        )

        # Create license file (should be ignored due to priority)
        license_path.write_text("This should be ignored")

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        assert metadata.license_text == "MIT"


def test_extract_pyproject_metadata_license_priority_text_over_expression() -> None:
    """Should prioritize text key over expression key."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { text = "MIT License", expression = "MIT" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_text == "MIT License"
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_file_glob_pattern() -> None:
    """Should resolve glob pattern in file key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license1_path = Path(tmpdir) / "LICENSE.txt"
        license2_path = Path(tmpdir) / "LICENSE.md"

        # Create pyproject.toml with glob pattern
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = "LICENSE.*" }
"""
        )

        # Create multiple license files
        license1_path.write_text("MIT License")
        license2_path.write_text("Additional terms")

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        # Should contain both files (order may vary, so check for both)
        assert "MIT License" in metadata.license_text
        assert "Additional terms" in metadata.license_text


def test_extract_pyproject_metadata_license_file_list() -> None:
    """Should handle list of files in file key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license1_path = Path(tmpdir) / "LICENSE.txt"
        license2_path = Path(tmpdir) / "NOTICE.txt"

        # Create pyproject.toml with list of files
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = ["LICENSE.txt", "NOTICE.txt"] }
"""
        )

        # Create license files
        license1_path.write_text("MIT License")
        license2_path.write_text("Additional notice")

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        # Should contain both files
        assert "MIT License" in metadata.license_text
        assert "Additional notice" in metadata.license_text


def test_extract_pyproject_metadata_license_files_field() -> None:
    """Should extract license-files field."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = "MIT"
license-files = ["LICENSE.txt", "NOTICE.txt"]
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_text == "MIT"
        assert metadata.license_files == ["LICENSE.txt", "NOTICE.txt"]
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_files_single_string() -> None:
    """Should handle license-files as single string."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = "MIT"
license-files = "LICENSE.txt"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_files == ["LICENSE.txt"]
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_files_missing() -> None:
    """Should return None for license_files when field is missing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = "MIT"
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        assert metadata.license_files is None
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_file_glob_multiple() -> None:
    """Should handle glob pattern matching multiple files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pyproject_path = Path(tmpdir) / "pyproject.toml"
        license_dir = Path(tmpdir) / "licenses"
        license_dir.mkdir()
        license1_path = license_dir / "LICENSE.txt"
        license2_path = license_dir / "LICENSE-MIT.txt"
        license3_path = license_dir / "README.txt"  # Should not match

        # Create pyproject.toml with glob pattern
        pyproject_path.write_text(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = "licenses/LICENSE*.txt" }
"""
        )

        # Create license files
        license1_path.write_text("MIT License")
        license2_path.write_text("Additional terms")
        license3_path.write_text("Should not be included")

        metadata = mod_config_resolve.extract_pyproject_metadata(pyproject_path)
        assert metadata is not None
        # Should contain both LICENSE files but not README
        assert "MIT License" in metadata.license_text
        assert "Additional terms" in metadata.license_text
        assert "Should not be included" not in metadata.license_text


def test_extract_pyproject_metadata_license_file_missing_glob() -> None:
    """Should handle missing glob pattern with warning message."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { file = "LICENSE*.txt" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        # Should contain warning message for missing pattern
        assert "See LICENSE*.txt" in metadata.license_text
        assert "distributed alongside this file" in metadata.license_text
    finally:
        path.unlink()


def test_extract_pyproject_metadata_license_invalid_dict() -> None:
    """Should handle invalid license dict format gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(
            """[project]
name = "test-package"
version = "1.0.0"
license = { invalid_key = "value" }
"""
        )
        f.flush()
        path = Path(f.name)

    try:
        metadata = mod_config_resolve.extract_pyproject_metadata(path)
        assert metadata is not None
        # Should return empty license_text when no valid keys found
        assert metadata.license_text == ""
    finally:
        path.unlink()


# Note: Tests for missing tomli on Python 3.10 are complex to mock reliably.
# These would require mocking sys.modules or __import__, which is fragile.
# The functionality is tested indirectly through resolve_build_config tests.
