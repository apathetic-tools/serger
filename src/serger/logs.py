# src/serger/logs.py

from typing import cast

from apathetic_logging import (
    INHERIT_LEVEL,
    Logger,
    getLogger,
    registerDefaultLogLevel,
    registerLogger,
    registerLogLevelEnvVars,
    setLoggerClass,
    setRootLevel,
)

from .constants import DEFAULT_ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL
from .meta import PROGRAM_ENV, PROGRAM_PACKAGE


class AppLogger(Logger):
    """App-specific logger class."""

    # for future use if needed, empty for now


# --- Logger initialization ---------------------------------------------------

# Force the logging module to use the Logger class globally.
# This must happen *before* any loggers are created.
setLoggerClass(AppLogger)

# Register log level environment variables and default
# This should happen BEFORE extendLoggingModule() so the root logger
# uses these settings when its level is determined.
registerLogLevelEnvVars(
    [f"{PROGRAM_ENV}_{DEFAULT_ENV_LOG_LEVEL}", DEFAULT_ENV_LOG_LEVEL]
)
registerDefaultLogLevel(DEFAULT_LOG_LEVEL)

# Register the logger name for auto-inference
registerLogger(PROGRAM_PACKAGE)

# Force registration of TRACE and SILENT levels
# This also replaces the root logger with AppLogger and sets up handlers
AppLogger.extendLoggingModule()

# Set root logger level to INFO to allow all messages through
# (Child loggers will do their own filtering based on their level)
setRootLevel("info")

# Create the app logger instance via getLogger()
# This is a child logger that inherits from the root logger.
# The root logger (created by extendLoggingModule) has the DualStreamHandler,
# and this child logger propagates to it via propagate=True.
_APP_LOGGER = cast("AppLogger", getLogger(PROGRAM_PACKAGE))

# Set the app logger level to INHERIT_LEVEL so it inherits from its parent
_APP_LOGGER.setLevel(INHERIT_LEVEL)


# --- Convenience utils ---------------------------------------------------------


def getAppLogger() -> AppLogger:  # noqa: N802
    """Return the configured app logger.

    This is the app-specific logger getter that returns Logger type.
    Use this in application code instead of utils_logs.get_logger() for
    better type hints.
    """
    return _APP_LOGGER
