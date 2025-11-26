# src/serger/selftest.py
"""Self-test functionality for verifying stitching works correctly."""

import platform
import py_compile
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .actions import get_metadata
from .build import run_build
from .constants import (
    DEFAULT_COMMENTS_MODE,
    DEFAULT_DOCSTRING_MODE,
    DEFAULT_EXTERNAL_IMPORTS,
    DEFAULT_INTERNAL_IMPORTS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MODULE_MODE,
    DEFAULT_STITCH_MODE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_WATCH_INTERVAL,
)
from .logs import getAppLogger
from .meta import PROGRAM_DISPLAY, PROGRAM_SCRIPT
from .utils import make_includeresolved, make_pathresolved
from .utils.utils_validation import validate_required_keys


if TYPE_CHECKING:
    from .config import RootConfigResolved

# Expected exit code from test script (42 * 2 = 84)
EXPECTED_EXIT_CODE = 84


def _create_test_package(pkg_dir: Path) -> None:
    """Create test package modules for selftest.

    Args:
        pkg_dir: Directory where test package modules should be created

    Raises:
        PermissionError: If unable to write files (environment issue)
        OSError: If directory operations fail (environment issue)
    """
    logger = getAppLogger()
    logger.trace("[SELFTEST] _create_test_package: pkg_dir=%s", pkg_dir)

    # base.py - simple module with a constant
    base_file = pkg_dir / "base.py"
    logger.trace("[SELFTEST] Creating base.py at %s", base_file)
    base_file.write_text(
        '"""Base module for selftest."""\nBASE_VALUE = 42\n',
        encoding="utf-8",
    )

    # utils.py - module that uses base
    utils_file = pkg_dir / "utils.py"
    logger.trace("[SELFTEST] Creating utils.py at %s", utils_file)
    utils_file.write_text(
        '"""Utils module for selftest."""\n'
        "from testpkg.base import BASE_VALUE\n\n"
        "def get_value() -> int:\n"
        "    return BASE_VALUE * 2\n",
        encoding="utf-8",
    )

    # main.py - entry point that uses utils
    main_file = pkg_dir / "main.py"
    logger.trace("[SELFTEST] Creating main.py at %s", main_file)
    main_file.write_text(
        '"""Main module for selftest."""\n'
        "from testpkg.utils import get_value\n\n"
        "def main(args: list[str] | None = None) -> int:\n"
        "    result = get_value()\n"
        "    print(f'Result: {result}')\n"
        "    return result\n",
        encoding="utf-8",
    )

    logger.debug(
        "[SELFTEST] Created test package modules: %s, %s, %s",
        base_file.name,
        utils_file.name,
        main_file.name,
    )


def _create_build_config(
    test_pkg_dir: Path, out_file: Path, tmp_dir: Path
) -> "RootConfigResolved":
    """Create build configuration for test package stitching.

    Args:
        test_pkg_dir: Directory containing test package modules
        out_file: Path where stitched output should be written
        tmp_dir: Temporary directory root for path resolution

    Returns:
        RootConfigResolved configuration for stitching

    Raises:
        RuntimeError: If config construction fails (program bug)
    """
    logger = getAppLogger()
    logger.trace(
        "[SELFTEST] _create_build_config: test_pkg_dir=%s, out_file=%s, tmp_dir=%s",
        test_pkg_dir,
        out_file,
        tmp_dir,
    )

    try:
        include_pattern = str(test_pkg_dir / "*.py")
        logger.trace("[SELFTEST] Resolving include pattern: %s", include_pattern)
        include_resolved = make_includeresolved(include_pattern, tmp_dir, "code")
        logger.trace("[SELFTEST] Resolved include: %s", include_resolved)

        logger.trace("[SELFTEST] Resolving output path: %s", out_file)
        out_resolved = make_pathresolved(out_file, tmp_dir, "code")
        logger.trace("[SELFTEST] Resolved output: %s", out_resolved)

        # Order entries should be file paths relative to tmp_dir (config_root)
        # Since include pattern is testpkg_dir/*.py, files are under testpkg_dir
        order_entries = [
            str((test_pkg_dir / "base.py").relative_to(tmp_dir)),
            str((test_pkg_dir / "utils.py").relative_to(tmp_dir)),
            str((test_pkg_dir / "main.py").relative_to(tmp_dir)),
        ]
        config = {
            "package": "testpkg",
            "order": order_entries,
            "include": [include_resolved],
            "exclude": [],
            "out": out_resolved,
            # Don't care about user's gitignore in selftest
            "respect_gitignore": False,
            "log_level": DEFAULT_LOG_LEVEL,
            "strict_config": DEFAULT_STRICT_CONFIG,
            "dry_run": False,
            "watch_interval": DEFAULT_WATCH_INTERVAL,
            "__meta__": {"cli_root": tmp_dir, "config_root": tmp_dir},
            # Required fields with defaults
            "internal_imports": DEFAULT_INTERNAL_IMPORTS[DEFAULT_STITCH_MODE],
            "external_imports": DEFAULT_EXTERNAL_IMPORTS[DEFAULT_STITCH_MODE],
            "stitch_mode": DEFAULT_STITCH_MODE,
            "module_mode": DEFAULT_MODULE_MODE,
            "comments_mode": DEFAULT_COMMENTS_MODE,
            "docstring_mode": DEFAULT_DOCSTRING_MODE,
            "post_processing": cast(
                "Any",
                {
                    "enabled": True,
                    "category_order": [],
                    "categories": {},
                },
            ),
        }
        logger.trace(
            "[SELFTEST] Build config created: package=%s, order=%s",
            "testpkg",
            config["order"],
        )
        return cast("RootConfigResolved", config)
    except Exception as e:
        xmsg = f"Config construction failed: {e}"
        logger.trace("[SELFTEST] Config construction error: %s", e, exc_info=True)
        raise RuntimeError(xmsg) from e


