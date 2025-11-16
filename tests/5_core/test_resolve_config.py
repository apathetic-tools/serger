# tests/5_core/test_resolve_config.py

"""Tests for serger.config_resolve."""

import argparse
from pathlib import Path

import pytest

import serger.config.config_resolve as mod_resolve
import serger.config.config_types as mod_types
import serger.constants as mod_constants
import serger.constants as mod_mutate_const  # for monkeypatch
import serger.logs as mod_logs
from tests.utils import make_build_input


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args(**kwargs: object) -> argparse.Namespace:
    """Build a fake argparse.Namespace with common CLI defaults."""
    arg_namespace = argparse.Namespace()
    # default fields expected by resolver
    arg_namespace.include = None
    arg_namespace.exclude = None
    arg_namespace.add_include = None
    arg_namespace.add_exclude = None
    arg_namespace.out = None
    arg_namespace.watch = None
    arg_namespace.log_level = None
    arg_namespace.respect_gitignore = None
    arg_namespace.use_color = None
    arg_namespace.config = None
    arg_namespace.dry_run = False
    for k, v in kwargs.items():
        setattr(arg_namespace, k, v)
    return arg_namespace


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_resolve_config_aggregates_builds_and_defaults(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Ensure resolve_config merges builds and assigns default values."""
    # --- setup ---
    root: mod_types.RootConfig = {
        "builds": [
            make_build_input(include=["src/**"], out="dist"),
            make_build_input(include=["lib/**"], out="libout"),
        ],
        "log_level": "warning",
    }
    args = _args()

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    builds = resolved["builds"]
    assert len(builds) == len(root["builds"])
    assert all("include" in b for b in builds)
    assert resolved["log_level"].lower() in ("warning", "info")  # env/cli may override
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["strict_config"] is False


def test_resolve_config_env_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Environment variables for watch interval and log level should override."""
    # --- setup ---
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()
    interval = 9.9

    # --- patch and execute ---
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_WATCH_INTERVAL, str(interval))
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_LOG_LEVEL, "debug")
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

        # --- validate ---
        assert resolved["watch_interval"] == pytest.approx(interval)  # pyright: ignore[reportUnknownMemberType]
        assert resolved["log_level"].lower() == "debug"


def test_resolve_config_invalid_env_watch_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Invalid watch interval env var should log warning and use default."""
    # --- setup ---
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}
    args = _args()

    # --- patch and execute ---
    monkeypatch.setenv(mod_mutate_const.DEFAULT_ENV_WATCH_INTERVAL, "badvalue")
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    assert isinstance(resolved["watch_interval"], float)
    assert resolved["watch_interval"] == mod_constants.DEFAULT_WATCH_INTERVAL


def test_resolve_config_propagates_cli_log_level(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """CLI --log-level should propagate into resolved root and runtime."""
    # --- setup ---
    args = _args(log_level="trace")
    root: mod_types.RootConfig = {"builds": [{"include": ["src/**"], "out": "dist"}]}

    # --- patch and execute ---
    with module_logger.use_level("info"):
        resolved = mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

        # --- validate ---
        assert resolved["log_level"].lower() == "trace"
        level = module_logger.level_name.lower()
        assert level.lower() == "trace"


def test_resolve_config_duplicate_output_paths_raises_error(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Multiple builds with the same output path should raise ValueError."""
    # --- setup ---
    root: mod_types.RootConfig = {
        "builds": [
            make_build_input(include=["src1/**"], out="dist/out.py"),
            make_build_input(include=["src2/**"], out="dist/out.py"),
            make_build_input(include=["src3/**"], out="dist/other.py"),
        ],
    }
    args = _args()

    # --- execute ---
    with (
        module_logger.use_level("info"),
        pytest.raises(ValueError, match="Several builds have the same output path"),
    ):
        mod_resolve.resolve_config(root, args, tmp_path, tmp_path)


def test_resolve_config_duplicate_output_paths_error_message(
    tmp_path: Path,
    module_logger: mod_logs.AppLogger,
) -> None:
    """Error message should list all duplicate output paths with build indices."""
    # --- setup ---
    root: mod_types.RootConfig = {
        "builds": [
            make_build_input(include=["src1/**"], out="dist/same.py"),
            make_build_input(include=["src2/**"], out="dist/other.py"),
            make_build_input(include=["src3/**"], out="dist/same.py"),
            make_build_input(include=["src4/**"], out="dist/other.py"),
        ],
    }
    args = _args()

    # --- execute ---
    with (
        module_logger.use_level("info"),
        pytest.raises(
            ValueError, match="Several builds have the same output path"
        ) as exc_info,
    ):
        mod_resolve.resolve_config(root, args, tmp_path, tmp_path)

    # --- validate ---
    error_msg = str(exc_info.value)
    assert "Several builds have the same output path" in error_msg
    assert "dist/other.py" in error_msg
    assert "dist/same.py" in error_msg
    assert "build #1" in error_msg or "build #2" in error_msg
    assert "build #3" in error_msg or "build #4" in error_msg
