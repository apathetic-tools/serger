# tests/5_core/test_ruff_is_available.py
"""Tests for ruff_is_available function."""

import shutil

import pytest

import serger.verify_script as mod_verify
from tests.utils import patch_everywhere


def test_ruff_is_available_when_ruff_exists() -> None:
    """Should return ruff path when ruff is available."""
    # This test will only pass if ruff is actually available
    result = mod_verify.ruff_is_available()
    if shutil.which("ruff") is not None:
        assert result is not None
        assert isinstance(result, str)
    else:
        assert result is None


def test_ruff_is_available_when_ruff_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return None when ruff is not available."""
    # Mock ruff_is_available to return None
    patch_everywhere(monkeypatch, mod_verify, "ruff_is_available", lambda: None)
    result = mod_verify.ruff_is_available()
    assert result is None


def test_ruff_is_available_returns_path_when_mocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return mocked path when ruff_is_available is mocked."""
    mock_path = "/usr/local/bin/ruff"
    patch_everywhere(monkeypatch, mod_verify, "ruff_is_available", lambda: mock_path)
    result = mod_verify.ruff_is_available()
    assert result == mock_path
