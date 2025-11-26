# src/serger/verify_script.py
"""Script verification and post-processing utilities.

This module provides functions for verifying stitched Python scripts,
including compilation checks, ruff formatting, and execution validation.
"""

import py_compile
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import PostProcessingConfigResolved, ToolConfigResolved
from .logs import getAppLogger
from .utils.utils_validation import validate_required_keys


def verify_compiles_string(source: str, filename: str = "<string>") -> None:
    """Verify that Python source code compiles without syntax errors.

    Args:
        source: Python source code as string
        filename: Filename to use in error messages (for debugging)

    Raises:
        SyntaxError: If compilation fails with syntax error details
    """
    compile(source, filename, "exec")


def verify_compiles(file_path: Path) -> bool:
    """Verify that a Python file compiles without syntax errors.

    Args:
        file_path: Path to Python file to check

    Returns:
        True if file compiles successfully, False otherwise
    """
    logger = getAppLogger()
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


def find_tool_executable(
    tool_name: str,
    custom_path: str | None = None,
) -> str | None:
    """Find tool executable, checking custom_path first, then PATH.

    Args:
        tool_name: Name of the tool to find
        custom_path: Optional custom path to the executable

    Returns:
        Path to executable if found, None otherwise
    """
    if custom_path:
        path = Path(custom_path)
        if path.exists() and path.is_file():
            return str(path.resolve())
        # If custom path doesn't exist, fall back to PATH

    return shutil.which(tool_name)


def build_tool_command(
    tool_label: str,
    category: str,  # noqa: ARG001
    file_path: Path,
    tool_override: ToolConfigResolved | None = None,  # noqa: ARG001
    tools_dict: dict[str, ToolConfigResolved] | None = None,
) -> list[str] | None:
    """Build the full command to execute a tool.

    Args:
        tool_label: Tool name or custom label (simple tool name or custom instance)
        category: Category name (static_checker, formatter, import_sorter) -
            unused, kept for API compatibility
        file_path: Path to the file to process
        tool_override: Optional tool override config (deprecated, unused)
        tools_dict: Dict of resolved tool configs keyed by label
            (includes defaults from resolved config)

    Returns:
        Command list if tool is available, None otherwise
    """
    # Look up tool in tools_dict (includes defaults from resolved config)
    if tools_dict and tool_label in tools_dict:
        tool_config = tools_dict[tool_label]
        validate_required_keys(
            tool_config, {"command", "args", "path", "options"}, "tool_config"
        )
        actual_tool_name = tool_config["command"]
        base_args = tool_config["args"]
        extra = tool_config["options"]
        custom_path = tool_config["path"]
    else:
        # Tool not found in tools_dict - not supported
        # (All tools should be in tools dict, including defaults)
        return None

    # Find executable
    executable = find_tool_executable(actual_tool_name, custom_path=custom_path)
    if not executable:
        return None

    return [executable, *base_args, *extra, str(file_path)]


