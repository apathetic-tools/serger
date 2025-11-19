# tests/50_core/test_extract_commit.py
"""Tests for extract_commit function."""

import os
from pathlib import Path

import serger.stitch as mod_stitch


def test_extract_commit_not_in_ci() -> None:
    """Should return 'unknown (local build)' outside CI context."""
    # Ensure we're not in CI - clear all CI-related environment variables
    for key in ["CI", "GITHUB_ACTIONS", "GIT_TAG", "GITHUB_REF"]:
        if key in os.environ:
            del os.environ[key]

    commit = mod_stitch.extract_commit(Path())
    assert commit == "unknown (local build)"
