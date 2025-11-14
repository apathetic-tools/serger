# src/serger/utils/utils_logs.py
"""Shared Apathetic CLI logger implementation."""

from __future__ import annotations

import argparse
import builtins
import importlib
import inspect
import logging
import os
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from typing import Any, TextIO, cast


# --- Constants ---------------------------------------------------------------

DEFAULT_APATHETIC_LOG_LEVEL: str = "info"
DEFAULT_APATHETIC_LOG_LEVEL_ENV_VARS: list[str] = ["LOG_LEVEL"]

# Flag for quick runtime enable/disable
TEST_TRACE_ENABLED = os.getenv("TEST_TRACE", "").lower() in {"1", "true", "yes"}

# Lazy, safe import — avoids patched time modules
#   in environments like pytest or eventlet
_real_time = importlib.import_module("time")

# ANSI Colors
RESET = "\033[0m"
CYAN = "\033[36m"
YELLOW = "\033[93m"  # or \033[33m
RED = "\033[91m"  # or \033[31m # or background \033[41m
GREEN = "\033[92m"  # or \033[32m
GRAY = "\033[90m"

# Logger levels
TEST_LEVEL = logging.DEBUG - 10  # most verbose, bypasses capture
TRACE_LEVEL = logging.DEBUG - 5
# DEBUG      - builtin # verbose
# INFO       - builtin
# WARNING    - builtin
# ERROR      - builtin
# CRITICAL   - builtin # quiet mode
SILENT_LEVEL = logging.CRITICAL + 1  # one above the highest builtin level

LEVEL_ORDER = [
    "test",  # most verbose, bypasses capture for debugging tests
    "trace",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    "silent",  # disables all logging
]

TAG_STYLES = {
    "TEST": (GRAY, "[TEST]"),
    "TRACE": (GRAY, "[TRACE]"),
    "DEBUG": (CYAN, "[DEBUG]"),
    "WARNING": ("", "⚠️ "),
    "ERROR": ("", "❌ "),
    "CRITICAL": ("", "💥 "),
}

# sanity check
assert set(TAG_STYLES.keys()) <= {lvl.upper() for lvl in LEVEL_ORDER}, (  # noqa: S101
    "TAG_STYLES contains unknown levels"
)

# --- globals ---------------------------------------------------------------

# Registry for configurable log level settings
_registered_log_level_env_vars: list[str] | None = None
_registered_default_log_level: str | None = None


# --- Logging that bypasses streams -------------------------------------------------


def safe_log(msg: str) -> None:
    """Emergency logger that never fails."""
    stream = cast("TextIO", sys.__stderr__)
    try:
        print(msg, file=stream)
    except Exception:  # noqa: BLE001
        # As final guardrail — never crash during crash reporting
        with suppress(Exception):
            stream.write(f"[INTERNAL] {msg}\n")


# --- Logging for debugging tests -------------------------------------------------


def make_test_trace(icon: str = "🧵") -> Callable[..., Any]:
    def local_trace(label: str, *args: Any) -> Any:
        return TEST_TRACE(label, *args, icon=icon)

    return local_trace


def TEST_TRACE(label: str, *args: Any, icon: str = "🧵") -> None:  # noqa: N802
    """Emit a synchronized, flush-safe diagnostic line.

    Args:
        label: Short identifier or context string.
        *args: Optional values to append.
        icon: Emoji prefix/suffix for easier visual scanning.

    """
    if not TEST_TRACE_ENABLED:
        return

    ts = _real_time.monotonic()
    # builtins.print more reliable than sys.stdout.write + sys.stdout.flush
    builtins.print(
        f"{icon} [TEST TRACE {ts:.6f}] {label}",
        *args,
        file=sys.__stderr__,
        flush=True,
    )


# --- Apathetic logger -----------------------------------------------------


