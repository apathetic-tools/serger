# src/serger/logs.py

import argparse
import logging
import os
from typing import cast

from apathetic_logging import (
    Logger,
    makeSafeTrace,
    registerDefaultLogLevel,
    registerLogger,
    registerLogLevelEnvVars,
)

from .constants import DEFAULT_ENV_LOG_LEVEL, DEFAULT_LOG_LEVEL
from .meta import PROGRAM_ENV, PROGRAM_PACKAGE


# --- Our application logger -----------------------------------------------------


class AppLogger(Logger):
    def determineLogLevel(  # noqa: N802
        self,
        *,
        args: argparse.Namespace | None = None,
        root_log_level: str | None = None,
        build_log_level: str | None = None,
    ) -> str:
        """Resolve log level from CLI → env → root config → default."""
        args_level = getattr(args, "log_level", None)
        if args_level is not None and args_level:
            # cast_hint would cause circular dependency
            return cast("str", args_level).upper()

        env_log_level = os.getenv(
            f"{PROGRAM_ENV}_{DEFAULT_ENV_LOG_LEVEL}"
        ) or os.getenv(DEFAULT_ENV_LOG_LEVEL)
        if env_log_level:
            return env_log_level.upper()

        if build_log_level:
            return build_log_level.upper()

        if root_log_level:
            return root_log_level.upper()

        return DEFAULT_LOG_LEVEL.upper()


# --- Logger initialization ---------------------------------------------------

# Force the logging module to use our subclass globally.
# This must happen *before* any loggers are created.
logging.setLoggerClass(AppLogger)

# Force registration of TRACE and SILENT levels
AppLogger.extendLoggingModule()

# Register log level environment variables and default
# This must happen before any loggers are created so they use the registered values
registerLogLevelEnvVars(
    [f"{PROGRAM_ENV}_{DEFAULT_ENV_LOG_LEVEL}", DEFAULT_ENV_LOG_LEVEL]
)
registerDefaultLogLevel(DEFAULT_LOG_LEVEL)

# Register the logger name so getLogger() can find it
registerLogger(PROGRAM_PACKAGE)

# Create the app logger instance via logging.getLogger()
# This ensures it's registered with the logging module and can be retrieved
# by other code that uses logging.getLogger()
_APP_LOGGER = cast("AppLogger", logging.getLogger(PROGRAM_PACKAGE))


# --- Convenience utils ---------------------------------------------------------


def getAppLogger() -> AppLogger:  # noqa: N802
    """Return the configured app logger.

    This is the app-specific logger getter that returns AppLogger type.
    Use this in application code instead of utils_logs.get_logger() for
    better type hints.
    """
    trace = makeSafeTrace()
    trace(
        "getAppLogger() called",
        f"id={id(_APP_LOGGER)}",
        f"name={_APP_LOGGER.name}",
        f"level={_APP_LOGGER.levelName}",
        f"handlers={[type(h).__name__ for h in _APP_LOGGER.handlers]}",
    )
    return _APP_LOGGER
