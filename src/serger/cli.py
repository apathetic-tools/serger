# src/serger/cli.py

import argparse
import platform
import sys
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path

from apathetic_logging import LEVEL_ORDER, safeLog, setRootLevel
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
from .logs import getAppLogger
from .meta import DESCRIPTION, PROGRAM_DISPLAY, PROGRAM_PACKAGE, PROGRAM_SCRIPT
from .selftest import run_selftest


# --------------------------------------------------------------------------- #
# CLI setup and helpers
# --------------------------------------------------------------------------- #


class HintingArgumentParser(argparse.ArgumentParser):
    """Argument parser that provides helpful hints for mistyped arguments."""

    def error(self, message: str) -> None:  # type: ignore[override]
        """Override error to provide hints for unrecognized arguments."""
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


def _setup_parser() -> argparse.ArgumentParser:  # noqa: PLR0915
    """Define and return the CLI argument parser."""
    parser = HintingArgumentParser(
        prog=PROGRAM_SCRIPT,
        description=DESCRIPTION,
    )

    # --- Commands ---
    commands = parser.add_argument_group("Commands")

    # build (default)
    #   invalidated by: info, list, validate
    #   can be used with: watch, init
    #   not valid with: version, selftest, help
    commands.add_argument(
        "--build",
        action="store_true",
        help="Build stitched file from current directory or config file. (default)",
    )

    # watch (rebuild automatically)
    #   implies build
    #   can be used with: build, info, list, validate
    #   not affected by: init
    #   not valid with: version, selftest, help
    commands.add_argument(
        "-w",
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

    # info (display interpreter + metadata)
    #   invalidates: build
    #   can be used with: watch, init, list, validate
    #   not valid with: version, selftest, help
    commands.add_argument(
        "--info",
        default=False,
        action="store_true",
        help="Display the interpreter + metadata.",
    )

    # init (create default config file)
    #   does not imply build
    #   can be used with: build, watch, info, list, validate
    #   not valid with: version, selftest, help
    commands.add_argument(
        "--init",
        action="store_true",
        help=f"Create a .{PROGRAM_PACKAGE}.jsonc config file from defaults and args.",
    )

    # list (display packages and files)
    #   invalidates: build
    #   can be used with: watch, info, init, validate
    #   not valid with: version, selftest, help
    commands.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List packages and files.",
    )

    # validate (configuration file)
    #   invalidates: build
    #   can be used with: watch, info, init, list, dry-run
    #   not valid with: version, selftest, help
    commands.add_argument(
        "--validate",
        action="store_true",
        dest="validate",
        help=(
            "Validate configuration file and resolved settings without "
            "executing a build. Validates config syntax, file collection, "
            "and path resolution (includes CLI arguments and environment variables)."
        ),
    )

    # selftest
    #   invalidates: all
    #   not valid with: version, help
    commands.add_argument(
        "--selftest",
        action="store_true",
        help="Run a built-in sanity test to verify tool correctness.",
    )

    # version
    #   invalidates: all
    #   not valid with: selftest, help
    commands.add_argument("--version", action="store_true", help="Show version info.")

    # --- Build flags ---
    build_flags = parser.add_argument_group("Build flags")

    # includes
    build_flags.add_argument(  # positional
        "include",
        action="extend",
        nargs="*",
        metavar="INCLUDE",
        help="Source directory, file, or glob pattern (shorthand for --include).",
    )
    build_flags.add_argument(
        "-i",
        "--include",
        action="extend",
        nargs="+",
        metavar="PATH",
        dest="include",
        help="Override include paths. Format: path or path:dest",
    )
    build_flags.add_argument(  # convenience alias
        "-s",
        "--source",
        action="extend",
        nargs="+",
        dest="include",
        help=argparse.SUPPRESS,
    )

    # additional includes
    build_flags.add_argument(
        "--add-include",
        action="extend",
        nargs="+",
        metavar="PATH",
        dest="add_include",
        help=(
            "Additional include paths (relative to cwd). "
            "Format: path or path:dest. Extends config includes."
        ),
    )

    # excludes
    build_flags.add_argument(
        "-e",
        "--exclude",
        action="extend",
        nargs="+",
        metavar="PATH",
        dest="exclude",
        help=(
            "Override exclude patterns. Format: path directory, file, or glob pattern."
        ),
    )

    # additional excludes
    build_flags.add_argument(
        "--add-exclude",
        action="extend",
        nargs="+",
        metavar="PATH",
        dest="add_exclude",
        help="Additional exclude patterns (relative to cwd). Extends config excludes.",
    )

    # output
    build_flags.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        help=(
            "Override the name of the output file or directory. "
            "Use trailing slash for directories (e.g., 'dist/'), "
            "otherwise treated as file. "
            "Examples: 'dist/project.py' (file) or 'bin/' (directory)."
        ),
    )
    build_flags.add_argument(  # convenience alias
        "--out", dest="output", help=argparse.SUPPRESS
    )

    # input
    build_flags.add_argument(
        "--input",
        dest="input",
        default=None,
        help=(
            "Override the name of the input file or directory. "
            "Start from an existing build (usually optional)"
            "Examples: 'dist/project.py' (file) or 'bin/' (directory)."
        ),
    )
    build_flags.add_argument(  # convenience alias
        "--in",
        dest="input",  # note: args.in is reserved
        help=argparse.SUPPRESS,
    )

    # config
    build_flags.add_argument("--config", help="Path to build config file.")

    # --- Build options ---
    build_opts = parser.add_argument_group("Build & Watch options")

    # dry-run
    build_opts.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate build actions without copying or deleting files.",
    )

    # gitignore behavior
    gitignore = build_opts.add_mutually_exclusive_group()
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

    # shebang
    shebang = build_opts.add_mutually_exclusive_group()
    shebang.add_argument(
        "-p",
        "--shebang",
        "--python",
        dest="shebang",
        default=None,
        help="The name of the Python interpreter to use (default: auto decide).",
    )
    shebang.add_argument(
        "--no-shebang",
        action="store_false",
        dest="shebang",
        help="Disable shebang insertion",
    )

    # main
    main = build_opts.add_mutually_exclusive_group()
    main.add_argument(
        "-m",
        "--main",
        dest="entry_point",
        default=None,
        help=("The main function of the application (default: auto decide)."),
    )
    main.add_argument(
        "--no-main",
        action="store_false",
        dest="entry_point",
        help="Disable main insertion.",
    )

    # timestamps
    build_opts.add_argument(
        "--disable-build-timestamp",
        action="store_true",
        help="Disable build timestamps for deterministic builds (uses placeholder).",
    )

    # --- Universal flags ---
    uni = parser.add_argument_group("Universal flags")

    # force (overwrite)
    uni.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Overwrite existing file.",
    )

    # strict (configuration)
    uni.add_argument(
        "--strict",
        action="store_true",
        help="Fail on config validation warnings",
    )

    # compat (compatibility)
    uni.add_argument(
        "--compat",
        action="store_true",
        dest="compat",
        help="Compatibility mode with Stdlib zipapp behaviour",
    )
    uni.add_argument(  # convenience alias
        "--compatability",
        action="store_true",
        dest="compat",
        help=argparse.SUPPRESS,
    )

    # --- Terminal flags ---
    term = parser.add_argument_group("Terminal flags")

    # color
    color = term.add_mutually_exclusive_group()
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

    # verbosity
    log_level = term.add_mutually_exclusive_group()

    #   quiet
    log_level.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const="warning",
        dest="log_level",
        help="Suppress non-critical output (same as --log-level warning).",
    )

    #   brief
    log_level.add_argument(
        "-b",
        "--brief",
        action="store_const",
        const="brief",
        dest="log_level",
        help="Show brief output (same as --log-level brief).",
    )

    #   detail
    log_level.add_argument(
        "-d",
        "--detail",
        action="store_const",
        const="detail",
        dest="log_level",
        help="Show detailed output (same as --log-level detail).",
    )

    #   verbose
    log_level.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const="debug",
        dest="log_level",
        help="Verbose output (same as --log-level debug).",
    )

    #   log-level
    log_level.add_argument(
        "--log-level",
        choices=LEVEL_ORDER,
        default=None,
        dest="log_level",
        help="Set log verbosity level.",
    )

    return parser


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
    logger = getAppLogger()
    log_level = logger.determineLogLevel(args=args)
    setRootLevel(log_level)
    logger.enable_color = getattr(args, "enable_color", logger.determineColorEnabled())
    logger.trace("[BOOT] log-level initialized: %s", logger.levelName)

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
    logger = getAppLogger()

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


