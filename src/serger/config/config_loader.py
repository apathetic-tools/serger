# src/serger/config/config_loader.py


import argparse
import sys
import traceback
from pathlib import Path
from typing import Any, cast

from apathetic_logging import getLevelNumber, setRootLevel
from apathetic_utils import (
    cast_hint,
    load_jsonc,
    plural,
    remove_path_in_error_message,
)

from serger.logs import getAppLogger
from serger.meta import (
    PROGRAM_CONFIG,
)

from .config_types import (
    RootConfig,
)
from .config_validate import ValidationSummary, validate_config


def can_run_configless(args: argparse.Namespace) -> bool:
    """To run without config we need at least --include
    or --add-include (positional includes are merged into include).
    """
    return bool(getattr(args, "include", None) or getattr(args, "add_include", None))


def find_config(
    args: argparse.Namespace,
    cwd: Path,
    *,
    missing_level: str = "error",
) -> Path | None:
    """Locate a configuration file.

    missing_level: log-level for failing to find a configuration file.

    Search order:
      1. Explicit path from CLI (--config)
      2. Default candidates in the current working directory:
         .{PROGRAM_CONFIG}.py, .{PROGRAM_CONFIG}.jsonc, .{PROGRAM_CONFIG}.json

    Returns the first matching path, or None if no config was found.
    """
    # NOTE: We only have early no-config Log-Level
    logger = getAppLogger()

    try:
        getLevelNumber(missing_level)
    except ValueError:
        logger.error(  # noqa: TRY400
            "Invalid log level name in find_config(): %s", missing_level
        )
        missing_level = "error"

    # --- 1. Explicit config path ---
    if getattr(args, "config", None):
        config = Path(args.config).expanduser().resolve()
        logger.trace(f"[find_config] Checking explicit path: {config}")
        if not config.exists():
            # Explicit path → hard failure
            xmsg = f"Specified config file not found: {config}"
            raise FileNotFoundError(xmsg)
        if config.is_dir():
            xmsg = f"Specified config path is a directory, not a file: {config}"
            raise ValueError(xmsg)
        return config

    # --- 2. Default candidate files (search current dir and parents) ---
    # Search from cwd up to filesystem root, returning first match (closest to cwd)
    current = cwd
    candidate_names = [
        f".{PROGRAM_CONFIG}.py",
        f".{PROGRAM_CONFIG}.jsonc",
        f".{PROGRAM_CONFIG}.json",
    ]
    found: list[Path] = []
    while True:
        for name in candidate_names:
            candidate = current / name
            if candidate.exists():
                found.append(candidate)
        if found:
            # Found at least one config file at this level
            break
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    if not found:
        # Expected absence — soft failure (continue)
        logger.logDynamic(missing_level, f"No config file found in {cwd} or parents")
        return None

    # --- 3. Handle multiple matches at same level (prefer .py > .jsonc > .json) ---
    if len(found) > 1:
        # Prefer .py, then .jsonc, then .json
        priority = {".py": 0, ".jsonc": 1, ".json": 2}
        found_sorted = sorted(found, key=lambda p: priority.get(p.suffix, 99))
        names = ", ".join(p.name for p in found_sorted)
        logger.warning(
            "Multiple config files detected (%s); using %s.",
            names,
            found_sorted[0].name,
        )
        return found_sorted[0]
    return found[0]


