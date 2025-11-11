# src/serger/verify_script.py
"""Script verification and post-processing utilities.

This module provides functions for verifying stitched Python scripts,
including compilation checks, ruff formatting, and execution validation.
"""

import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

from .logs import get_logger


def verify_compiles(file_path: Path) -> bool:
    """Verify that a Python file compiles without syntax errors.

    Args:
        file_path: Path to Python file to check

    Returns:
        True if file compiles successfully, False otherwise
    """
    logger = get_logger()
    try:
        py_compile.compile(str(file_path), doraise=True)
    except py_compile.PyCompileError as e:
        lineno = getattr(e, "lineno", "unknown")
        logger.debug("Compilation error at line %s: %s", lineno, e.msg)
        return False
    except FileNotFoundError:
        logger.debug("File not found: %s", file_path)
        return False
    else:
        logger.debug("File compiles successfully: %s", file_path)
        return True


def ruff_is_available() -> str | None:
    """Check if ruff is available in the system PATH.

    Returns:
        Path to ruff executable if available, None otherwise
    """
    return shutil.which("ruff")


def run_ruff_if_available(file_path: Path) -> bool:
    """Run ruff check --fix and ruff format on a file if ruff is available.

    Args:
        file_path: Path to Python file to format

    Returns:
        True if ruff was run successfully, False if ruff is not available
    """
    logger = get_logger()
    ruff_cmd = ruff_is_available()
    if ruff_cmd is None:
        logger.debug("ruff not found in PATH, skipping ruff processing")
        return False

    logger.debug("Running ruff on %s", file_path)

    # Run ruff check --fix
    try:
        result = subprocess.run(  # noqa: S603
            [ruff_cmd, "check", str(file_path), "--fix"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.debug(
                "ruff check --fix exited with code %d: %s",
                result.returncode,
                result.stderr,
            )
        else:
            logger.debug("ruff check --fix completed successfully")
    except Exception as e:  # noqa: BLE001
        logger.debug("Error running ruff check --fix: %s", e)
        return False

    # Run ruff format
    try:
        result = subprocess.run(  # noqa: S603
            [ruff_cmd, "format", str(file_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.debug(
                "ruff format exited with code %d: %s",
                result.returncode,
                result.stderr,
            )
        else:
            logger.debug("ruff format completed successfully")
    except Exception as e:  # noqa: BLE001
        logger.debug("Error running ruff format: %s", e)
        return False

    return True


def verify_executes(file_path: Path) -> bool:
    """Verify that a Python script can be executed (basic sanity check).

    First tries to run the script with --help (common CLI flag), then falls back
    to compilation check if that fails. This provides a lightweight execution
    verification without requiring full functionality testing.

    Args:
        file_path: Path to Python script to check

    Returns:
        True if script executes without immediate errors, False otherwise
    """
    logger = get_logger()

    # Check if file exists first
    if not file_path.exists():
        logger.debug("File does not exist: %s", file_path)
        return False

    # First, try to actually execute the script with --help
    # This verifies the script can run, not just compile
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(file_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        # Exit code 0 or 2 (help typically exits with 0 or 2)
        if result.returncode in (0, 2):
            logger.debug("Script executes successfully (--help): %s", file_path)
            return True
        # If --help fails, try --version as fallback
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(file_path), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode in (0, 2):
            logger.debug("Script executes successfully (--version): %s", file_path)
            return True
    except Exception as e:  # noqa: BLE001
        logger.debug("Error running script with --help/--version: %s", e)

    # Fallback: verify it compiles (lightweight check)
    try:
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            logger.debug("Script compiles successfully: %s", file_path)
            return True
        logger.debug(
            "Script execution check failed: %s", result.stderr or result.stdout
        )
    except Exception as e:  # noqa: BLE001
        logger.debug("Error during compilation check: %s", e)

    return False


def post_stitch_processing(
    out_path: Path,
    *,
    use_ruff: bool = True,
) -> None:
    """Post-process a stitched file with ruff, compilation checks, and verification.

    This function:
    1. Compiles the file before ruff processing
    2. Runs ruff check --fix and ruff format if ruff is available and use_ruff is True
    3. Compiles the file after ruff processing
    4. Reverts changes if compilation fails after ruff but succeeded before
    5. Runs a basic execution sanity check

    Args:
        out_path: Path to the stitched Python file
        use_ruff: Whether to attempt ruff processing (default: True)

    Raises:
        RuntimeError: If compilation fails and cannot be reverted
    """
    logger = get_logger()
    logger.debug("Starting post-stitch processing for %s", out_path)

    # Compile before ruff
    compiled_before = verify_compiles(out_path)
    if not compiled_before:
        logger.warning(
            "Stitched file does not compile before ruff processing. "
            "Skipping ruff and continuing."
        )
        # Still try to verify it executes
        verify_executes(out_path)
        return

    # Save original content in case we need to revert
    original_content = out_path.read_text(encoding="utf-8")

    # Run ruff if requested and available
    ruff_ran = False
    if use_ruff:
        ruff_ran = run_ruff_if_available(out_path)
        if ruff_ran:
            logger.debug("Ruff processing completed")
        else:
            logger.debug("Ruff processing skipped (not available or failed)")

    # Compile after ruff
    compiled_after = verify_compiles(out_path)
    if not compiled_after and compiled_before and ruff_ran:
        # Revert if it compiled before but not after ruff
        logger.warning(
            "File no longer compiles after ruff processing. Reverting changes."
        )
        out_path.write_text(original_content, encoding="utf-8")
        out_path.chmod(0o755)
        # Verify it compiles after revert
        if not verify_compiles(out_path):
            xmsg = (
                "File does not compile after reverting ruff changes. "
                "This indicates a problem with the original stitched file."
            )
            raise RuntimeError(xmsg)
    elif not compiled_after:
        # It didn't compile after, but either it didn't compile before
        # or ruff didn't run, so we can't revert
        xmsg = "Stitched file does not compile after post-processing"
        raise RuntimeError(xmsg)

    # Run execution sanity check
    verify_executes(out_path)

    logger.debug("Post-stitch processing completed successfully")