def _validate_package(  # noqa: PLR0912
    root_cfg: RootConfig,
    resolved: RootConfigResolved,
    _args: argparse.Namespace,
) -> bool:
    """
    Primary validation: Check that the build has a package name (required for
    stitch builds).

    This is the detailed validation that provides helpful error messages with
    context:
    - Lists available modules/packages found in source_bases
    - Explains why auto-detection failed (multiple modules, no modules, etc.)
    - Suggests solutions based on the specific situation
    - Respects strict_config to determine error vs warning

    This runs early in the CLI flow (after config resolution) to fail fast with
    actionable guidance. A defensive check in run_build() serves as a safety net
    for direct calls or edge cases.

    Note: Package is only required for stitch builds (which need includes).
    If there are no includes, package validation is skipped.

    Returns True if validation passes, False if we should abort.
    Logs appropriate warnings/errors.
    """
    logger = getAppLogger()

    # Package is only required for stitch builds (which need includes)
    # If there are no includes (config or CLI), skip package validation
    # Note: CLI includes are merged during resolve_config, so resolved.get("include")
    # should already include them. We check both resolved and args to be safe.
    config_includes = resolved.get("include", [])
    has_includes = len(config_includes) > 0
    has_cli_includes = bool(
        getattr(_args, "include", None) or getattr(_args, "add_include", None)
    )
    # If no includes at all, package is not required
    if not has_includes and not has_cli_includes:
        # No includes means no stitch build, so package is not required
        return True
    # If CLI provides includes, skip validation (package will be inferred from
    # CLI includes during resolution). This handles the case where CLI includes
    # are provided but package hasn't been resolved yet.
    if has_cli_includes:
        return True

    # The presence of "package" key (even if None) signals intentional choice:
    #   {"package": None}                  → package:null in config → no check
    #
    # Missing "package" key likely means forgotten or couldn't be auto-detected:
    #   {}                                 → no package key → check
    #   {"log_level": "debug"}             → no package key → check
    has_explicit_package_key = "package" in root_cfg

    # Check if package is missing in resolved config
    package = resolved.get("package")
    config_missing_package = not package

    if not has_explicit_package_key and config_missing_package:
        # Collect context for better error messages
        source_bases = resolved.get("source_bases", [])
        config_dir: Path | None = None
        meta = resolved.get("__meta__")
        if meta and isinstance(meta, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
            config_dir_raw = meta.get("config_root")
            if isinstance(config_dir_raw, Path):  # pyright: ignore[reportUnnecessaryIsInstance]
                config_dir = config_dir_raw

        # Get all modules found in source_bases for helpful error messages
        all_modules: list[str] = []
        if source_bases and config_dir:
            from .config.config_resolve import (  # noqa: PLC0415
                _get_first_level_modules_from_bases,  # pyright: ignore[reportPrivateUsage]
            )

            all_modules = _get_first_level_modules_from_bases(source_bases, config_dir)
            # Remove duplicates while preserving order
            seen: set[str] = set()
            unique_modules: list[str] = []
            for mod in all_modules:
                if mod not in seen:
                    seen.add(mod)
                    unique_modules.append(mod)
            all_modules = unique_modules

        # Build helpful error message based on what was found
        if not source_bases:
            msg = (
                "No package name found.\n"
                "   Use 'package' in your config, or set 'source_bases' to enable "
                "auto-detection."
            )
        elif len(all_modules) == 0:
            msg = (
                "No package name found. No modules found in source_bases: "
                f"{source_bases}.\n"
                "   Use 'package' in your config, or ensure source_bases contain "
                "Python modules/packages."
            )
        elif len(all_modules) == 1:
            # This shouldn't happen (should have been auto-detected), but provide
            # helpful message
            msg = (
                f"No package name found. Found single module '{all_modules[0]}' "
                f"in source_bases: {source_bases}.\n"
                "   This should have been auto-detected. Please specify 'package' "
                "explicitly or report this as a bug."
            )
        else:
            # Multiple modules found - explain why auto-detection failed
            modules_str = ", ".join(f"'{m}'" for m in all_modules)
            msg = (
                f"No package name found. Found multiple modules in source_bases "
                f"{source_bases}: {modules_str}.\n"
                "   Please specify 'package' explicitly in your config to "
                "indicate which module to use."
            )

        # Determine if we should error or warn based on strict_config
        any_strict = resolved.get("strict_config", True)

        if any_strict:
            # Error: config has no package and strict_config=true
            logger.error(msg)
            return False

        # Warning: config has no package but strict_config=false
        logger.warning(msg)

    return True


def _handle_early_exits(args: argparse.Namespace) -> int | None:
    """
    Handle early exit conditions (version, selftest, Python version check).

    Returns exit code if we should exit early, None otherwise.
    """
    logger = getAppLogger()

    # --- Version flag ---
    if getattr(args, "version", None):
        meta = get_metadata()
        stitched = " [stitched]" if globals().get("__STITCHED__", False) else ""
        logger.info(
            "%s %s (%s)%s", PROGRAM_DISPLAY, meta.version, meta.commit, stitched
        )
        return 0

    # --- Python version check ---
    if get_sys_version_info() < (3, 10):
        logger.error("%s requires Python 3.10 or newer.", PROGRAM_DISPLAY)
        return 1

    # --- Self-test mode ---
    if getattr(args, "selftest", None):
        return 0 if run_selftest() else 1

    return None


def _load_and_resolve_config(
    args: argparse.Namespace,
) -> _LoadedConfig:
    """Load config and resolve final configuration."""
    logger = getAppLogger()

    # --- Load configuration ---
    config_path: Path | None = None
    root_cfg: RootConfig | None = None
    config_result = load_and_validate_config(args)
    if config_result is not None:
        config_path, root_cfg, _validation_summary = config_result

    logger.trace("[CONFIG] log-level re-resolved from config: %s", logger.levelName)

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
    resolved["validate"] = getattr(args, "validate", False)

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


def main(argv: list[str] | None = None) -> int:  # noqa: PLR0911, PLR0912
    logger = getAppLogger()  # init (use env + defaults)

    try:
        parser = _setup_parser()
        args = parser.parse_args(argv)

        # --- Early runtime init (use CLI + env + defaults) ---
        _initialize_logger(args)

        # --- Handle early exits (version, selftest, etc.) ---
        # These exit immediately, so we don't need to check incompatibilities with them
        early_exit_code = _handle_early_exits(args)
        if early_exit_code is not None:
            return early_exit_code

        # --- Load and resolve configuration ---
        config = _load_and_resolve_config(args)

        # --- Validate includes ---
        if not _validate_includes(config.root_cfg, config.resolved, args):
            return 1

        # --- Validate package ---
        if not _validate_package(config.root_cfg, config.resolved, args):
            return 1

        # --- Validate-config notice ---
        if getattr(args, "validate", None):
            logger.info("🔍 Validating configuration...")

        # --- Dry-run notice ---
        if getattr(args, "dry_run", None):
            logger.info("🧪 Dry-run mode: no files will be written or deleted.\n")

        # --- Config summary ---
        if config.config_path:
            logger.detail("🔧 Using config: %s", config.config_path.name)
        else:
            logger.detail("🔧 Running in CLI-only mode (no config file).")
        logger.detail("📁 Config root: %s", config.config_dir)
        logger.detail("📂 Invoked from: %s", config.cwd)

        # --- Execute build ---
        _execute_build(config.resolved, args, argv)

    except (FileNotFoundError, ValueError, TypeError, RuntimeError) as e:
        # controlled termination
        silent = getattr(e, "silent", False)
        if not silent:
            try:
                logger.errorIfNotDebug(str(e))
            except Exception:  # noqa: BLE001
                safeLog(f"[FATAL] Logging failed while reporting: {e}")
        return getattr(e, "code", 1)

    except Exception as e:  # noqa: BLE001
        # unexpected internal error
        try:
            logger.criticalIfNotDebug("Unexpected internal error: %s", e)
        except Exception:  # noqa: BLE001
            safeLog(f"[FATAL] Logging failed while reporting: {e}")

        return getattr(e, "code", 1)

    else:
        return 0