def _execute_selftest_build(build_cfg: "RootConfigResolved") -> None:
    """Execute stitch build in both dry-run and real modes.

    Args:
        build_cfg: Build configuration to execute

    Raises:
        RuntimeError: If build execution fails (program bug)
    """
    # run_build will validate required keys, but we need package for this function
    validate_required_keys(build_cfg, {"package"}, "build_cfg")
    logger = getAppLogger()
    logger.trace(
        "[SELFTEST] _execute_selftest_build: package=%s", build_cfg.get("package")
    )

    for dry_run in (True, False):
        build_cfg["dry_run"] = dry_run
        phase = "dry-run" if dry_run else "real"
        logger.debug("[SELFTEST] Running stitch build (%s mode)", phase)
        logger.trace(
            "[SELFTEST] Build config: package=%s, out=%s, include_count=%d",
            build_cfg.get("package"),
            build_cfg.get("out"),
            len(build_cfg.get("include", [])),
        )

        phase_start = time.time()
        try:
            run_build(build_cfg)
            phase_elapsed = time.time() - phase_start
            logger.trace(
                "[SELFTEST] Build phase '%s' completed in %.3fs",
                phase,
                phase_elapsed,
            )
        except Exception as e:
            phase_elapsed = time.time() - phase_start
            logger.trace(
                "[SELFTEST] Build phase '%s' failed after %.3fs: %s",
                phase,
                phase_elapsed,
                e,
                exc_info=True,
            )
            xmsg = f"Stitch build failed ({phase} mode): {e}"
            raise RuntimeError(xmsg) from e


def _verify_compiles(stitched_file: Path) -> None:
    """Verify that the stitched file compiles without syntax errors.

    Args:
        stitched_file: Path to stitched Python file

    Raises:
        RuntimeError: If compilation fails (program bug - stitched output invalid)
    """
    logger = getAppLogger()
    file_size = stitched_file.stat().st_size
    logger.trace(
        "[SELFTEST] _verify_compiles: file=%s, size=%d bytes",
        stitched_file,
        file_size,
    )

    try:
        py_compile.compile(str(stitched_file), doraise=True)
        logger.debug(
            "[SELFTEST] Stitched file compiles successfully: %s", stitched_file
        )
    except py_compile.PyCompileError as e:
        lineno = getattr(e, "lineno", "unknown")
        logger.trace("[SELFTEST] Compilation error: %s at line %s", e.msg, lineno)
        xmsg = f"Stitched file has syntax errors at line {lineno}: {e.msg}"
        raise RuntimeError(xmsg) from e


