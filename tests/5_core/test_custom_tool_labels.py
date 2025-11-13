# tests/5_core/test_custom_tool_labels.py
"""Tests for custom tool labels in post-processing configuration."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import serger.config.config_resolve as mod_resolve
import serger.config.config_types as mod_types
import serger.constants as mod_constants
import serger.verify_script as mod_verify


def test_custom_labels_in_user_config_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should handle custom labels in user config priority."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            executed_commands.append(command)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            return f"/fake/path/{tool_name}"

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        # User config with custom labels in priority
        build_cfg: mod_types.BuildConfig = {
            "post_processing": {
                "categories": {
                    "formatter": {
                        "priority": ["ruff:first", "ruff:second"],
                        "tools": {
                            "ruff:first": {
                                "command": "ruff",
                                "args": ["check", "--fix"],
                            },
                            "ruff:second": {
                                "command": "ruff",
                                "args": ["format"],
                            },
                        },
                    },
                },
            },
        }
        resolved = mod_resolve.resolve_post_processing(build_cfg, None)
        mod_verify.execute_post_processing(path, resolved)

        # Should have executed both custom label commands
        assert len(executed_commands) >= 1
        # Both should be in priority
        formatter = resolved["categories"]["formatter"]
        assert formatter.get("priority") == ["ruff:first", "ruff:second"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
    finally:
        path.unlink(missing_ok=True)


def test_custom_labels_in_default_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should handle custom labels in DEFAULT_CATEGORIES priority."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            executed_commands.append(command)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            return f"/fake/path/{tool_name}"

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        # Temporarily modify DEFAULT_CATEGORIES to have custom labels
        original_formatter = mod_constants.DEFAULT_CATEGORIES["formatter"].copy()
        mod_constants.DEFAULT_CATEGORIES["formatter"] = {
            "enabled": True,
            "priority": ["ruff:check", "ruff:format"],
            "tools": {
                "ruff:check": {
                    "command": "ruff",
                    "args": ["check", "--fix"],
                },
                "ruff:format": {
                    "command": "ruff",
                    "args": ["format"],
                },
            },
        }

        try:
            # User config doesn't override - should use defaults
            build_cfg: mod_types.BuildConfig = {}
            resolved = mod_resolve.resolve_post_processing(build_cfg, None)

            formatter = resolved["categories"]["formatter"]
            # Should have custom labels from defaults
            assert formatter.get("priority") == ["ruff:check", "ruff:format"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            tools = formatter.get("tools")  # pyright: ignore[reportTypedDictNotRequiredAccess]
            assert tools is not None
            assert "ruff:check" in tools
            assert "ruff:format" in tools

            # Should execute successfully
            mod_verify.execute_post_processing(path, resolved)
            assert len(executed_commands) >= 1
        finally:
            mod_constants.DEFAULT_CATEGORIES["formatter"] = original_formatter
    finally:
        path.unlink(missing_ok=True)


def test_custom_label_fallback_from_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should fallback to DEFAULT_CATEGORIES when custom label in priority.

    Custom label should be found in DEFAULT_CATEGORIES when not in user tools.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            executed_commands.append(command)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            return f"/fake/path/{tool_name}"

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        # DEFAULT_CATEGORIES has custom label
        original_formatter = mod_constants.DEFAULT_CATEGORIES["formatter"].copy()
        mod_constants.DEFAULT_CATEGORIES["formatter"] = {
            "enabled": True,
            "priority": ["ruff:check", "ruff:format"],
            "tools": {
                "ruff:check": {
                    "command": "ruff",
                    "args": ["check", "--fix"],
                },
                "ruff:format": {
                    "command": "ruff",
                    "args": ["format"],
                },
            },
        }

        try:
            # User config has custom label in priority but doesn't define it in tools
            build_cfg: mod_types.BuildConfig = {
                "post_processing": {
                    "categories": {
                        "formatter": {
                            "priority": [
                                "ruff:check"
                            ],  # In priority but not in user tools
                            # No tools dict - should fallback to defaults
                        },
                    },
                },
            }
            resolved = mod_resolve.resolve_post_processing(build_cfg, None)

            formatter = resolved["categories"]["formatter"]
            assert formatter.get("priority") == ["ruff:check"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
            tools = formatter.get("tools")  # pyright: ignore[reportTypedDictNotRequiredAccess]
            assert tools is not None
            # Should have ruff:check from defaults via fallback
            assert "ruff:check" in tools

            # Should execute successfully
            mod_verify.execute_post_processing(path, resolved)
            assert len(executed_commands) >= 1
        finally:
            mod_constants.DEFAULT_CATEGORIES["formatter"] = original_formatter
    finally:
        path.unlink(missing_ok=True)


def test_custom_label_missing_from_tools_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should skip custom label gracefully when missing from tools and defaults.

    Custom label in priority but not defined anywhere should be skipped.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            executed_commands.append(command)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            return f"/fake/path/{tool_name}"

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        # User config has custom label in priority but not defined anywhere
        build_cfg: mod_types.BuildConfig = {
            "post_processing": {
                "categories": {
                    "formatter": {
                        "priority": ["ruff:missing", "ruff"],  # ruff:missing not defined
                        "tools": {
                            "ruff": {
                                "command": "ruff",
                                "args": ["format"],
                            },
                        },
                    },
                },
            },
        }
        resolved = mod_resolve.resolve_post_processing(build_cfg, None)

        # Should not raise, should skip ruff:missing and use ruff
        mod_verify.execute_post_processing(path, resolved)
        # Should have executed at least one command (ruff)
        assert len(executed_commands) >= 1
    finally:
        path.unlink(missing_ok=True)
