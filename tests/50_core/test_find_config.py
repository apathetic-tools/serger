# tests/50_core/test_find_config.py

from argparse import Namespace
from pathlib import Path

import apathetic_logging as mod_alogs
import pytest

import serger.config.config_loader as mod_config_loader
import serger.meta as mod_meta


def test_find_config_raises_for_missing_file(tmp_path: Path) -> None:
    """Explicit --config path that doesn't exist should raise FileNotFoundError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path / "nope.json"))

    # --- execute and verify ---
    with pytest.raises(FileNotFoundError, match="not found"):
        mod_config_loader.find_config(args, tmp_path)


def test_find_config_returns_explicit_file(tmp_path: Path) -> None:
    """Should return the explicit file path when it exists."""
    # --- setup ---
    cfg = tmp_path / ".serger.json"
    cfg.write_text("{}")
    args = Namespace(config=str(cfg))

    # --- execute ---
    result = mod_config_loader.find_config(args, tmp_path)

    # --- verify ---
    assert result == cfg.resolve()


def test_find_config_logs_and_returns_none_when_missing(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Should log and return None when no default config file exists."""
    # --- setup ---
    args = Namespace(config=None)

    # --- execute ---
    result = mod_config_loader.find_config(args, tmp_path)

    # --- verify ---
    assert result is None
    # ensure an error was logged
    out = capsys.readouterr().err.lower()
    assert mod_alogs.TAG_STYLES["ERROR"][1].lower() in out
    assert "config" in out


def test_find_config_warns_for_multiple_candidates(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """If multiple config files exist, should warn and use the first."""
    # --- setup ---
    prefix = mod_meta.PROGRAM_CONFIG
    py = tmp_path / f".{prefix}.py"
    json = tmp_path / f".{prefix}json"
    jsonc = tmp_path / f".{prefix}.jsonc"
    for f in (py, json, jsonc):
        f.write_text("{}")

    args = Namespace(config=None)

    # --- execute ---
    result = mod_config_loader.find_config(args, tmp_path)

    # --- verify ---
    assert result == py
    # confirm that at least one warning was logged
    out = capsys.readouterr().err.lower()
    assert mod_alogs.TAG_STYLES["WARNING"][1].lower() in out
    assert "multiple config" in out


def test_find_config_raises_for_directory(tmp_path: Path) -> None:
    """Explicit --config path pointing to a directory should raise ValueError."""
    # --- setup ---
    args = Namespace(config=str(tmp_path))

    # --- execute and verify ---
    with pytest.raises(ValueError, match="directory"):
        mod_config_loader.find_config(args, tmp_path)


def test_find_config_respects_missing_level(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """missing_level argument should control log level on missing config."""
    # --- setup ---
    args = Namespace(config=None)

    # --- execute ---
    mod_config_loader.find_config(args, tmp_path, missing_level="warning")

    # --- verify ---
    out = capsys.readouterr().err.lower()
    assert mod_alogs.TAG_STYLES["WARNING"][1].lower() in out


def test_find_config_searches_parent_directories(tmp_path: Path) -> None:
    """Should find config files in parent directories, preferring closest."""
    # --- setup ---
    # Create directory structure: root/parent/child
    root = tmp_path / "root"
    parent = root / "parent"
    child = parent / "child"
    child.mkdir(parents=True)

    # Create config files at different levels with distinct values
    root_config = root / f".{mod_meta.PROGRAM_CONFIG}.json"
    root_config.write_text('{"out": "root_out"}')

    parent_config = parent / f".{mod_meta.PROGRAM_CONFIG}.json"
    parent_config.write_text('{"out": "parent_out"}')

    args = Namespace(config=None)

    # --- execute from child directory ---
    result = mod_config_loader.find_config(args, child)

    # --- verify ---
    # Should find parent config (closest), not root config
    assert result == parent_config.resolve()


def test_find_config_closest_wins_over_parent(tmp_path: Path) -> None:
    """Closest config file should win, not merge with parent configs."""
    # --- setup ---
    # Create directory structure: root/parent/child
    root = tmp_path / "root"
    parent = root / "parent"
    child = parent / "child"
    child.mkdir(parents=True)

    # Create config files with different values
    root_config = root / f".{mod_meta.PROGRAM_CONFIG}.json"
    root_config.write_text('{"out": "root_dist"}')

    parent_config = parent / f".{mod_meta.PROGRAM_CONFIG}.json"
    parent_config.write_text('{"out": "parent_dist"}')

    args = Namespace(config=None)

    # --- execute from child directory ---
    result = mod_config_loader.find_config(args, child)

    # --- verify ---
    # Should find parent config (closest), not root config
    # This proves it doesn't merge - if it merged, we'd need to check both
    assert result == parent_config.resolve()
    assert result != root_config.resolve()
