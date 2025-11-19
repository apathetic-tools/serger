# tests/50_core/test_extract_commit.py
"""Tests for extract_commit function."""

from pathlib import Path

import pytest

import serger.stitch as mod_stitch
from tests.utils import clear_ci_env


def test_extract_commit_not_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return 'unknown (local build)' outside CI context."""
    # Ensure we're not in CI - clear all CI-related environment variables
    clear_ci_env(monkeypatch)

    commit = mod_stitch.extract_commit(Path())
    assert commit == "unknown (local build)"