def execute_post_processing(
    file_path: Path,
    config: PostProcessingConfigResolved,
) -> None:
    """Execute post-processing tools on a file according to configuration.

    Args:
        file_path: Path to the file to process
        config: Resolved post-processing configuration
    """
    validate_required_keys(
        config, {"enabled", "category_order", "categories"}, "config"
    )
    logger = getAppLogger()

    if not config["enabled"]:
        logger.debug("Post-processing disabled, skipping")
        return

    # Track executed commands for deduplication
    executed_commands: set[tuple[str, ...]] = set()

    # Process categories in order
    for category_name in config["category_order"]:
        if category_name not in config["categories"]:
            continue

        category = config["categories"][category_name]
        validate_required_keys(category, {"enabled", "priority", "tools"}, "category")
        if not category["enabled"]:
            logger.debug("Category %s is disabled, skipping", category_name)
            continue

        priority = category["priority"]
        if not priority:
            logger.debug("Category %s has empty priority, skipping", category_name)
            continue

        # Try tools in priority order
        tool_ran = False
        tools_dict = category["tools"]
        for tool_label in priority:
            # Tool should be in tools dict (guaranteed by resolution)
            tool_config = (
                tools_dict.get(tool_label) if tool_label in tools_dict else None
            )
            command = build_tool_command(
                tool_label, category_name, file_path, tool_config, tools_dict
            )

            if command is None:
                logger.debug(
                    "Tool %s not available or doesn't support category %s",
                    tool_label,
                    category_name,
                )
                continue

            # Deduplicate: skip if we've already run this exact command
            command_tuple = tuple(command)
            if command_tuple in executed_commands:
                logger.debug("Skipping duplicate command: %s", " ".join(command))
                continue

            # Execute command
            logger.debug("Running %s for category %s", tool_label, category_name)
            try:
                result = subprocess.run(  # noqa: S603
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    logger.debug(
                        "%s completed successfully for category %s",
                        tool_label,
                        category_name,
                    )
                    tool_ran = True
                    executed_commands.add(command_tuple)
                    break  # Success, move to next category
                logger.debug(
                    "%s exited with code %d: %s",
                    tool_label,
                    result.returncode,
                    result.stderr or result.stdout,
                )
            except Exception as e:  # noqa: BLE001
                logger.debug("Error running %s: %s", tool_label, e)

        if not tool_ran:
            logger.debug(
                "No tool succeeded for category %s (tried: %s)",
                category_name,
                priority,
            )


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
    logger = getAppLogger()

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


def _get_error_file_pattern(out_path: Path) -> str:
    """Get the glob pattern for error files matching the output path.

    Args:
        out_path: Path to the output file (e.g., dist/package.py)

    Returns:
        Glob pattern string (e.g., "package_ERROR_*.py")
    """
    stem = out_path.stem
    return f"{stem}_ERROR_*.py"


def _cleanup_error_files(out_path: Path) -> None:  # pyright: ignore[reportUnusedFunction]
    """Delete all error files matching the output path pattern.

    Args:
        out_path: Path to the output file (e.g., dist/package.py)
    """
    logger = getAppLogger()
    pattern = _get_error_file_pattern(out_path)
    error_files = list(out_path.parent.glob(pattern))
    if error_files:
        logger.debug(
            "Cleaning up %d error file(s) matching pattern: %s",
            len(error_files),
            pattern,
        )
        for error_file in error_files:
            try:
                error_file.unlink()
                logger.trace("Deleted error file: %s", error_file)
            except OSError as e:  # noqa: PERF203
                logger.debug("Failed to delete error file %s: %s", error_file, e)


def _write_error_file(  # pyright: ignore[reportUnusedFunction]
    out_path: Path,
    source: str,
    error: SyntaxError,
) -> Path:
    """Write source code to an error file with date suffix.

    Args:
        out_path: Path to the output file (e.g., dist/package.py)
        source: Source code that failed to compile
        error: SyntaxError from compilation failure

    Returns:
        Path to the written error file
    """
    logger = getAppLogger()
    now = datetime.now(timezone.utc)
    date_suffix = now.strftime("%Y_%m_%d")
    stem = out_path.stem
    error_filename = f"{stem}_ERROR_{date_suffix}.py"
    error_path = out_path.parent / error_filename

    # Get existing error files before writing (exclude the one we're about to write)
    pattern = _get_error_file_pattern(out_path)
    all_error_files = list(out_path.parent.glob(pattern))
    # Filter out the file we're about to write (in case it already exists)
    existing_error_files = [
        f for f in all_error_files if f.resolve() != error_path.resolve()
    ]

    # Build error header with troubleshooting information
    lineno = error.lineno or "unknown"
    error_msg = error.msg or "unknown error"
    separator = "# " + "=" * 70
    error_header = f"""{separator}
# COMPILATION ERROR - TROUBLESHOOTING FILE
# ============================================================================
# This file was generated because the stitched code failed to compile.
#
# Error Details:
#   - Type: SyntaxError
#   - Line: {lineno}
#   - Message: {error_msg}
#   - Generated: {now.isoformat()}
#
# Original Output Path: {out_path}
#
# Troubleshooting:
#   1. Review the error message above to identify the syntax issue
#   2. Check the source code around line {lineno} in this file
#   3. Fix the syntax error in your source files
#   4. Rebuild with: python -m serger
#   5. This error file can be safely deleted after fixing the issue
#
# If you need to report this error, please include:
#   - This error file (or the error details above)
#   - Your serger configuration
#   - The source files that were being stitched
# ============================================================================

"""

    # Write error file
    error_content = error_header + source
    error_path.write_text(error_content, encoding="utf-8")
    logger.warning("Compilation failed. Error file written to: %s", error_path)

    # Clean up pre-existing error files (excluding the one we just wrote)
    if existing_error_files:
        logger.debug(
            "Deleting %d pre-existing error file(s)", len(existing_error_files)
        )
        for old_error_file in existing_error_files:
            try:
                old_error_file.unlink()
                logger.trace("Deleted pre-existing error file: %s", old_error_file)
            except OSError as e:  # noqa: PERF203
                logger.debug(
                    "Failed to delete pre-existing error file %s: %s",
                    old_error_file,
                    e,
                )

    return error_path


def post_stitch_processing(
    out_path: Path,
    *,
    post_processing: PostProcessingConfigResolved | None = None,
) -> None:
    """Post-process a stitched file with tools, compilation checks, and verification.

    This function:
    1. Compiles the file before post-processing
    2. Runs configured post-processing tools (static checker, formatter, import sorter)
    3. Compiles the file after post-processing
    4. Reverts changes if compilation fails after processing but succeeded before
    5. Runs a basic execution sanity check

    If post-processing breaks compilation, this function logs a warning, reverts
    the file, and continues (does not raise). The build is considered successful
    as long as the original stitched file compiles.

    Args:
        out_path: Path to the stitched Python file
        post_processing: Post-processing configuration (if None, skips post-processing)

    Note:
        This function does not raise on post-processing failures. It only raises
        if the file doesn't compile before post-processing (which should never happen
        if in-memory compilation check was performed first).
    """
    logger = getAppLogger()
    logger.debug("Starting post-stitch processing for %s", out_path)

    # Compile before post-processing
    compiled_before = verify_compiles(out_path)
    if not compiled_before:
        # This should never happen if in-memory compilation check was performed
        # But handle it gracefully just in case
        logger.warning(
            "Stitched file does not compile before post-processing. "
            "Skipping post-processing and continuing."
        )
        # Still try to verify it executes
        verify_executes(out_path)
        return

    # Save original content in case we need to revert
    original_content = out_path.read_text(encoding="utf-8")

    # Run post-processing if configured
    processing_ran = False
    if post_processing:
        try:
            execute_post_processing(out_path, post_processing)
            processing_ran = True
            logger.debug("Post-processing completed")
        except Exception as e:  # noqa: BLE001
            # Post-processing tools can fail - log and continue
            logger.warning("Post-processing failed: %s. Reverting changes.", e)
            out_path.write_text(original_content, encoding="utf-8")
            out_path.chmod(0o755)
            return
    else:
        logger.debug("Post-processing skipped (no configuration)")

    # Compile after post-processing
    compiled_after = verify_compiles(out_path)
    if not compiled_after and compiled_before and processing_ran:
        # Revert if it compiled before but not after processing
        logger.warning(
            "File no longer compiles after post-processing. Reverting changes."
        )
        out_path.write_text(original_content, encoding="utf-8")
        out_path.chmod(0o755)
        # Verify it compiles after revert (should always succeed)
        if not verify_compiles(out_path):
            # This should never happen, but log it if it does
            logger.error(
                "File does not compile after reverting post-processing changes. "
                "This indicates a problem with the original stitched file."
            )
        return
    if not compiled_after:
        # It didn't compile after, but either it didn't compile before
        # or processing didn't run - this shouldn't happen if we checked before
        logger.warning(
            "File does not compile after post-processing. "
            "This should not happen if in-memory compilation check passed."
        )
        return

    # Run execution sanity check
    verify_executes(out_path)

    logger.debug("Post-stitch processing completed successfully")
