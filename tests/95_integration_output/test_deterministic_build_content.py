# tests/95_integration_output/test_deterministic_build_content.py
"""Integration tests for deterministic build output content.

These tests verify that builds with disabled timestamps produce
identical, reproducible output suitable for verification purposes.
They check the actual content of generated build files.
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


def test_disable_build_timestamp_cli_produces_identical_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two builds using CLI --disable-build-timestamp produce identical output."""
    # --- setup ---
    pkg_dir = tmp_path / "mypkg"
    make_test_package(pkg_dir)

    # Create config WITHOUT disable_build_timestamp (will use CLI flag instead)
    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=["mypkg/**/*.py"],
        out="dist/mypkg.py",
        # No disable_build_timestamp in config - will use CLI flag
    )

    monkeypatch.chdir(tmp_path)

    # --- execute: first build with CLI flag ---
    code1 = mod_cli.main(["--disable-build-timestamp"])
    assert code1 == 0
    output_file1 = tmp_path / "dist" / "mypkg.py"
    assert output_file1.exists()
    content1 = output_file1.read_text()

    # Delete the output file to force a fresh build
    output_file1.unlink()

    # --- execute: second build with CLI flag ---
    code2 = mod_cli.main(["--disable-build-timestamp"])
    assert code2 == 0
    output_file2 = tmp_path / "dist" / "mypkg.py"
    assert output_file2.exists()
    content2 = output_file2.read_text()

    # --- verify: outputs are identical ---
    assert content1 == content2, (
        "Two builds with --disable-build-timestamp CLI flag should produce "
        "identical output"
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


def test_package_ordering_determinism_multiple_top_level_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Package ordering should be deterministic when multiple top-level packages exist.

    This test verifies that when multiple packages have the same depth (e.g., both
    are top-level packages with 0 dots), they are ordered deterministically by name
    to ensure reproducible builds.
    """
    # --- setup: create multiple top-level packages ---
    # Create apathetic_logging package
    logging_pkg = tmp_path / "apathetic_logging"
    make_test_package(
        logging_pkg,
        module_name="logger",
        module_content='def get_logger():\n    return "logger"\n',
    )

    # Create apathetic_utils package
    utils_pkg = tmp_path / "apathetic_utils"
    make_test_package(
        utils_pkg,
        module_name="helpers",
        module_content='def helper():\n    return "helper"\n',
    )

    # Create a main package that imports from both
    main_pkg = tmp_path / "mypkg"
    make_test_package(
        main_pkg,
        module_name="main",
        module_content=(
            "from apathetic_logging.logger import get_logger\n"
            "from apathetic_utils.helpers import helper\n"
            'def main():\n    return "main"\n'
        ),
    )

    config = tmp_path / f".{mod_meta.PROGRAM_CONFIG}.json"
    write_config_file(
        config,
        package="mypkg",
        include=[
            "mypkg/**/*.py",
            "apathetic_logging/**/*.py",
            "apathetic_utils/**/*.py",
        ],
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

    # Extract the order of _create_pkg_module calls
    pkg_calls1 = re.findall(r'_create_pkg_module\("([^"]+)"\)', content1)

    # Delete the output file to force a fresh build
    output_file1.unlink()

    # --- execute: second build ---
    code2 = mod_cli.main([])
    assert code2 == 0
    output_file2 = tmp_path / "dist" / "mypkg.py"
    assert output_file2.exists()
    content2 = output_file2.read_text()

    # Extract the order of _create_pkg_module calls
    pkg_calls2 = re.findall(r'_create_pkg_module\("([^"]+)"\)', content2)

    # --- verify: outputs are identical ---
    assert content1 == content2, (
        "Two builds with multiple top-level packages should produce identical output"
    )

    # --- verify: package order is deterministic ---
    # Both top-level packages (apathetic_logging, apathetic_utils) should appear
    # in the same order in both builds
    assert pkg_calls1 == pkg_calls2, (
        f"Package order should be deterministic. "
        f"First build: {pkg_calls1}, Second build: {pkg_calls2}"
    )

    # Verify that apathetic_logging comes before apathetic_utils (alphabetical)
    # This ensures the secondary sort key (package name) is working
    logging_idx1 = (
        pkg_calls1.index("apathetic_logging")
        if "apathetic_logging" in pkg_calls1
        else -1
    )
    utils_idx1 = (
        pkg_calls1.index("apathetic_utils") if "apathetic_utils" in pkg_calls1 else -1
    )
    if logging_idx1 >= 0 and utils_idx1 >= 0:
        assert logging_idx1 < utils_idx1, (
            "apathetic_logging should come before apathetic_utils "
            "(alphabetical ordering)"
        )