def load_config(config_path: Path) -> dict[str, Any] | list[Any] | None:
    """Load configuration data from a file.

    Supports:
      - Python configs: .py files exporting either `config` or `includes`
      - JSON/JSONC configs: .json, .jsonc files

    Returns:
        The raw object defined in the config (dict, list, or None).
        Returns None for intentionally empty configs
          (e.g. empty files or `config = None`).

    Raises:
        ValueError if a .py config defines none of the expected variables.

    """
    # NOTE: We only have early no-config Log-Level
    logger = getAppLogger()
    logger.trace(f"[load_config] Loading from {config_path} ({config_path.suffix})")

    # --- Python config ---
    if config_path.suffix == ".py":
        config_globals: dict[str, Any] = {}

        # Allow local imports in Python configs (e.g. from ./helpers import foo)
        # This is safe because configs are trusted user code.
        parent_dir = str(config_path.parent)
        added_to_sys_path = parent_dir not in sys.path
        if added_to_sys_path:
            sys.path.insert(0, parent_dir)

        # Execute the python config file
        try:
            source = config_path.read_text(encoding="utf-8")
            exec(compile(source, str(config_path), "exec"), config_globals)  # noqa: S102
            logger.trace(
                f"[EXEC] globals after exec: {list(config_globals.keys())}",
            )
        except Exception as e:
            tb = traceback.format_exc()
            xmsg = (
                f"Error while executing Python config: {config_path.name}\n"
                f"{type(e).__name__}: {e}\n{tb}"
            )
            # Raise a generic runtime error for main() to catch and print cleanly
            raise RuntimeError(xmsg) from e
        finally:
            # Only remove if we actually inserted it
            if added_to_sys_path and sys.path[0] == parent_dir:
                sys.path.pop(0)

        for key in ("config", "includes"):
            if key in config_globals:
                result = config_globals[key]
                if not isinstance(result, (dict, list, type(None))):
                    xmsg = (
                        f"{key} in {config_path.name} must be a dict, list, or None"
                        f", not {type(result).__name__}"
                    )
                    raise TypeError(xmsg)

                # Explicitly narrow the loaded config to its expected union type.
                return cast("dict[str, Any] | list[Any] | None", result)

        xmsg = f"{config_path.name} did not define `config` or `includes`"
        raise ValueError(xmsg)

    # JSONC / JSON fallback
    try:
        return load_jsonc(config_path)
    except ValueError as e:
        clean_msg = remove_path_in_error_message(str(e), config_path)
        xmsg = (
            f"Error while loading configuration file '{config_path.name}': {clean_msg}"
        )
        raise ValueError(xmsg) from e


def _parse_case_2_list_of_strings(
    raw_config: list[str],
) -> dict[str, Any]:
    # --- Case 2: naked list of strings → flat config with include ---
    return {"include": list(raw_config)}


def _parse_case_flat_config(
    raw_config: dict[str, Any],
) -> dict[str, Any]:
    # --- Flat config: all fields at root level ---
    # The user gave a flat single-build config.
    # No hoisting needed - all fields are already at the root level.
    return dict(raw_config)


