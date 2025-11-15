# tests/5_core/test_execute_post_processing.py
"""Tests for execute_post_processing function."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import serger.config.config_resolve as mod_config_resolve
import serger.config.config_types as mod_config_types
import serger.constants as mod_constants
import serger.verify_script as mod_verify
from tests.utils import (
    make_post_category_config_resolved,
    make_post_processing_config_resolved,
    make_tool_config_resolved,
)


RUFF_AVAILABLE = shutil.which("ruff") is not None


@pytest.mark.skipif(not RUFF_AVAILABLE, reason="ruff not available")
def test_execute_post_processing_with_ruff() -> None:
    """Should execute post-processing when ruff is available."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        # Write code with formatting issues that ruff can fix
        f.write("x=1+2\n")  # Missing spaces
        f.flush()
        path = Path(f.name)

    try:
        # Create a minimal config that uses ruff for formatting
        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)
        # Verify ruff formatted the file (or at least ran)
        content = path.read_text()
        assert content  # Should have content
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_disabled() -> None:
    """Should skip post-processing when disabled."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        config = make_post_processing_config_resolved(
            enabled=False,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should not raise an error even if ruff is not available
        mod_verify.execute_post_processing(path, config)
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_multiple_instances_same_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should execute multiple instances of the same tool."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        # Track executed commands
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

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff-check", "ruff-imports"],
                    tools={
                        "ruff-check": make_tool_config_resolved(
                            args=["check", "--fix"], command="ruff"
                        ),
                        "ruff-imports": make_tool_config_resolved(
                            args=["check", "--select", "I", "--fix"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have executed both commands
        assert len(executed_commands) >= 1  # At least one should succeed
        # Check that both commands were attempted (or at least one succeeded)
        command_strings = [" ".join(cmd) for cmd in executed_commands]
        # One should contain "check --fix" and one should contain "--select I"
        assert any("check" in cmd and "--fix" in cmd for cmd in command_strings)
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_mixed_simple_and_custom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should handle mixed simple tool names and custom instances."""
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

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff", "ruff-custom"],
                    tools={
                        "ruff-custom": make_tool_config_resolved(
                            args=["check", "--select", "E", "--fix"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have executed at least one command
        assert len(executed_commands) >= 1
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_command_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should deduplicate identical commands even with different labels."""
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

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Both instances produce the same command
        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff-1", "ruff-2"],
                    tools={
                        "ruff-1": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                        "ruff-2": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should only execute once due to deduplication
        assert len(executed_commands) == 1
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_default_custom_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should execute default custom instances from DEFAULT_CATEGORIES."""
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

        monkeypatch.setattr(subprocess, "run", mock_run)

        # Patch DEFAULT_CATEGORIES to include custom instances
        # Modify in place to ensure config_resolve sees the changes
        original_formatter = mod_constants.DEFAULT_CATEGORIES["formatter"].copy()
        mod_constants.DEFAULT_CATEGORIES["formatter"] = {
            "enabled": True,
            "priority": ["ruff:firstcheck", "ruff:secondcheck"],
            "tools": {
                "ruff:firstcheck": {
                    "command": "ruff",
                    "args": ["check", "--fix"],
                    "path": None,
                    "options": [],
                },
                "ruff:secondcheck": {
                    "command": "ruff",
                    "args": ["check", "--select", "E", "--fix"],
                    "path": None,
                    "options": [],
                },
            },
        }

        try:
            # Create a minimal build config (no user overrides)
            build_cfg: mod_config_types.BuildConfig = {}
            resolved = mod_config_resolve.resolve_post_processing(build_cfg, None)

            # Execute with resolved config
            mod_verify.execute_post_processing(path, resolved)

            # Should have executed at least one command
            assert len(executed_commands) >= 1
            # Check that commands contain the expected args
            command_strings = [" ".join(cmd) for cmd in executed_commands]
            assert any("check" in cmd and "--fix" in cmd for cmd in command_strings)
        finally:
            # Restore original
            mod_constants.DEFAULT_CATEGORIES["formatter"] = original_formatter
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_priority_fallback_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should fall back to second tool when first tool fails."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []
        call_count = 0

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            # Make sure both tools are found
            return f"/fake/path/{tool_name}"

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            nonlocal call_count
            executed_commands.append(command)
            call_count += 1
            result = MagicMock()
            # First tool fails (returncode != 0), second succeeds
            result.returncode = 1 if call_count == 1 else 0
            result.stdout = ""
            result.stderr = "Error" if call_count == 1 else ""
            return result

        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )
        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["tool1", "tool2"],
                    tools={
                        "tool1": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                        "tool2": make_tool_config_resolved(
                            args=["format"], command="black"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have tried both tools (first fails, second succeeds)
        expected_command_count = 2
        assert len(executed_commands) == expected_command_count
        # Both tools should have been tried
        # First tool fails, so second tool should be tried and succeed
        assert "ruff" in str(executed_commands[0]) or "tool1" in str(
            executed_commands[0]
        )
        assert "black" in str(executed_commands[1]) or "tool2" in str(
            executed_commands[1]
        )
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_priority_fallback_on_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should fall back to second tool when first tool is unavailable."""
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
            # First tool unavailable, second available
            return None if tool_name == "tool1" else "/fake/path/tool2"

        monkeypatch.setattr(subprocess, "run", mock_run)
        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["tool1", "tool2"],
                    tools={
                        "tool1": make_tool_config_resolved(
                            args=["format"], command="nonexistent"
                        ),
                        "tool2": make_tool_config_resolved(
                            args=["format"], command="tool2"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have executed only the second tool
        assert len(executed_commands) == 1
        assert "tool2" in executed_commands[0][0]
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_all_tools_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should continue gracefully when all tools fail."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_commands: list[list[str]] = []

        def mock_find_tool_executable(
            tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            # Make sure both tools are found
            return f"/fake/path/{tool_name}"

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            executed_commands.append(command)
            result = MagicMock()
            result.returncode = 1  # All tools fail
            result.stdout = ""
            result.stderr = "Error"
            return result

        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )
        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["tool1", "tool2"],
                    tools={
                        "tool1": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                        "tool2": make_tool_config_resolved(
                            args=["format"], command="black"
                        ),
                    },
                ),
            },
        )
        # Should not raise, just log
        mod_verify.execute_post_processing(path, config)

        # Should have tried both tools
        expected_command_count = 2
        assert len(executed_commands) == expected_command_count
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_all_tools_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should continue gracefully when all tools are unavailable."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:

        def mock_find_tool_executable(
            _tool_name: str,
            **_kwargs: object,
        ) -> str | None:
            # All tools unavailable
            return None

        monkeypatch.setattr(
            mod_verify, "find_tool_executable", mock_find_tool_executable
        )

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["tool1", "tool2"],
                    tools={
                        "tool1": make_tool_config_resolved(
                            args=["format"], command="nonexistent1"
                        ),
                        "tool2": make_tool_config_resolved(
                            args=["format"], command="nonexistent2"
                        ),
                    },
                ),
            },
        )
        # Should not raise, just skip
        mod_verify.execute_post_processing(path, config)
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_categories_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should execute categories in category_order."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_categories: list[str] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            # Track which category is being processed
            cmd_str = " ".join(command)
            # Check for import_sorter first (more specific)
            if "--select" in cmd_str and "I" in cmd_str:
                executed_categories.append("import_sorter")
            elif "format" in cmd_str:
                executed_categories.append("formatter")
            elif "check" in cmd_str and "--fix" in cmd_str:
                executed_categories.append("static_checker")

            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["static_checker", "formatter", "import_sorter"],
            categories={
                "static_checker": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["check", "--fix"], command="ruff"
                        ),
                    },
                ),
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
                "import_sorter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["check", "--select", "I", "--fix"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have executed all three categories in order
        expected_category_count = 3
        assert len(executed_categories) == expected_category_count
        assert executed_categories[0] == "static_checker"
        assert executed_categories[1] == "formatter"
        assert executed_categories[2] == "import_sorter"
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_skips_disabled_category(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should skip category when disabled even if in category_order."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_categories: list[str] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            cmd_str = " ".join(command)
            if "format" in cmd_str:
                executed_categories.append("formatter")

            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["static_checker", "formatter"],
            categories={
                "static_checker": make_post_category_config_resolved(
                    enabled=False,  # Disabled
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["check", "--fix"], command="ruff"
                        ),
                    },
                ),
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should only execute formatter, not static_checker
        assert len(executed_categories) == 1
        assert executed_categories[0] == "formatter"
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_skips_category_not_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should skip category when not in category_order."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_categories: list[str] = []

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            cmd_str = " ".join(command)
            if "format" in cmd_str:
                executed_categories.append("formatter")
            elif "check" in cmd_str and "--fix" in cmd_str:
                executed_categories.append("static_checker")

            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],  # Only formatter in order
            categories={
                "static_checker": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["check", "--fix"], command="ruff"
                        ),
                    },
                ),
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should only execute formatter, not static_checker
        assert len(executed_categories) == 1
        assert executed_categories[0] == "formatter"
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_one_category_fails_others_continue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should continue with other categories when one category fails."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:
        executed_categories: list[str] = []
        call_count = 0

        def mock_run(
            command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            nonlocal call_count
            call_count += 1
            cmd_str = " ".join(command)
            if "check" in cmd_str and "--fix" in cmd_str and "--select" not in cmd_str:
                executed_categories.append("static_checker")
            elif "format" in cmd_str:
                executed_categories.append("formatter")

            result = MagicMock()
            # First category fails, second succeeds
            result.returncode = 1 if call_count == 1 else 0
            result.stdout = ""
            result.stderr = "Error" if call_count == 1 else ""
            return result

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["static_checker", "formatter"],
            categories={
                "static_checker": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["check", "--fix"], command="ruff"
                        ),
                    },
                ),
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        mod_verify.execute_post_processing(path, config)

        # Should have tried both categories
        expected_category_count = 2
        assert len(executed_categories) == expected_category_count
        assert executed_categories[0] == "static_checker"
        assert executed_categories[1] == "formatter"
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_subprocess_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should handle subprocess exceptions gracefully."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = Path(f.name)

    try:

        def mock_run(
            _command: list[str],
            **_kwargs: object,
        ) -> MagicMock:
            msg = "Command not found"
            raise OSError(msg)

        monkeypatch.setattr(subprocess, "run", mock_run)

        config = make_post_processing_config_resolved(
            enabled=True,
            category_order=["formatter"],
            categories={
                "formatter": make_post_category_config_resolved(
                    enabled=True,
                    priority=["ruff"],
                    tools={
                        "ruff": make_tool_config_resolved(
                            args=["format"], command="ruff"
                        ),
                    },
                ),
            },
        )
        # Should not raise, just log the error
        mod_verify.execute_post_processing(path, config)
    finally:
        path.unlink(missing_ok=True)


def test_execute_post_processing_custom_label_missing_from_tools_skipped(
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
        build_cfg: mod_config_types.BuildConfig = {
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
        resolved = mod_config_resolve.resolve_post_processing(build_cfg, None)

        # Should not raise, should skip ruff:missing and use ruff
        mod_verify.execute_post_processing(path, resolved)
        # Should have executed at least one command (ruff)
        assert len(executed_commands) >= 1
    finally:
        path.unlink(missing_ok=True)