class ApatheticCLILogger(logging.Logger):
    """Logger for all Apathetic CLI tools."""

    enable_color: bool = False

    _logging_module_extended: bool = False

    # if stdout or stderr are redirected, we need to repoint
    _last_stream_ids: tuple[TextIO, TextIO] | None = None

    def __init__(
        self,
        name: str,
        level: int = logging.NOTSET,
        *,
        enable_color: bool | None = None,
    ) -> None:
        # it is too late to call extend_logging_module

        # now let's init our logger
        super().__init__(name, level)

        # default level resolution
        if self.level == logging.NOTSET:
            self.setLevel(self.determine_log_level())

        # detect color support once per instance
        self.enable_color = (
            enable_color
            if enable_color is not None
            else type(self).determine_color_enabled()
        )

        self.propagate = False  # avoid duplicate root logs

        # handler attachment will happen in _log() with ensure_handlers()

    def ensure_handlers(self) -> None:
        if self._last_stream_ids is None or not self.handlers:
            rebuild = True
        else:
            last_stdout, last_stderr = self._last_stream_ids
            rebuild = (last_stdout is not sys.stdout) or (last_stderr is not sys.stderr)

        if rebuild:
            self.handlers.clear()
            h = DualStreamHandler()
            h.setFormatter(TagFormatter("%(message)s"))
            h.enable_color = self.enable_color
            self.addHandler(h)
            self._last_stream_ids = (sys.stdout, sys.stderr)
            TEST_TRACE("ensure_handlers()", f"rebuilt_handlers={self.handlers}")

    def _log(  # type: ignore[override]
        self, level: int, msg: str, args: tuple[Any, ...], **kwargs: Any
    ) -> None:
        TEST_TRACE(
            "_log",
            f"logger={self.name}",
            f"id={id(self)}",
            f"level={self.level_name}",
            f"msg={msg!r}",
        )
        self.ensure_handlers()
        super()._log(level, msg, args, **kwargs)

    def setLevel(self, level: int | str) -> None:  # noqa: N802
        """Case insensitive version"""
        if isinstance(level, str):
            level = level.upper()
        super().setLevel(level)

    @classmethod
    def determine_color_enabled(cls) -> bool:
        """Return True if colored output should be enabled."""
        # Respect explicit overrides
        if "NO_COLOR" in os.environ:
            return False
        if os.getenv("FORCE_COLOR", "").lower() in {"1", "true", "yes"}:
            return True

        # Auto-detect: use color if output is a TTY
        return sys.stdout.isatty()

    @classmethod
    def extend_logging_module(cls) -> bool:
        """The return value tells you if we ran or not.
        If it is False and you're calling it via super(),
        you can likely skip your code too."""
        # ensure module-level logging setup runs only once
        if cls._logging_module_extended:
            return False
        cls._logging_module_extended = True

        logging.setLoggerClass(cls)

        logging.addLevelName(TEST_LEVEL, "TEST")
        logging.addLevelName(TRACE_LEVEL, "TRACE")
        logging.addLevelName(SILENT_LEVEL, "SILENT")

        logging.TEST = TEST_LEVEL  # type: ignore[attr-defined]
        logging.TRACE = TRACE_LEVEL  # type: ignore[attr-defined]
        logging.SILENT = SILENT_LEVEL  # type: ignore[attr-defined]

        return True

    def determine_log_level(
        self,
        *,
        args: argparse.Namespace | None = None,
        root_log_level: str | None = None,
    ) -> str:
        """Resolve log level from CLI → env → root config → default."""
        args_level = getattr(args, "log_level", None)
        if args_level is not None:
            # cast_hint would cause circular dependency
            return cast("str", args_level).upper()

        # Check registered environment variables, or fall back to "LOG_LEVEL"
        env_vars_to_check = (
            _registered_log_level_env_vars or DEFAULT_APATHETIC_LOG_LEVEL_ENV_VARS
        )
        for env_var in env_vars_to_check:
            env_log_level = os.getenv(env_var)
            if env_log_level:
                return env_log_level.upper()

        if root_log_level:
            return root_log_level.upper()

        # Use registered default, or fall back to module default
        default_level = _registered_default_log_level or DEFAULT_APATHETIC_LOG_LEVEL
        return default_level.upper()

    @property
    def level_name(self) -> str:
        """Return the current effective level name
        (see also: logging.getLevelName)."""
        return logging.getLevelName(self.getEffectiveLevel())

    def error_if_not_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception with the real traceback starting from the caller.
        Only shows full traceback if debug/trace is enabled."""
        exc_info = kwargs.pop("exc_info", True)
        stacklevel = kwargs.pop("stacklevel", 2)  # skip helper frame
        if self.isEnabledFor(logging.DEBUG):
            self.exception(msg, *args, exc_info=exc_info, stacklevel=stacklevel)
        else:
            self.error(msg, *args)

    def critical_if_not_debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Logs an exception with the real traceback starting from the caller.
        Only shows full traceback if debug/trace is enabled."""
        exc_info = kwargs.pop("exc_info", True)
        stacklevel = kwargs.pop("stacklevel", 2)  # skip helper frame
        if self.isEnabledFor(logging.DEBUG):
            self.exception(msg, *args, exc_info=exc_info, stacklevel=stacklevel)
        else:
            self.critical(msg, *args)

    def colorize(
        self, text: str, color: str, *, enable_color: bool | None = None
    ) -> str:
        if enable_color is None:
            enable_color = self.enable_color
        return f"{color}{text}{RESET}" if enable_color else text

    def trace(self, msg: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE_LEVEL):
            self._log(TRACE_LEVEL, msg, args, **kwargs)

    def test(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a test-level message (most verbose, bypasses capture)."""
        if self.isEnabledFor(TEST_LEVEL):
            self._log(TEST_LEVEL, msg, args, **kwargs)

    def resolve_level_name(self, level_name: str) -> int | None:
        """logging.getLevelNamesMapping() is only introduced in 3.11"""
        return getattr(logging, level_name.upper(), None)

    def log_dynamic(
        self, level: str | int, msg: str, *args: Any, **kwargs: Any
    ) -> None:
        # Resolve level
        if isinstance(level, str):
            level_no = self.resolve_level_name(level)
            if not isinstance(level_no, int):
                self.error("Unknown log level: %r", level)
                return
        elif isinstance(level, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            level_no = level
        else:
            self.error("Invalid log level type: %r", type(level))
            return

        self._log(level_no, msg, args, **kwargs)

    @contextmanager
    def use_level(
        self, level: str | int, *, minimum: bool = False
    ) -> Generator[None, None, None]:
        """Use a context to temporarily log with a different log-level.

        Args:
            level: Log level to use (string name or numeric value)
            minimum: If True, only set the level if it's more verbose (lower
                numeric value) than the current level. This prevents downgrading
                from a more verbose level (e.g., TRACE) to a less verbose one
                (e.g., DEBUG). Defaults to False.

        Yields:
            None: Context manager yields control to the with block
        """
        prev_level = self.level

        # Resolve level
        if isinstance(level, str):
            level_no = self.resolve_level_name(level)
            if not isinstance(level_no, int):
                self.error("Unknown log level: %r", level)
                # Yield control anyway so the 'with' block doesn't explode
                yield
                return
        elif isinstance(level, int):  # pyright: ignore[reportUnnecessaryIsInstance]
            level_no = level
        else:
            self.error("Invalid log level type: %r", type(level))
            yield
            return

        # Apply new level (only if more verbose when minimum=True)
        if minimum:
            # Only set if requested level is more verbose (lower number) than current
            if level_no < prev_level:
                self.setLevel(level_no)
            # Otherwise keep current level (don't downgrade)
        else:
            self.setLevel(level_no)

        try:
            yield
        finally:
            self.setLevel(prev_level)


# --- Tag formatter ---------------------------------------------------------


class TagFormatter(logging.Formatter):
    def format(self: TagFormatter, record: logging.LogRecord) -> str:
        tag_color, tag_text = TAG_STYLES.get(record.levelname, ("", ""))
        msg = super().format(record)
        if tag_text:
            if getattr(record, "enable_color", False) and tag_color:
                prefix = f"{tag_color}{tag_text}{RESET}"
            else:
                prefix = tag_text
            return f"{prefix} {msg}"
        return msg


# --- DualStreamHandler ---------------------------------------------------------


class DualStreamHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Send info/debug/trace to stdout, everything else to stderr.

    When logger level is TEST, TRACE/DEBUG/TEST messages bypass capture
    by writing to sys.__stdout__/sys.__stderr__ instead of sys.stdout/sys.stderr.
    This allows debugging tests without breaking output assertions.
    """

    enable_color: bool = False

    def __init__(self) -> None:
        # default to stdout, overridden per record in emit()
        super().__init__()  # pyright: ignore[reportUnknownMemberType]

    def emit(self, record: logging.LogRecord) -> None:
        level = record.levelno

        # Check if logger is in TEST mode (bypass capture for verbose levels)
        logger_name = record.name
        logger_instance = logging.getLogger(logger_name)
        is_test_mode = (
            isinstance(logger_instance, ApatheticCLILogger)
            and logger_instance.getEffectiveLevel() == TEST_LEVEL
        )

        # Determine target stream
        if level >= logging.WARNING:
            # Warnings and errors always go to stderr (normal behavior)
            # This ensures they still break tests as expected
            # Even in TEST mode, warnings/errors use normal stderr
            self.stream = sys.stderr
        # TRACE, DEBUG, TEST, INFO go to stdout
        # If in TEST mode, bypass capture for verbose levels (TEST/TRACE/DEBUG)
        elif is_test_mode and level < logging.INFO:
            # Use bypass stream for TEST/TRACE/DEBUG in test mode
            self.stream = sys.__stdout__
        else:
            # Normal behavior: use regular stdout
            self.stream = sys.stdout

        # used by TagFormatter
        record.enable_color = getattr(self, "enable_color", False)

        super().emit(record)


