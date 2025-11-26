# tests/utils/log_fixtures.py
"""Reusable fixtures for testing the Apathetic logger system."""

import uuid

import pytest

import serger.logs as mod_logs
from tests.utils import make_test_trace, patch_everywhere


TEST_TRACE = make_test_trace(icon="📏")


def _suffix() -> str:
    return "_" + uuid.uuid4().hex[:6]


@pytest.fixture
def direct_logger() -> mod_logs.AppLogger:
    """Create a brand-new AppLogger with no shared state.

    Only for testing the logger itself.

    This fixture does NOT affect getAppLogger() or global state —
    it's just a clean logger instance for isolated testing.

    Default log level is set to "test" for maximum verbosity in test output.
    """
    # Give each test's logger a unique name for debug clarity
    name = f"test_logger{_suffix()}"
    logger = mod_logs.AppLogger(name, enable_color=False)
    logger.setLevel("test")
    return logger


@pytest.fixture
def module_logger(monkeypatch: pytest.MonkeyPatch) -> mod_logs.AppLogger:
    """Replace getAppLogger() everywhere with a new isolated instance.

    Ensures all modules (build, config, etc.) calling getAppLogger()
    will use this test logger for the duration of the test.

    Automatically reverts after test completion.

    Default log level is set to "test" for maximum verbosity in test output.
    """
    new_logger = mod_logs.AppLogger(f"isolated_logger{_suffix()}", enable_color=False)
    new_logger.setLevel("test")
    patch_everywhere(monkeypatch, mod_logs, "getAppLogger", lambda: new_logger)
    TEST_TRACE(
        "module_logger fixture",
        f"id={id(new_logger)}",
        f"level={new_logger.levelName}",
        f"handlers={[type(h).__name__ for h in new_logger.handlers]}",
    )
    return new_logger