def _verify_executes(stitched_file: Path) -> None:
    """Verify that the stitched file executes and produces expected output.

    Args:
        stitched_file: Path to stitched Python file

    Raises:
        FileNotFoundError: If python3 is not found (environment issue)
        RuntimeError: If execution fails or produces unexpected output (program bug)
        AssertionError: If output validation fails (program bug)
    """
    logger = getAppLogger()
    logger.trace("[SELFTEST] _verify_executes: file=%s", stitched_file)

    python_cmd = ["python3", str(stitched_file)]
    logger.trace("[SELFTEST] Executing: %s", " ".join(python_cmd))

    try:
        exec_start = time.time()
        result = subprocess.run(  # noqa: S603
            python_cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        exec_elapsed = time.time() - exec_start
        logger.trace(
            "[SELFTEST] Execution completed in %.3fs: exit=%d, "
            "stdout_len=%d, stderr_len=%d",
            exec_elapsed,
            result.returncode,
            len(result.stdout),
            len(result.stderr),
        )

        # Check that expected output is present
        output = result.stdout
        expected_output = f"Result: {EXPECTED_EXIT_CODE}"
        if expected_output not in output:
            logger.trace(
                "[SELFTEST] Output mismatch: expected=%r, got_stdout=%r, got_stderr=%r",
                expected_output,
                output,
                result.stderr,
            )
            xmsg = (
                f"Unexpected output from stitched script. "
                f"Expected '{expected_output}' in stdout, but got: {output!r}. "
                f"stderr: {result.stderr!r}, exit code: {result.returncode}"
            )
            raise AssertionError(xmsg)

        # Exit code 84 is expected (the return value of main())
        # Any other non-zero exit code indicates an error
        if result.returncode not in {EXPECTED_EXIT_CODE, 0}:
            logger.trace(
                "[SELFTEST] Unexpected exit code: got=%d, expected=%s",
                result.returncode,
                {EXPECTED_EXIT_CODE, 0},
            )
            xmsg = (
                f"Stitched script execution failed with exit code "
                f"{result.returncode} (expected {EXPECTED_EXIT_CODE} or 0). "
                f"stderr: {result.stderr!r}"
            )
            raise RuntimeError(xmsg)

        logger.debug(
            "[SELFTEST] Stitched file executes correctly: exit=%d, output=%r",
            result.returncode,
            output.strip(),
        )

    except FileNotFoundError as e:
        # python3 not found - environment issue
        logger.trace("[SELFTEST] python3 not found: %s", e)
        xmsg = (
            f"python3 interpreter not found. Please ensure Python 3 is installed "
            f"and available in your PATH. Error: {e}"
        )
        raise FileNotFoundError(xmsg) from e

    except subprocess.TimeoutExpired as e:
        logger.trace("[SELFTEST] Execution timed out after 10s")
        xmsg = "Stitched script execution timed out after 10 seconds"
        raise RuntimeError(xmsg) from e


def _verify_content(stitched_file: Path) -> None:
    """Verify that key content markers are present in stitched file.

    Args:
        stitched_file: Path to stitched Python file

    Raises:
        AssertionError: If expected markers are not found (program bug)
    """
    logger = getAppLogger()
    logger.trace("[SELFTEST] _verify_content: file=%s", stitched_file)

    content = stitched_file.read_text(encoding="utf-8")
    content_size = len(content)
    line_count = content.count("\n") + 1
    logger.trace(
        "[SELFTEST] Content size: %d bytes, %d lines", content_size, line_count
    )

    expected_markers = [
        "# === testpkg.base ===",
        "# === testpkg.utils ===",
        "# === testpkg.main ===",
        "BASE_VALUE = 42",
        "def get_value()",
        "def main(",
    ]
    logger.trace("[SELFTEST] Checking %d content markers", len(expected_markers))

    for marker in expected_markers:
        if marker not in content:
            logger.trace("[SELFTEST] Missing marker: %r", marker)
            xmsg = (
                f"Expected marker '{marker}' not found in stitched output. "
                f"This indicates the stitching process did not include "
                f"expected content."
            )
            raise AssertionError(xmsg)

    logger.debug(
        "[SELFTEST] All content markers verified (%d markers)",
        len(expected_markers),
    )


def run_selftest() -> bool:  # noqa: PLR0915
    """Run a lightweight functional test of the stitching functionality.

    Creates a simple test package with multiple Python modules, stitches them
    together, and verifies the output compiles and executes correctly.

    Returns:
        True if selftest passes, False otherwise
    """
    logger = getAppLogger()

    # Always run selftest with at least DEBUG level, then revert
    with logger.useLevel("DEBUG", minimum=True):
        logger.info("🧪 Running self-test...")

        # Log environment info for GitHub issue reporting
        try:
            metadata = get_metadata()
            logger.debug(
                "[SELFTEST] Environment: %s %s, Python %s (%s) on %s",
                PROGRAM_DISPLAY,
                metadata,
                platform.python_version(),
                platform.python_implementation(),
                platform.system(),
            )
            logger.debug(
                "[SELFTEST] Python details: %s",
                sys.version.replace("\n", " "),
            )
        except Exception:  # noqa: BLE001
            # Metadata is optional for selftest, continue if it fails
            logger.trace("[SELFTEST] Failed to get metadata (non-fatal)")

        start_time = time.time()
        tmp_dir: Path | None = None
        stitched_file: Path | None = None

        try:
            logger.trace("[SELFTEST] Creating temporary directory")
            tmp_dir = Path(tempfile.mkdtemp(prefix=f"{PROGRAM_SCRIPT}-selftest-"))
            test_pkg_dir = tmp_dir / "testpkg"
            out_dir = tmp_dir / "out"
            test_pkg_dir.mkdir()
            out_dir.mkdir()

            logger.debug("[SELFTEST] Temp dir: %s", tmp_dir)
            logger.trace(
                "[SELFTEST] Test package dir: %s, Output dir: %s",
                test_pkg_dir,
                out_dir,
            )

            # --- Phase 1: Create test package modules ---
            phase_start = time.time()
            logger.debug("[SELFTEST] Phase 1: Creating test package modules")
            _create_test_package(test_pkg_dir)
            logger.debug(
                "[SELFTEST] Phase 1 completed in %.3fs",
                time.time() - phase_start,
            )

            # --- Phase 2: Prepare stitch config ---
            phase_start = time.time()
            logger.debug("[SELFTEST] Phase 2: Preparing stitch configuration")
            stitched_file = out_dir / "testpkg.py"
            build_cfg = _create_build_config(test_pkg_dir, stitched_file, tmp_dir)
            logger.debug(
                "[SELFTEST] Phase 2 completed in %.3fs, output will be: %s",
                time.time() - phase_start,
                stitched_file,
            )

            # --- Phase 3: Execute build (both dry and real) ---
            phase_start = time.time()
            logger.debug("[SELFTEST] Phase 3: Executing stitch build")
            _execute_selftest_build(build_cfg)
            logger.debug(
                "[SELFTEST] Phase 3 completed in %.3fs",
                time.time() - phase_start,
            )

            # --- Phase 4: Validate stitched output ---
            phase_start = time.time()
            logger.debug("[SELFTEST] Phase 4: Validating stitched output")
            if not stitched_file.exists():
                xmsg = (
                    f"Expected stitched output file missing: {stitched_file}. "
                    f"This indicates the build process did not create the output file."
                )
                raise RuntimeError(xmsg)  # noqa: TRY301

            file_size = stitched_file.stat().st_size
            logger.debug(
                "[SELFTEST] Stitched file exists: %s (%d bytes)",
                stitched_file,
                file_size,
            )
            logger.trace(
                "[SELFTEST] Stitched file path (absolute): %s",
                stitched_file.resolve(),
            )

            _verify_compiles(stitched_file)
            _verify_executes(stitched_file)
            _verify_content(stitched_file)
            logger.debug(
                "[SELFTEST] Phase 4 completed in %.3fs",
                time.time() - phase_start,
            )

            elapsed = time.time() - start_time
            logger.info(
                "✅ Self-test passed in %.2fs — %s is working correctly.",
                elapsed,
                PROGRAM_DISPLAY,
            )
            logger.trace("[SELFTEST] Total test duration: %.6fs", elapsed)

        except (PermissionError, OSError, FileNotFoundError) as e:
            # Environment issues: file system permissions, temp dir creation,
            # python3 not found, missing dependencies, etc.
            if isinstance(e, FileNotFoundError) and "python3" in str(e).lower():
                msg_template = (
                    "Self-test failed due to missing dependency or tool "
                    "(this is likely a problem with your environment, not with %s): %s"
                )
            else:
                msg_template = (
                    "Self-test failed due to environment issue (this is likely "
                    "a problem with your system setup, not with %s): %s"
                )
            logger.errorIfNotDebug(msg_template, PROGRAM_DISPLAY, e)
            logger.debug(
                "[SELFTEST] Environment issue details: error=%s, tmp_dir=%s",
                e,
                tmp_dir,
            )
            return False

        except RuntimeError as e:
            # Program bugs: build failures, compilation errors, execution errors
            stitched_file_info = str(stitched_file) if stitched_file else "N/A"
            logger.errorIfNotDebug(
                "Self-test failed (this appears to be a bug in %s): %s",
                PROGRAM_DISPLAY,
                e,
            )
            logger.debug(
                "[SELFTEST] Program bug details: error=%s, tmp_dir=%s, "
                "stitched_file=%s",
                e,
                tmp_dir,
                stitched_file_info,
            )
            return False

        except AssertionError as e:
            # Program bugs: validation failures, content mismatches
            stitched_file_info = str(stitched_file) if stitched_file else "N/A"
            logger.errorIfNotDebug(
                "Self-test failed validation (this appears to be a bug in %s): %s",
                PROGRAM_DISPLAY,
                e,
            )
            logger.debug(
                "[SELFTEST] Validation failure: error=%s, tmp_dir=%s, stitched_file=%s",
                e,
                tmp_dir,
                stitched_file_info,
            )
            return False

        except Exception as e:
            # Unexpected program bugs: should never happen
            logger.exception(
                "Unexpected self-test failure (this is a bug in %s). "
                "Please report this traceback in a GitHub issue:",
                PROGRAM_DISPLAY,
            )
            logger.debug(
                "[SELFTEST] Unexpected error: type=%s, error=%s, tmp_dir=%s",
                type(e).__name__,
                e,
                tmp_dir,
            )
            return False

        else:
            return True

        finally:
            if tmp_dir and tmp_dir.exists():
                logger.trace("[SELFTEST] Cleaning up temp dir: %s", tmp_dir)
                shutil.rmtree(tmp_dir, ignore_errors=True)
