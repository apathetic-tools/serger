# tests/utils/ci.py
"""CI environment detection utilities for tests.

This module duplicates is_ci logic to avoid relying on production code during tests.
Uses CI_ENV_VARS constant from apathetic_utils.ci for consistency.
"""

import os
from typing import TYPE_CHECKING

import apathetic_utils.ci as mod_ci


if TYPE_CHECKING:
    import pytest


__all__ = ["clear_ci_env", "is_ci"]


def is_ci() -> bool:
    """Check if running in a CI environment.

    Duplicates the logic from apathetic_utils.ci.is_ci() to avoid relying on
    production code during test runs. Uses CI_ENV_VARS constant for consistency.

    Returns:
        True if running in CI, False otherwise
    """
    return bool(any(os.getenv(var) for var in mod_ci.CI_ENV_VARS))


def clear_ci_env(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Clear all CI-related environment variables using monkeypatch.

    This ensures they are automatically restored after the test.
    Uses CI_ENV_VARS constant from apathetic_utils.ci for consistency.

    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    for key in mod_ci.CI_ENV_VARS:
        monkeypatch.delenv(key, raising=False)
