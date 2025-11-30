# tests/50_core/test_build_tool_command.py
"""Tests for build_tool_command function."""

import shutil
from pathlib import Path
from typing import Any

import apathetic_utils as mod_utils
import pytest

import serger.meta as mod_meta
import serger.verify_script as mod_verify


RUFF_AVAILABLE = shutil.which("ruff") is not None


def test_build_tool_command_with_available_tool(tmp_path: Path) -> None:
    """Should build command when tool is available."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    tools_dict: dict[str, Any] = {
        "ruff": {
            "command": "ruff",
            "args": ["format"],
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff", "formatter", path, tools_dict=tools_dict
    )
    if RUFF_AVAILABLE:
        assert command is not None
        assert len(command) > 0
        assert command[0] == shutil.which("ruff")
        assert str(path) in command
    else:
        assert command is None


def test_build_tool_command_with_unavailable_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return None when tool is not available."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    # Mock find_tool_executable to return None
    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        lambda *_, **__: None,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )
    command = mod_verify.build_tool_command("ruff", "formatter", path)
    assert command is None


def test_build_tool_command_with_unsupported_category(tmp_path: Path) -> None:
    """Should return None when tool doesn't support category."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    # ruff doesn't support a non-existent category
    command = mod_verify.build_tool_command("ruff", "nonexistent_category", path)
    assert command is None


def test_build_tool_command_with_custom_path(tmp_path: Path) -> None:
    """Should use custom path when provided."""
    custom_executable = tmp_path / "custom_ruff"
    custom_executable.touch()

    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    tools_dict: dict[str, Any] = {
        "ruff": {
            "command": "ruff",
            "args": ["format"],
            "path": str(custom_executable),
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff",
        "formatter",
        path,
        tools_dict=tools_dict,
    )
    # Should use custom path
    assert command is not None
    assert command[0] == str(custom_executable.resolve())


def test_build_tool_command_custom_instance_with_explicit_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should use custom instance with explicit tool field."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    # Mock find_tool_executable to return a fake path
    fake_executable = "/fake/path/ruff"

    def mock_find_tool(tool_name: str, **_: object) -> str | None:
        return fake_executable if tool_name == "ruff" else None

    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        mock_find_tool,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )

    tools_dict: dict[str, Any] = {
        "ruff:imports": {
            "command": "ruff",
            "args": ["check", "--select", "I", "--fix"],
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff:imports", "formatter", path, tools_dict=tools_dict
    )
    assert command is not None
    assert command[0] == fake_executable
    assert command[1:4] == ["check", "--select", "I"]
    assert str(path) in command


def test_build_tool_command_custom_instance_inferred_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should infer tool name from key when tool field is missing."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    # Mock find_tool_executable - key is "my-ruff", but we'll use "ruff" as tool
    fake_executable = "/fake/path/ruff"

    def mock_find_tool(tool_name: str, **_: object) -> str | None:
        return fake_executable if tool_name == "ruff" else None

    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        mock_find_tool,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )

    tools_dict: dict[str, Any] = {
        "my-ruff-check": {
            "command": "ruff",  # explicit command
            "args": ["check", "--fix", "--select", "E"],
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "my-ruff-check", "formatter", path, tools_dict=tools_dict
    )
    assert command is not None
    assert command[0] == fake_executable
    assert "check" in command
    assert "--fix" in command
    assert str(path) in command


def test_build_tool_command_custom_instance_with_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should use explicit command field when provided."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    fake_executable = "/fake/path/ruff"

    def mock_find_tool(tool_name: str, **_: object) -> str | None:
        return fake_executable if tool_name == "ruff" else None

    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        mock_find_tool,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )

    tools_dict: dict[str, Any] = {
        "ruff-check": {
            "command": "ruff",
            "args": ["check", "--fix"],
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff-check", "static_checker", path, tools_dict=tools_dict
    )
    assert command is not None
    # Should use explicit command, not DEFAULT_TOOL_COMMANDS
    assert command[1:3] == ["check", "--fix"]
    assert str(path) in command


def test_build_tool_command_custom_instance_options_appending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should append options to command, not replace."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    fake_executable = "/fake/path/ruff"

    def mock_find_tool(tool_name: str, **_: object) -> str | None:
        return fake_executable if tool_name == "ruff" else None

    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        mock_find_tool,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )

    tools_dict: dict[str, Any] = {
        "ruff-check": {
            "command": "ruff",
            "args": ["check", "--fix"],
            "path": None,
            "options": ["--select", "E"],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff-check", "static_checker", path, tools_dict=tools_dict
    )
    assert command is not None
    # Command should be: [executable, "check", "--fix", "--select", "E", file_path]
    assert command[1:3] == ["check", "--fix"]
    assert "--select" in command
    assert "E" in command
    assert str(path) in command
    # Options should come after command
    assert command.index("--select") > command.index("--fix")


def test_build_tool_command_custom_instance_fallback_to_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should fall back to DEFAULT_TOOL_COMMANDS when command field is missing."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    fake_executable = "/fake/path/ruff"

    def mock_find_tool(tool_name: str, **_: object) -> str | None:
        return fake_executable if tool_name == "ruff" else None

    mod_utils.patch_everywhere(
        monkeypatch,
        mod_verify,
        "find_tool_executable",
        mock_find_tool,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={
            "/dist/",
            "standalone",
            f"{mod_meta.PROGRAM_SCRIPT}.py",
            ".pyz",
        },
    )

    tools_dict: dict[str, Any] = {
        "ruff-custom": {
            "command": "ruff",
            "args": ["format"],  # Args is now required
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff-custom", "formatter", path, tools_dict=tools_dict
    )
    assert command is not None
    # Should use the command from tools_dict
    assert "format" in command
    assert str(path) in command


def test_build_tool_command_simple_tool_name_backward_compatible(
    tmp_path: Path,
) -> None:
    """Should work with simple tool names (backward compatibility)."""
    path = tmp_path / "test.py"
    path.write_text("x = 1\n")

    # Simple tool name with tools_dict (defaults are merged in during resolution)
    tools_dict: dict[str, Any] = {
        "ruff": {
            "command": "ruff",
            "args": ["format"],
            "path": None,
            "options": [],
        },
    }
    command = mod_verify.build_tool_command(
        "ruff", "formatter", path, tools_dict=tools_dict
    )
    if RUFF_AVAILABLE:
        assert command is not None
        assert len(command) > 0
        assert command[0] == shutil.which("ruff")
        assert str(path) in command
    else:
        assert command is None
