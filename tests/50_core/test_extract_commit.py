# tests/50_core/test_extract_commit.py
"""Tests for extract_commit function."""

from pathlib import Path

import apathetic_utils as mod_utils
import pytest

import serger.stitch as mod_stitch


def test_extract_commit_not_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return 'unknown (local build)' outside CI context."""
    # Ensure we're not in CI - clear all CI-related environment variables
    for key in mod_utils.CI_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    commit = mod_stitch.extract_commit(Path())
    assert commit == "unknown (local build)"
