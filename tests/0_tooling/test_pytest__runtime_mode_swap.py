# tests/0_independant/test_pytest__runtime_mode_swap.py
"""Verify runtime mode swap functionality in conftest.py.

This test verifies that our unique runtime_mode swap functionality works
correctly. Our conftest.py uses runtime_swap() to allow tests to run against
either the installed package (src/serger) or the standalone single-file script
(dist/serger.py) based on the RUNTIME_MODE environment variable.

Verifies:
  - When RUNTIME_MODE=singlefile: All modules resolve to dist/serger.py
  - When RUNTIME_MODE is unset (installed): All modules resolve to src/serger/
  - Python's import cache (sys.modules) points to the correct sources
  - All submodules load from the expected location

This ensures our dual-runtime testing infrastructure functions correctly.
"""

import importlib
import inspect
import os
import pkgutil
import sys
from pathlib import Path

import pytest

import serger as app_package
import serger.meta as mod_meta
import serger.utils.utils_system as mod_utils_system
from tests.utils import PROJ_ROOT, make_test_trace


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_TRACE = make_test_trace("🪞")

SRC_ROOT = PROJ_ROOT / "src"
DIST_ROOT = PROJ_ROOT / "dist"


def list_important_modules() -> list[str]:
    """Return all importable submodules under the package, if available."""
    important: list[str] = []
    if not hasattr(app_package, "__path__"):
        TEST_TRACE("pkgutil.walk_packages skipped — standalone runtime (no __path__)")
        important.append(app_package.__name__)
    else:
        for _, name, _ in pkgutil.walk_packages(
            app_package.__path__,
            app_package.__name__ + ".",
        ):
            important.append(name)

    return important


def dump_snapshot(*, include_full: bool = False) -> None:
    """Prints a summary of key modules and (optionally) a full sys.modules dump."""
    mode: str = os.getenv("RUNTIME_MODE", "installed")

    TEST_TRACE("========== SNAPSHOT ===========")
    TEST_TRACE(f"RUNTIME_MODE={mode}")

    important_modules = list_important_modules()

    # Summary: the modules we care about most
    TEST_TRACE("======= IMPORTANT MODULES =====")
    for name in important_modules:
        mod = sys.modules.get(name)
        if not mod:
            continue
        origin = getattr(mod, "__file__", None)
        TEST_TRACE(f"  {name:<25} {origin}")

    if include_full:
        # Full origin dump
        TEST_TRACE("======== OTHER MODULES ========")
        for name, mod in sorted(sys.modules.items()):
            if name in important_modules:
                continue
            origin = getattr(mod, "__file__", None)
            TEST_TRACE(f"  {name:<38} {origin}")

    TEST_TRACE("===============================")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pytest_runtime_cache_integrity() -> None:
    """Verify runtime mode swap correctly loads modules from expected locations.

    Ensures that modules imported at the top of test files resolve to the
    correct source based on RUNTIME_MODE:
    - singlefile mode: All modules must load from dist/serger.py
    - installed mode: All modules must load from src/serger/

    Also verifies that Python's import cache (sys.modules) doesn't have stale
    references pointing to the wrong runtime.
    """
    # --- setup ---
    mode = os.getenv("RUNTIME_MODE", "unknown")
    utils_file = str(inspect.getsourcefile(mod_utils_system))
    expected_script = DIST_ROOT / f"{mod_meta.PROGRAM_SCRIPT}.py"

    # --- execute ---
    TEST_TRACE(f"RUNTIME_MODE={mode}")
    TEST_TRACE(f"{mod_meta.PROGRAM_PACKAGE}.utils.utils_system  → {utils_file}")

    if os.getenv("TRACE"):
        dump_snapshot()
    runtime_mode = mod_utils_system.detect_runtime_mode()

    if mode == "singlefile":
        # --- verify singlefile ---
        # what does the module itself think?
        assert runtime_mode == "standalone"

        # path peeks
        assert utils_file.startswith(str(DIST_ROOT)), f"{utils_file} not in dist/"

        # exists
        assert expected_script.exists(), (
            f"Expected standalone script at {expected_script}"
        )

        # troubleshooting info
        TEST_TRACE(
            f"sys.modules['{mod_meta.PROGRAM_PACKAGE}']"
            f" = {sys.modules.get(mod_meta.PROGRAM_PACKAGE)}",
        )
        TEST_TRACE(
            f"sys.modules['{mod_meta.PROGRAM_PACKAGE}.utils.utils_system']"
            f" = {sys.modules.get(f'{mod_meta.PROGRAM_PACKAGE}.utils.utils_system')}",
        )

    else:
        # --- verify module ---
        # what does the module itself think?
        assert runtime_mode != "standalone"

        # path peeks
        assert utils_file.startswith(str(SRC_ROOT)), f"{utils_file} not in src/"

    # --- verify both ---
    important_modules = list_important_modules()
    for submodule in important_modules:
        mod = importlib.import_module(f"{submodule}")
        path = Path(inspect.getsourcefile(mod) or "")
        if mode == "singlefile":
            assert path.samefile(expected_script), f"{submodule} loaded from {path}"
        else:
            assert path.is_relative_to(SRC_ROOT), f"{submodule} not in src/: {path}"


@pytest.mark.debug
def test_debug_dump_all_module_origins() -> None:
    """Debug helper: Dump all loaded module origins for forensic analysis.

    Useful when debugging import leakage, stale sys.modules cache, or runtime
    mode swap issues. Always fails intentionally to force pytest to show TRACE
    output.

    Usage:
        TRACE=1 poetry run pytest -k debug -s
        RUNTIME_MODE=singlefile TRACE=1 poetry run pytest -k debug -s
    """
    # --- verify ---

    # dump everything we know
    dump_snapshot(include_full=True)

    # show total module count for quick glance
    count = sum(1 for name in sys.modules if name.startswith(mod_meta.PROGRAM_PACKAGE))
    TEST_TRACE(f"Loaded {count} {mod_meta.PROGRAM_PACKAGE} modules total")

    # force visible failure for debugging runs
    xmsg = (
        f"Intentional fail — {count} {mod_meta.PROGRAM_PACKAGE} modules listed above."
    )
    raise AssertionError(xmsg)
