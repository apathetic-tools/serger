# tests/conftest.py
"""Shared test setup for project.

Each pytest run now targets a single runtime mode:
- Normal mode (default): uses src/serger
- Stitched mode: uses dist/serger.py when RUNTIME_MODE=stitched
- Zipapp mode: uses dist/serger.pyz when RUNTIME_MODE=zipapp

Switch mode with: RUNTIME_MODE=stitched pytest or RUNTIME_MODE=zipapp pytest
"""

import os
from collections.abc import Generator

import pytest
from apathetic_logging import makeSafeTrace
from apathetic_utils import runtime_swap

import serger.logs as mod_logs
import serger.meta as mod_meta
from tests.utils import DEFAULT_TEST_LOG_LEVEL, PROJ_ROOT
from tests.utils.log_fixtures import (
    direct_logger,
    module_logger,
)


# These fixtures are intentionally re-exported so pytest can discover them.
__all__ = [
    "direct_logger",
    "module_logger",
]

SAFE_TRACE = makeSafeTrace("⚡️")

# early jank hook - must run before importing apathetic_logging
# so we get the stitched version if in stitched/zipapp mode
runtime_swap(  # pyright: ignore[reportCallIssue]
    root=PROJ_ROOT,
    package_name=mod_meta.PROGRAM_PACKAGE,
    script_name=mod_meta.PROGRAM_SCRIPT,
    log_level="warning",
)

# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_logger_level() -> Generator[None, None, None]:
    """Reset logger level to DEFAULT_TEST_LOG_LEVEL (test)
        before each test for isolation.

    In stitched mode, the logger is a module-level singleton that persists
    between tests. This fixture ensures the logger level is reset to TEST
    (the default for tests) before and after each test, preventing test
    interference from previous tests.

    Note: When module_logger fixture is used, it temporarily replaces the
    logger with an isolated instance and fully restores the original afterward,
    so this fixture always resets the original logger (never the test logger).
    """
    # Get the app logger and reset to TEST level for maximum test verbosity
    logger = mod_logs.getAppLogger()
    logger.setLevel(DEFAULT_TEST_LOG_LEVEL)  # test
    yield
    # After test, reset again to ensure clean state for next test
    logger.setLevel(DEFAULT_TEST_LOG_LEVEL)  # test


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _mode() -> str:
    return os.getenv("RUNTIME_MODE", "package")


def _filter_debug_tests(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    # detect if the user is filtering for debug tests
    keywords = config.getoption("-k") or ""
    running_debug = "debug" in keywords.lower()

    if running_debug:
        return  # user explicitly requested them, don't skip

    for item in items:
        if "debug" in item.keywords:
            item.add_marker(
                pytest.mark.skip(reason="Skipped debug test (use -k debug to run)"),
            )


def _filter_runtime_mode_tests(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    mode = _mode()

    # file → number of tests
    included_map: dict[str, int] = {}
    root = str(config.rootpath)
    testpaths: list[str] = config.getini("testpaths") or []

    # Identify mode-specific files by a custom variable defined at module scope
    for item in list(items):
        mod = item.getparent(pytest.Module)
        if mod is None or not hasattr(mod, "obj"):
            continue

        runtime_marker = getattr(mod.obj, "__runtime_mode__", None)

        if runtime_marker and runtime_marker != mode:
            items.remove(item)
            continue

        if runtime_marker and runtime_marker == mode:
            file_path = str(item.fspath)
            # Make path relative to project root dir
            if file_path.startswith(root):
                file_path = os.path.relpath(file_path, root)
                for tp in testpaths:
                    if file_path.startswith(tp.rstrip("/") + os.sep):
                        file_path = file_path[len(tp.rstrip("/") + os.sep) :]
                        break

            included_map[file_path] = included_map.get(file_path, 0) + 1

    # Store results for later reporting
    config._included_map = included_map  # type: ignore[attr-defined] # noqa: SLF001
    config._runtime_mode = mode  # type: ignore[attr-defined] # noqa: SLF001


# ----------------------------------------------------------------------
# Hooks
# ----------------------------------------------------------------------


def pytest_report_header(config: pytest.Config) -> str:  # noqa: ARG001
    mode = _mode()
    return f"Runtime mode: {mode}"


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Filter and record runtime-specific tests for later reporting.

    also automatically skips debug tests unless asked for
    """
    _filter_debug_tests(config, items)
    _filter_runtime_mode_tests(config, items)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Print summary of included runtime-specific tests at the end."""
    included_map: dict[str, int] = getattr(config, "_included_map", {})
    mode = getattr(config, "_runtime_mode", "package")

    if not included_map:
        return

    total_tests = sum(included_map.values())
    print(
        f"🧪 Included {total_tests} {mode}-specific tests"
        f" across {len(included_map)} files:",
    )
    for path, count in sorted(included_map.items()):
        print(f"   • ({count}) {path}")