# --- Logger registry ---------------------------------------------------------


# Registry to store the registered logger name
# The logging module itself acts as the registry via logging.getLogger()
_registered_logger_name: str | None = None


def _extract_top_level_package(package_name: str | None) -> str | None:
    """Extract the top-level package name from a full package path.

    Args:
        package_name: Full package name (e.g., "serger.logs")

    Returns:
        Top-level package name (e.g., "serger") or None if package_name is None
    """
    if package_name is None:
        return None
    if "." in package_name:
        return package_name.split(".", 1)[0]
    return package_name


def register_log_level_env_vars(env_vars: list[str]) -> None:
    """Register environment variable names to check for log level.

    The environment variables will be checked in order, and the first
    non-empty value found will be used.

    Args:
        env_vars: List of environment variable names to check
            (e.g., ["SERGER_LOG_LEVEL", "LOG_LEVEL"])

    Example:
        >>> from apathetic_logs import register_log_level_env_vars
        >>> register_log_level_env_vars(["MYAPP_LOG_LEVEL", "LOG_LEVEL"])
    """
    global _registered_log_level_env_vars  # noqa: PLW0603
    _registered_log_level_env_vars = env_vars
    TEST_TRACE(
        "register_log_level_env_vars() called",
        f"env_vars={env_vars}",
    )


