# src/serger/cli.py

import argparse
import platform
import sys
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from apathetic_logs import LEVEL_ORDER, safe_log
from apathetic_utils import cast_hint, get_sys_version_info

from .actions import get_metadata, watch_for_changes
from .build import run_build
from .config import (
    RootConfig,
    RootConfigResolved,
    load_and_validate_config,
    resolve_config,
)
from .constants import (
    DEFAULT_DRY_RUN,
    DEFAULT_WATCH_INTERVAL,
)
from .logs import get_app_logger
from .meta import (
    PROGRAM_DISPLAY,
    PROGRAM_SCRIPT,
)
from .selftest import run_selftest


# --------------------------------------------------------------------------- #
# CLI setup and helpers
# --------------------------------------------------------------------------- #


class HintingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        # Build known option strings: ["-v", "--verbose", "--log-level", ...]
        known_opts: list[str] = []
        for action in self._actions:
            known_opts.extend([s for s in action.option_strings if s])

        hint_lines: list[str] = []
        # Argparse message for bad flags is typically
        # "unrecognized arguments: --inclde ..."
        if "unrecognized arguments:" in message:
            bad = message.split("unrecognized arguments:", 1)[1].strip()
            # Split conservatively on whitespace
            bad_args = [tok for tok in bad.split() if tok.startswith("-")]
            for arg in bad_args:
                close = get_close_matches(arg, known_opts, n=1, cutoff=0.6)
                if close:
                    hint_lines.append(f"Hint: did you mean {close[0]}?")

        # Print usage + the original error
        self.print_usage(sys.stderr)
        full = f"{self.prog}: error: {message}"
        if hint_lines:
            full += "\n" + "\n".join(hint_lines)
        self.exit(2, full + "\n")


def _setup_parser() -> argparse.ArgumentParser:
    """Define and return the CLI argument parser."""
    parser = HintingArgumentParser(prog=PROGRAM_SCRIPT)

    # --- Positional shorthand arguments ---
    parser.add_argument(
        "positional_include",
        nargs="*",
        metavar="INCLUDE",
        help="Positional include paths or patterns (shorthand for --include).",
    )
    parser.add_argument(
        "positional_out",
        nargs="?",
        metavar="OUT",
        help=(
            "Positional output file or directory (shorthand for --out). "
            "Use trailing slash for directories (e.g., 'dist/'), "
            "otherwise treated as file."
        ),
    )

    # --- Standard flags ---
    parser.add_argument(
        "--include",
        nargs="+",
        help="Override include patterns. Format: path or path:dest",
    )
    parser.add_argument("--exclude", nargs="+", help="Override exclude patterns.")
    parser.add_argument(
        "-o",
        "--out",
        help=(
            "Override output file or directory. "
            "Use trailing slash for directories (e.g., 'dist/'), "
            "otherwise treated as file. "
            "Examples: 'dist/serger.py' (file) or 'bin/' (directory)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate build actions without copying or deleting files.",
    )
    parser.add_argument("-c", "--config", help="Path to build config file.")

    parser.add_argument(
        "--add-include",
        nargs="+",
        help=(
            "Additional include paths (relative to cwd). "
            "Format: path or path:dest. Extends config includes."
        ),
    )
    parser.add_argument(
        "--add-exclude",
        nargs="+",
        help="Additional exclude patterns (relative to cwd). Extends config excludes.",
    )

    parser.add_argument(
        "--watch",
        nargs="?",
        type=float,
        metavar="SECONDS",
        default=None,
        help=(
            "Rebuild automatically on changes. "
            "Optionally specify interval in seconds"
            f" (default config or: {DEFAULT_WATCH_INTERVAL}). "
        ),
    )

    # --- Gitignore behavior ---
    gitignore = parser.add_mutually_exclusive_group()
    gitignore.add_argument(
        "--gitignore",
        dest="respect_gitignore",
        action="store_true",
        help="Respect .gitignore when selecting files (default).",
    )
    gitignore.add_argument(
        "--no-gitignore",
        dest="respect_gitignore",
        action="store_false",
        help="Ignore .gitignore and include all files.",
    )
    gitignore.set_defaults(respect_gitignore=None)

    # --- Color ---
    color = parser.add_mutually_exclusive_group()
    color.add_argument(
        "--no-color",
        dest="use_color",
        action="store_const",
        const=False,
        help="Disable ANSI color output.",
    )
    color.add_argument(
        "--color",
        dest="use_color",
        action="store_const",
        const=True,
        help="Force-enable ANSI color output (overrides auto-detect).",
    )
    color.set_defaults(use_color=None)

    # --- Version and verbosity ---
    parser.add_argument("--version", action="store_true", help="Show version info.")

    log_level = parser.add_mutually_exclusive_group()
    log_level.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const="warning",
        dest="log_level",
        help="Suppress non-critical output (same as --log-level warning).",
    )
    log_level.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const="debug",
        dest="log_level",
        help="Verbose output (same as --log-level debug).",
    )
    log_level.add_argument(
        "--log-level",
        choices=LEVEL_ORDER,
        default=None,
        dest="log_level",
        help="Set log verbosity level.",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run a built-in sanity test to verify tool correctness.",
    )
    return parser


