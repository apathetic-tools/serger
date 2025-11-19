# tests/50_core/test_extract_commit.py
"""Tests for extract_commit function."""

from pathlib import Path

import pytest

import serger.stitch as mod_stitch


def test_extract_commit_not_in_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should return 'unknown (local build)' outside CI context."""
    # Ensure we're not in CI - clear all CI-related environment variables
    # Using monkeypatch ensures they're automatically restored after the test
    for key in ["CI", "GITHUB_ACTIONS", "GIT_TAG", "GITHUB_REF"]:
        monkeypatch.delenv(key, raising=False)

    commit = mod_stitch.extract_commit(Path())
    assert commit == "unknown (local build)"
