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

from .config_types import PostProcessingConfigResolved, ToolConfig
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
    _category: str,
    file_path: Path,
    _tool_override: ToolConfig | None = None,
    tools_dict: dict[str, ToolConfig] | None = None,
) -> list[str] | None:
    """Build the full command to execute a tool.

    Args:
        tool_label: Tool name or custom label (simple tool name or custom instance)
        _category: Category name (static_checker, formatter, import_sorter) -
            unused, kept for API compatibility
        file_path: Path to the file to process
        _tool_override: Optional tool override config (deprecated, unused)
        tools_dict: Dict of tool overrides keyed by label
            (includes defaults from resolved config)

    Returns:
        Command list if tool is available, None otherwise
    """
    # Look up tool in tools_dict (includes defaults from resolved config)
    if tools_dict and tool_label in tools_dict:
        override = tools_dict[tool_label]
        actual_tool_name = override.get("command", tool_label)  # default to key

        # Args is required in tools dict (defaults are merged in during resolution)
        if "args" not in override:
            return None
        base_args = override["args"]

        # Append options (not replace)
        extra = override.get("options", [])
        custom_path = override.get("path")
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
    logger = get_logger()

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
        if not category.get("enabled", True):
            logger.debug("Category %s is disabled, skipping", category_name)
            continue

        priority = category.get("priority", [])
        if not priority:
            logger.debug("Category %s has empty priority, skipping", category_name)
            continue

        # Try tools in priority order
        tool_ran = False
        tools_dict = category.get("tools", {})
        for tool_label in priority:
            # For backward compatibility, check if tool_label exists in tools dict
            # If it does, it's a custom instance; if not, it's a simple tool name
            tool_override = (
                tools_dict.get(tool_label) if tool_label in tools_dict else None
            )
            command = build_tool_command(
                tool_label, category_name, file_path, tool_override, tools_dict
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
    post_processing: PostProcessingConfigResolved | None = None,
) -> None:
    """Post-process a stitched file with tools, compilation checks, and verification.

    This function:
    1. Compiles the file before post-processing
    2. Runs configured post-processing tools (static checker, formatter, import sorter)
    3. Compiles the file after post-processing
    4. Reverts changes if compilation fails after processing but succeeded before
    5. Runs a basic execution sanity check

    Args:
        out_path: Path to the stitched Python file
        post_processing: Post-processing configuration (if None, skips post-processing)

    Raises:
        RuntimeError: If compilation fails and cannot be reverted
    """
    logger = get_logger()
    logger.debug("Starting post-stitch processing for %s", out_path)

    # Compile before post-processing
    compiled_before = verify_compiles(out_path)
    if not compiled_before:
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
        execute_post_processing(out_path, post_processing)
        processing_ran = True
        logger.debug("Post-processing completed")
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
        # Verify it compiles after revert
        if not verify_compiles(out_path):
            xmsg = (
                "File does not compile after reverting post-processing changes. "
                "This indicates a problem with the original stitched file."
            )
            raise RuntimeError(xmsg)
    elif not compiled_after:
        # It didn't compile after, but either it didn't compile before
        # or processing didn't run, so we can't revert
        xmsg = "Stitched file does not compile after post-processing"
        raise RuntimeError(xmsg)

    # Run execution sanity check
    verify_executes(out_path)

    logger.debug("Post-stitch processing completed successfully")