def _normalize_positional_args(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> None:
    """Normalize positional arguments into explicit include/out flags."""
    logger = get_app_logger()
    includes: list[str] = getattr(args, "positional_include", [])
    out_pos: str | None = getattr(args, "positional_out", None)

    # If no --out, assume last positional is output if we have ≥2 positionals
    if not getattr(args, "out", None) and len(includes) >= 2 and not out_pos:  # noqa: PLR2004
        out_pos = includes.pop()

    # If --out provided, treat all positionals as includes
    elif getattr(args, "out", None) and out_pos:
        logger.trace(
            "Interpreting all positionals as includes since --out was provided.",
        )
        includes.append(out_pos)
        out_pos = None

    # Conflict: can't mix --include and positional includes
    if getattr(args, "include", None) and (includes or out_pos):
        parser.error(
            "Cannot mix positional include arguments with --include; "
            "use --out for destination or --add-include to extend."
        )

    # Internal sanity check
    assert not (getattr(args, "out", None) and out_pos), (  # only for dev # noqa: S101
        "out_pos not cleared after normalization"
    )

    # Assign normalized values
    if includes:
        args.include = includes
    if out_pos:
        args.out = out_pos


# --------------------------------------------------------------------------- #
# Main entry helpers
# --------------------------------------------------------------------------- #


@dataclass
class _LoadedConfig:
    """Container for loaded and resolved configuration data."""

    config_path: Path | None
    root_cfg: RootConfig
    resolved: RootConfigResolved
    config_dir: Path
    cwd: Path


def _initialize_logger(args: argparse.Namespace) -> None:
    """Initialize logger with CLI args, env vars, and defaults."""
    logger = get_app_logger()
    log_level = logger.determine_log_level(args=args)
    logger.setLevel(log_level)
    logger.enable_color = getattr(
        args, "enable_color", logger.determine_color_enabled()
    )
    logger.trace("[BOOT] log-level initialized: %s", logger.level_name)

    logger.debug(
        "Runtime: Python %s (%s)\n    %s",
        platform.python_version(),
        platform.python_implementation(),
        sys.version.replace("\n", " "),
    )


def _validate_includes(
    root_cfg: RootConfig,
    resolved: RootConfigResolved,
    args: argparse.Namespace,
) -> bool:
    """
    Validate that the build has include patterns.

    Returns True if validation passes, False if we should abort.
    Logs appropriate warnings/errors.
    """
    logger = get_app_logger()

    # The presence of "include" key (even if empty) signals intentional choice:
    #   {"include": []}                    → include:[] in config → no check
    #
    # Missing "include" key likely means forgotten:
    #   {} or ""                           → no include key → check
    #   {"log_level": "debug"}             → no include key → check
    has_explicit_include_key = "include" in root_cfg

    # Check if CLI provides includes
    has_cli_includes = bool(
        getattr(args, "add_include", None) or getattr(args, "include", None)
    )

    # Check if config has no includes
    config_missing_includes = not resolved.get("include")

    if (
        not has_explicit_include_key
        and not has_cli_includes
        and config_missing_includes
    ):
        # Determine if we should error or warn based on strict_config
        any_strict = resolved.get("strict_config", True)

        if any_strict:
            # Error: config has no includes and strict_config=true
            logger.error(
                "No include patterns found "
                "(strict_config=true prevents continuing).\n"
                "   Use 'include' in your config or pass "
                "--include / --add-include.",
            )
            return False

        # Warning: config has no includes but strict_config=false
        logger.warning(
            "No include patterns found.\n"
            "   Use 'include' in your config or pass "
            "--include / --add-include.",
        )

    return True


def _handle_early_exits(args: argparse.Namespace) -> int | None:
    """
    Handle early exit conditions (version, selftest, Python version check).

    Returns exit code if we should exit early, None otherwise.
    """
    logger = get_app_logger()

    # --- Version flag ---
    if getattr(args, "version", None):
        meta = get_metadata()
        standalone = " [standalone]" if globals().get("__STANDALONE__", False) else ""
        logger.info(
            "%s %s (%s)%s", PROGRAM_DISPLAY, meta.version, meta.commit, standalone
        )
        return 0

    # --- Python version check ---
    if get_sys_version_info() < (3, 10):
        logger.error("%s requires Python 3.10 or newer.", {PROGRAM_DISPLAY})
        return 1

    # --- Self-test mode ---
    if getattr(args, "selftest", None):
        return 0 if run_selftest() else 1

    return None


def _load_and_resolve_config(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
) -> _LoadedConfig:
    """Load config, normalize args, and resolve final configuration."""
    logger = get_app_logger()

    # --- Load configuration ---
    config_path: Path | None = None
    root_cfg: RootConfig | None = None
    config_result = load_and_validate_config(args)
    if config_result is not None:
        config_path, root_cfg, _validation_summary = config_result

    logger.trace("[CONFIG] log-level re-resolved from config: %s", logger.level_name)

    # --- Normalize shorthand arguments ---
    _normalize_positional_args(args, parser)
    cwd = Path.cwd().resolve()
    config_dir = config_path.parent if config_path else cwd

    # --- CLI-only mode fallback ---
    # Remove early bailout check - let downstream logic (auto-include, file
    # collection) handle validation. This allows pyproject.toml-based configless
    # builds to proceed and fail with more appropriate error messages if needed.
    if root_cfg is None:
        logger.info("No config file found — using CLI-only mode.")
        root_cfg = cast_hint(RootConfig, {})

    # --- Resolve config with args and defaults ---
    resolved = resolve_config(root_cfg, args, config_dir, cwd)

    return _LoadedConfig(
        config_path=config_path,
        root_cfg=root_cfg,
        resolved=resolved,
        config_dir=config_dir,
        cwd=cwd,
    )


def _execute_build(
    resolved: RootConfigResolved,
    args: argparse.Namespace,
    argv: list[str] | None,
) -> None:
    """Execute build either in watch mode or one-time mode."""
    watch_enabled = getattr(args, "watch", None) is not None or (
        "--watch" in (argv or [])
    )

    resolved["dry_run"] = getattr(args, "dry_run", DEFAULT_DRY_RUN)

    if watch_enabled:
        watch_interval = resolved["watch_interval"]
        watch_for_changes(
            lambda: run_build(resolved),
            resolved,
            interval=watch_interval,
        )
    else:
        run_build(resolved)


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    logger = get_app_logger()  # init (use env + defaults)

    try:
        parser = _setup_parser()
        args = parser.parse_args(argv)

        # --- Early runtime init (use CLI + env + defaults) ---
        _initialize_logger(args)

        # --- Handle early exits (version, selftest, etc.) ---
        early_exit_code = _handle_early_exits(args)
        if early_exit_code is not None:
            return early_exit_code

        # --- Load and resolve configuration ---
        config = _load_and_resolve_config(args, parser)

        # --- Validate includes ---
        if not _validate_includes(config.root_cfg, config.resolved, args):
            return 1

        # --- Dry-run notice ---
        if getattr(args, "dry_run", None):
            logger.info("🧪 Dry-run mode: no files will be written or deleted.\n")

        # --- Config summary ---
        if config.config_path:
            logger.info("🔧 Using config: %s", config.config_path.name)
        else:
            logger.info("🔧 Running in CLI-only mode (no config file).")
        logger.info("📁 Config root: %s", config.config_dir)
        logger.info("📂 Invoked from: %s", config.cwd)

        # --- Execute build ---
        _execute_build(config.resolved, args, argv)

    except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
        # controlled termination
        silent = getattr(e, "silent", False)
        if not silent:
            try:
                logger.error_if_not_debug(str(e))
            except Exception:  # noqa: BLE001
                safe_log(f"[FATAL] Logging failed while reporting: {e}")
        return getattr(e, "code", 1)

    except Exception as e:  # noqa: BLE001
        # unexpected internal error
        try:
            logger.critical_if_not_debug("Unexpected internal error: %s", e)
        except Exception:  # noqa: BLE001
            safe_log(f"[FATAL] Logging failed while reporting: {e}")

        return getattr(e, "code", 1)

    else:
        return 0
