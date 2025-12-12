# tests/utils/log_fixtures.py
"""Reusable fixtures for testing the Apathetic logger system."""

import logging
import uuid
from collections.abc import Generator

import pytest
from apathetic_logging import makeSafeTrace
from apathetic_utils import patch_everywhere

import serger.logs as mod_logs
import serger.meta as mod_meta


SAFE_TRACE = makeSafeTrace(icon="📏")


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
def module_logger(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[mod_logs.AppLogger, None, None]:
    """Replace getAppLogger() everywhere with a new isolated instance.

    Ensures all modules (build, config, etc.) calling getAppLogger()
    will use this test logger for the duration of the test.

    Automatically reverts after test completion, including restoring the
    logging registry to its original state.

    Default log level is set to "test" for maximum verbosity in test output.
    """
    # Use the same logger name as the original logger so that DualStreamHandler
    # can find it when it looks up the logger by name in emit()
    original_logger_name = mod_meta.PROGRAM_PACKAGE
    new_logger = mod_logs.AppLogger(original_logger_name, enable_color=False)
    new_logger.setLevel("test")
    # Use setPropagate() instead of direct assignment to set _propagate_explicit flag.
    # This prevents apathetic_logging.getLogger() from later resetting propagate=True
    # when it's called elsewhere (e.g., in load_jsonc), which would remove our handler.
    new_logger.setPropagate(False)

    # Replace the logger in the logging registry
    registry = logging.Logger.manager.loggerDict
    original_registry_logger = registry.get(original_logger_name)
    registry[original_logger_name] = new_logger

    # Patch logging.getLogger to prevent it from creating new logger instances
    original_get_logger = logging.getLogger

    def patched_get_logger(name: str | None = None) -> logging.Logger:
        if name == original_logger_name:
            return new_logger
        return original_get_logger(name)

    monkeypatch.setattr(logging, "getLogger", patched_get_logger)

    # Patch getAppLogger everywhere it's imported
    def mock_get_app_logger() -> mod_logs.AppLogger:
        return new_logger

    patch_everywhere(
        monkeypatch,
        mod_logs,
        "getAppLogger",
        mock_get_app_logger,
        package_prefix=mod_meta.PROGRAM_PACKAGE,
        stitch_hints={"/dist/", "stitched", f"{mod_meta.PROGRAM_SCRIPT}.py", ".pyz"},
    )

    # Also patch _APP_LOGGER directly in both source and stitched modules
    monkeypatch.setattr("serger.logs._APP_LOGGER", new_logger)

    # Patch in stitched module if it exists
    stitched_module = __import__("sys").modules.get("serger")
    if stitched_module and hasattr(stitched_module, "logs"):
        monkeypatch.setattr(stitched_module.logs, "_APP_LOGGER", new_logger)

    SAFE_TRACE(
        "module_logger fixture",
        f"id={id(new_logger)}",
        f"level={new_logger.levelName}",
        f"handlers={[type(h).__name__ for h in new_logger.handlers]}",
    )

    # Yield the logger for the test to use
    yield new_logger

    # --- Cleanup: Restore the logging registry to its original state ---
    if original_registry_logger is not None:
        registry[original_logger_name] = original_registry_logger
    else:
        logging.Logger.manager.loggerDict.pop(original_logger_name, None)