def parse_config(
    raw_config: dict[str, Any] | list[Any] | None,
) -> dict[str, Any] | None:
    """Normalize user config into canonical RootConfig shape (no filesystem work).

    Accepted forms:
      - None / [] / {}                → None (empty config)
      - ["src/**", "assets/**"]       → flat config with those includes
      - {...}                         → flat config (all fields at root level)

     After normalization:
      - Returns flat dict with all fields at root level, or None for empty config.
      - Preserves all unknown keys for later validation.
    """
    # NOTE: This function only normalizes shape — it does NOT validate or restrict keys.
    #       Unknown keys are preserved for the validation phase.

    logger = getAppLogger()
    logger.trace(f"[parse_config] Parsing {type(raw_config).__name__}")

    # --- Case 1: empty config → None ---
    # Includes None (empty file / config = None), [] (no builds), and {} (empty object)
    if not raw_config or raw_config == {}:  # handles None, [], {}
        return None

    # --- Case 2: naked list of strings → flat config with include ---
    if isinstance(raw_config, list) and all(isinstance(x, str) for x in raw_config):
        logger.trace("[parse_config] Detected case: list of strings")
        return _parse_case_2_list_of_strings(raw_config)

    # --- Invalid list types (not all strings) ---
    if isinstance(raw_config, list):
        xmsg = (
            "Invalid list configuration: "
            "all elements must be strings (for include patterns)."
        )
        raise TypeError(xmsg)

    # --- From here on, must be a dict ---
    # Defensive check: should be unreachable after list cases above,
    # but kept to guard against future changes or malformed input.
    if not isinstance(raw_config, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = (
            f"Invalid top-level value: {type(raw_config).__name__} "
            "(expected object or list of strings)",
        )
        raise TypeError(xmsg)

    # --- Flat config: all fields at root level ---
    # Note: build/builds keys will be rejected as unknown keys by validation
    return _parse_case_flat_config(raw_config)


def _validation_summary(
    summary: ValidationSummary,
    config_path: Path,
) -> None:
    """Pretty-print a validation summary using the standard log() interface."""
    logger = getAppLogger()
    mode = "strict mode" if summary.strict else "lenient mode"

    # --- Build concise counts line ---
    counts: list[str] = []
    if summary.errors:
        counts.append(f"{len(summary.errors)} error{plural(summary.errors)}")
    if summary.strict_warnings:
        counts.append(
            f"{len(summary.strict_warnings)} strict warning"
            f"{plural(summary.strict_warnings)}",
        )
    if summary.warnings:
        counts.append(
            f"{len(summary.warnings)} normal warning{plural(summary.warnings)}",
        )
    counts_msg = f"\nFound {', '.join(counts)}." if counts else ""

    # --- Header (single icon) ---
    if not summary.valid:
        logger.error(
            "Failed to validate configuration file %s (%s).%s",
            config_path.name,
            mode,
            counts_msg,
        )
    elif counts:
        logger.warning(
            "Validated configuration file  %s (%s) with warnings.%s",
            config_path.name,
            mode,
            counts_msg,
        )
    else:
        logger.debug("Validated  %s (%s) successfully.", config_path.name, mode)

    # --- Detailed sections ---
    if summary.errors:
        msg_summary = "\n  • ".join(summary.errors)
        logger.error("\nErrors:\n  • %s", msg_summary)
    if summary.strict_warnings:
        msg_summary = "\n  • ".join(summary.strict_warnings)
        logger.error("\nStrict warnings (treated as errors):\n  • %s", msg_summary)
    if summary.warnings:
        msg_summary = "\n  • ".join(summary.warnings)
        logger.warning("\nWarnings (non-fatal):\n  • %s", msg_summary)


def load_and_validate_config(
    args: argparse.Namespace,
) -> tuple[Path, RootConfig, ValidationSummary] | None:
    """Find, load, parse, and validate the user's configuration.

    Also determines the effective log level (from CLI/env/config/default)
    early, so logging can initialize as soon as possible.

    Returns:
        (config_path, root_cfg, validation_summary)
        if a config file was found and valid, or None if no config was found.

    """
    logger = getAppLogger()
    # warn if cwd doesn't exist, edge case. We might still be able to run
    cwd = Path.cwd().resolve()
    if not cwd.exists():
        logger.warning("Working directory does not exist: %s", cwd)

    # --- Find config file ---
    cwd = Path.cwd().resolve()
    missing_level = "warning" if can_run_configless(args) else "error"
    config_path = find_config(args, cwd, missing_level=missing_level)
    if config_path is None:
        return None

    # --- Load the raw config (dict or list) ---
    raw_config = load_config(config_path)
    if raw_config is None:
        return None

    # --- Early peek for log_level before parsing ---
    # Handles:
    #   - Root configs with "log_level"
    #   - Single-build dicts with "log_level"
    # Skips empty or list configs.
    if isinstance(raw_config, dict):
        raw_log_level = raw_config.get("log_level")
        if isinstance(raw_log_level, str) and raw_log_level:
            log_level = logger.determineLogLevel(
                args=args, root_log_level=raw_log_level
            )
            setRootLevel(log_level)

    # --- Parse structure into final form without types ---
    try:
        parsed_cfg = parse_config(raw_config)
    except TypeError as e:
        xmsg = f"Could not parse config {config_path.name}: {e}"
        raise TypeError(xmsg) from e
    if parsed_cfg is None:
        return None

    # --- Validate schema ---
    validation_result = validate_config(parsed_cfg)
    if not validation_result.valid:
        # Build comprehensive error message with all details
        mode = "strict mode" if validation_result.strict else "lenient mode"
        counts: list[str] = []
        if validation_result.errors:
            error_count = len(validation_result.errors)
            counts.append(f"{error_count} error{plural(validation_result.errors)}")
        if validation_result.strict_warnings:
            warning_count = len(validation_result.strict_warnings)
            counts.append(
                f"{warning_count} strict warning"
                f"{plural(validation_result.strict_warnings)}"
            )
        counts_msg = f"\nFound {', '.join(counts)}." if counts else ""

        # Build detailed error message with newlines
        error_parts: list[str] = []
        error_parts.append(
            f"Failed to validate configuration file {config_path.name} "
            f"({mode}).{counts_msg}"
        )

        if validation_result.errors:
            msg_summary = "\n  • ".join(validation_result.errors)
            error_parts.append(f"\nErrors:\n  • {msg_summary}")

        if validation_result.strict_warnings:
            msg_summary = "\n  • ".join(validation_result.strict_warnings)
            error_parts.append(
                f"\nStrict warnings (treated as errors):\n  • {msg_summary}"
            )

        xmsg = "".join(error_parts)
        exception = ValueError(xmsg)
        exception.data = validation_result  # type: ignore[attr-defined]
        raise exception

    # Log validation summary (only if valid or has warnings)
    _validation_summary(validation_result, config_path)

    # --- Upgrade to RootConfig type ---
    root_cfg: RootConfig = cast_hint(RootConfig, parsed_cfg)
    return config_path, root_cfg, validation_result