def register_default_log_level(default_level: str) -> None:
    """Register the default log level to use when no other source is found.

    Args:
        default_level: Default log level name (e.g., "info", "warning")

    Example:
        >>> from apathetic_logs import register_default_log_level
        >>> register_default_log_level("warning")
    """
    global _registered_default_log_level  # noqa: PLW0603
    _registered_default_log_level = default_level
    TEST_TRACE(
        "register_default_log_level() called",
        f"default_level={default_level}",
    )


def register_logger_name(logger_name: str | None = None) -> None:
    """Register a logger name for use by get_logger().

    This allows applications to specify which logger name to use.
    The actual logger instance is stored by Python's logging module
    via logging.getLogger(), so we only need to store the name.

    If logger_name is not provided, the top-level package is automatically
    extracted from this module's __package__ attribute. For example, if
    this module is in "serger.logs", it will default to "serger".

    Args:
        logger_name: The name of the logger to retrieve (e.g., "serger").
            If None, extracts the top-level package from __package__.

    Example:
        >>> # Explicit registration
        >>> from serger.meta import PROGRAM_PACKAGE
        >>> from serger.logs import register_logger_name
        >>> register_logger_name(PROGRAM_PACKAGE)

        >>> # Auto-infer from __package__
        >>> register_logger_name()  # Uses top-level package from __package__
    """
    global _registered_logger_name  # noqa: PLW0603

    auto_inferred = False
    if logger_name is None:
        # Extract top-level package from this module's __package__
        package = globals().get("__package__")
        if package:
            logger_name = _extract_top_level_package(package)
            auto_inferred = True
        if logger_name is None:
            _msg = (
                "Cannot auto-infer logger name: __package__ is not set. "
                "Please call register_logger_name() with an explicit logger name."
            )
            raise RuntimeError(_msg)

    _registered_logger_name = logger_name
    TEST_TRACE(
        "register_logger_name() called",
        f"name={logger_name}",
        f"auto_inferred={auto_inferred}",
    )


def get_logger() -> ApatheticCLILogger:
    """Return the registered logger instance.

    Uses Python's built-in logging registry (logging.getLogger()) to retrieve
    the logger. If no logger name has been registered, attempts to auto-infer
    the logger name from the calling module's top-level package.

    Returns:
        The logger instance from logging.getLogger() (as ApatheticCLILogger type)

    Raises:
        RuntimeError: If called before a logger name has been registered and
            auto-inference fails.

    Note:
        This function is used internally by utils_logs.py. Applications
        should use their app-specific getter (e.g., get_app_logger()) for
        better type hints.
    """
    global _registered_logger_name  # noqa: PLW0603

    if _registered_logger_name is None:
        # Try to auto-infer from the calling module's package
        frame = inspect.currentframe()
        if frame is not None:
            try:
                # Get the calling frame (skip get_logger itself)
                caller_frame = frame.f_back
                if caller_frame is not None:
                    caller_module = caller_frame.f_globals.get("__package__")
                    if caller_module:
                        inferred_name = _extract_top_level_package(caller_module)
                        if inferred_name:
                            _registered_logger_name = inferred_name
                            TEST_TRACE(
                                "get_logger() auto-inferred logger name",
                                f"name={inferred_name}",
                                f"from_module={caller_module}",
                            )
            finally:
                del frame

    if _registered_logger_name is None:
        _msg = (
            "Logger name not registered and could not be auto-inferred. "
            "Call register_logger_name() or ensure your app's logs module is imported."
        )
        raise RuntimeError(_msg)

    logger = logging.getLogger(_registered_logger_name)
    # Cast to ApatheticCLILogger - at runtime this will be AppLogger if registered
    typed_logger = cast("ApatheticCLILogger", logger)
    TEST_TRACE(
        "get_logger() called",
        f"name={typed_logger.name}",
        f"id={id(typed_logger)}",
        f"level={typed_logger.level_name}",
        f"handlers={[type(h).__name__ for h in typed_logger.handlers]}",
    )
    return typed_logger
