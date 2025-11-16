"""Tests for serger.module_actions.extract_module_name_from_source_path."""

from pathlib import Path

import pytest

import serger.module_actions as mod_module_actions


def test_extract_module_name_exact_match(tmp_path: Path) -> None:
    """Test that exact module name match works."""
    # Setup: Create file structure
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    utils_file = pkg_dir / "utils.py"
    utils_file.write_text("def helper(): pass\n")

    package_root = tmp_path
    expected_source = "mypkg.utils"

    # Should not raise and return extracted module name
    result = mod_module_actions.extract_module_name_from_source_path(
        utils_file, package_root, expected_source
    )
    assert result == "mypkg.utils"


def test_extract_module_name_suffix_match(tmp_path: Path) -> None:
    """Test that suffix match works (extracted ends with .expected)."""
    # Setup: Create file structure
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    utils_file = pkg_dir / "utils.py"
    utils_file.write_text("def helper(): pass\n")

    package_root = tmp_path
    expected_source = "utils"  # Shorter than extracted "mypkg.utils"

    # Should not raise - suffix match is allowed
    result = mod_module_actions.extract_module_name_from_source_path(
        utils_file, package_root, expected_source
    )
    assert result == "mypkg.utils"


def test_extract_module_name_prefix_match_error(tmp_path: Path) -> None:
    """Test that prefix match (expected longer than extracted) raises error."""
    # Setup: Create file structure
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    utils_file = pkg_dir / "utils.py"
    utils_file.write_text("def helper(): pass\n")

    package_root = tmp_path
    expected_source = "mypkg.sub.utils"  # Longer than extracted "mypkg.utils"

    # Should raise ValueError - extracted name is shorter than expected
    with pytest.raises(ValueError, match="does not match expected source"):
        mod_module_actions.extract_module_name_from_source_path(
            utils_file, package_root, expected_source
        )


def test_extract_module_name_no_match_error(tmp_path: Path) -> None:
    """Test that name mismatch raises ValueError."""
    # Setup: Create file structure
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    utils_file = pkg_dir / "utils.py"
    utils_file.write_text("def helper(): pass\n")

    package_root = tmp_path
    expected_source = "otherpkg.other"  # Doesn't match

    # Should raise ValueError
    with pytest.raises(ValueError, match="does not match expected source"):
        mod_module_actions.extract_module_name_from_source_path(
            utils_file, package_root, expected_source
        )


def test_extract_module_name_file_not_exists_error(tmp_path: Path) -> None:
    """Test that non-existent file raises ValueError."""
    nonexistent_file = tmp_path / "nonexistent.py"
    package_root = tmp_path
    expected_source = "mypkg.utils"

    # Should raise ValueError
    with pytest.raises(ValueError, match="does not exist"):
        mod_module_actions.extract_module_name_from_source_path(
            nonexistent_file, package_root, expected_source
        )


def test_extract_module_name_not_python_file_error(tmp_path: Path) -> None:
    """Test that non-Python file raises ValueError."""
    # Setup: Create non-Python file
    txt_file = tmp_path / "file.txt"
    txt_file.write_text("not python\n")

    package_root = tmp_path
    expected_source = "file"

    # Should raise ValueError
    with pytest.raises(ValueError, match="must be a Python file"):
        mod_module_actions.extract_module_name_from_source_path(
            txt_file, package_root, expected_source
        )


def test_extract_module_name_nested_package(tmp_path: Path) -> None:
    """Test that nested package structure works."""
    # Setup: Create nested package structure
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    sub_dir = pkg_dir / "sub"
    sub_dir.mkdir()
    module_file = sub_dir / "module.py"
    module_file.write_text("def func(): pass\n")

    package_root = tmp_path
    expected_source = "mypkg.sub.module"

    # Should not raise
    result = mod_module_actions.extract_module_name_from_source_path(
        module_file, package_root, expected_source
    )
    assert result == "mypkg.sub.module"


def test_extract_module_name_file_not_under_root(tmp_path: Path) -> None:
    """Test that file not under package_root still works."""
    # Setup: Create file outside package_root
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    utils_file = other_dir / "utils.py"
    utils_file.write_text("def helper(): pass\n")

    package_root = tmp_path / "mypkg"  # Different root
    package_root.mkdir()
    expected_source = "utils"  # Just filename

    # Should not raise - uses filename when file not under root
    result = mod_module_actions.extract_module_name_from_source_path(
        utils_file, package_root, expected_source
    )
    assert result == "utils"
