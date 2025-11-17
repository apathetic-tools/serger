# tests/90_integration/test_deterministic_builds.py
"""Integration tests for deterministic builds with disabled timestamps.

These tests verify that builds with `disable_build_timestamp=True` produce
reproducible, deterministic output suitable for verification purposes.
"""

import re
from pathlib import Path

import pytest

import serger.cli as mod_cli
import serger.constants as mod_constants
import serger.meta as mod_meta
from tests.utils import make_test_package, write_config_file


def test_disable_build_timestamp_produces_identical_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two builds with disable_build_timestamp=True should produce identical output."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute: first build ---
    code1 = mod_cli.main([])
    assert code1 == 0
    output_file1 = tmp_path / "dist" / "mypkg.py"
    assert output_file1.exists()
    content1 = output_file1.read_text()

    # Delete the output file to force a fresh build
    output_file1.unlink()

    # --- execute: second build ---
    code2 = mod_cli.main([])
    assert code2 == 0
    output_file2 = tmp_path / "dist" / "mypkg.py"
    assert output_file2.exists()
    content2 = output_file2.read_text()

    # --- verify: outputs are identical ---
    assert content1 == content2, (
        "Two builds with disable_build_timestamp=True should produce identical output"
    )


def test_disable_build_timestamp_placeholder_in_header_comment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placeholder should appear in header comment when disabled."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    # Check header comment contains placeholder
    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    header_pattern = rf"# Build Date: {re.escape(placeholder)}"
    assert re.search(header_pattern, content), (
        f"Header comment should contain '# Build Date: {placeholder}'"
    )


def test_disable_build_timestamp_placeholder_in_docstring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placeholder should appear in docstring when disabled."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    # Check docstring contains placeholder
    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    docstring_pattern = rf"Built: {re.escape(placeholder)}"
    assert re.search(docstring_pattern, content), (
        f"Docstring should contain 'Built: {placeholder}'"
    )


def test_disable_build_timestamp_placeholder_in_constant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placeholder should appear in __build_date__ constant when disabled."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    # Check constant contains placeholder
    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    constant_pattern = rf'__build_date__ = "{re.escape(placeholder)}"'
    assert re.search(constant_pattern, content), (
        f"Constant should contain '__build_date__ = \"{placeholder}\"'"
    )


def test_disable_build_timestamp_version_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placeholder should be used as version fallback when no version found."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create a config without version (no pyproject.toml, no version in config)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
        # No version specified
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    # Check version fallback uses placeholder
    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    version_pattern = rf"# Version: {re.escape(placeholder)}"
    assert re.search(version_pattern, content), (
        f"Version fallback should use placeholder: '# Version: {placeholder}'"
    )


def test_disable_build_timestamp_false_uses_real_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When disable_build_timestamp=False, real timestamps should be used."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=False,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    # Check that real timestamp format is used (YYYY-MM-DD HH:MM:SS UTC)
    timestamp_pattern = r"# Build Date: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC"
    assert re.search(timestamp_pattern, content), (
        "Real timestamp should be used when disable_build_timestamp=False"
    )

    # Check that placeholder is NOT used
    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    assert placeholder not in content, (
        f"Placeholder '{placeholder}' should not appear when "
        "disable_build_timestamp=False"
    )


def test_disable_build_timestamp_cli_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI flag --disable-build-timestamp should override config setting."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Config has disable_build_timestamp=False
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=False,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute with CLI flag ---
    code = mod_cli.main(["--disable-build-timestamp"])
    assert code == 0

    # --- verify: placeholder is used (CLI overrides config) ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    header_pattern = rf"# Build Date: {re.escape(placeholder)}"
    assert re.search(header_pattern, content), (
        "CLI flag should override config and use placeholder"
    )


def test_disable_build_timestamp_config_file_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Config file setting should be respected when no CLI flag is provided."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Config has disable_build_timestamp=True
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute without CLI flag ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify: placeholder is used (from config) ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER
    header_pattern = rf"# Build Date: {re.escape(placeholder)}"
    assert re.search(header_pattern, content), "Config file setting should be respected"


def test_disable_build_timestamp_all_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Placeholder should appear in all expected locations when disabled."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        disable_build_timestamp=True,
    )

    monkeypatch.chdir(tmp_path)

    # --- execute ---
    code = mod_cli.main([])
    assert code == 0

    # --- verify: all locations contain placeholder ---
    output_file = tmp_path / "dist" / "mypkg.py"
    assert output_file.exists()
    content = output_file.read_text()

    placeholder = mod_constants.BUILD_TIMESTAMP_PLACEHOLDER

    # Check all expected locations
    assert f"# Build Date: {placeholder}" in content, (
        "Header comment should contain placeholder"
    )
    assert f"Built: {placeholder}" in content, "Docstring should contain placeholder"
    assert f'__build_date__ = "{placeholder}"' in content, (
        "Constant should contain placeholder"
    )
