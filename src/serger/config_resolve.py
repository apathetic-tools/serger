# src/serger/config_resolve.py


import argparse
import os
from pathlib import Path
from typing import Any, cast

from .config_types import (
    BuildConfig,
    BuildConfigResolved,
    IncludeResolved,
    MetaBuildConfigResolved,
    OriginType,
    PathResolved,
    RootConfig,
    RootConfigResolved,
)
from .constants import (
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_USE_PYPROJECT,
    DEFAULT_USE_RUFF,
    DEFAULT_WATCH_INTERVAL,
)
from .logs import get_logger
from .stitch import PyprojectMetadata, extract_pyproject_metadata
from .utils import has_glob_chars
from .utils_types import cast_hint, make_includeresolved, make_pathresolved


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _should_use_pyproject(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    num_builds: int,
) -> bool:
    """Determine if pyproject.toml should be used for this build.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)
        num_builds: Number of builds in root config

    Returns:
        True if pyproject.toml should be used, False otherwise
    """
    build_use_pyproject = build_cfg.get("use_pyproject")
    root_use_pyproject = (root_cfg or {}).get("use_pyproject")
    build_pyproject_path = build_cfg.get("pyproject_path")

    # Determine if this build has opted in
    build_opted_in = False
    if isinstance(build_use_pyproject, bool):
        build_opted_in = build_use_pyproject
    elif build_pyproject_path:
        # Specifying a path is an implicit opt-in
        build_opted_in = True

    if num_builds > 1:
        # Multi-build: build must explicitly opt-in
        return build_opted_in

    # Single build: use root/default settings unless build explicitly opts out
    if isinstance(build_use_pyproject, bool):
        return build_use_pyproject
    if build_pyproject_path:
        return True
    # Use root setting or default
    if isinstance(root_use_pyproject, bool):
        return root_use_pyproject
    return DEFAULT_USE_PYPROJECT


def _resolve_pyproject_path(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
) -> Path:
    """Resolve the path to pyproject.toml file.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution

    Returns:
        Resolved path to pyproject.toml
    """
    build_pyproject_path = build_cfg.get("pyproject_path")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")

    if build_pyproject_path:
        # Build-level path takes precedence
        return (config_dir / build_pyproject_path).resolve()
    if root_pyproject_path:
        # Root-level path
        return (config_dir / root_pyproject_path).resolve()
    # Default: config_dir / "pyproject.toml" (project root)
    return config_dir / "pyproject.toml"


def _is_explicitly_requested(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
) -> bool:
    """Check if pyproject.toml was explicitly requested (not just default).

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        True if explicitly requested, False if just default behavior
    """
    build_use_pyproject = build_cfg.get("use_pyproject")
    root_use_pyproject = (root_cfg or {}).get("use_pyproject")
    build_pyproject_path = build_cfg.get("pyproject_path")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")

    return (
        isinstance(build_use_pyproject, bool)
        or build_pyproject_path is not None
        or isinstance(root_use_pyproject, bool)
        or root_pyproject_path is not None
    )


def _extract_pyproject_metadata_safe(
    pyproject_path: Path,
    *,
    explicitly_requested: bool,
) -> PyprojectMetadata:
    """Extract metadata from pyproject.toml with error handling.

    Args:
        pyproject_path: Path to pyproject.toml
        explicitly_requested: Whether pyproject was explicitly requested

    Returns:
        PyprojectMetadata object (may be empty if unavailable)

    Raises:
        RuntimeError: If explicitly requested and TOML parsing unavailable
    """
    logger = get_logger()

    try:
        metadata = extract_pyproject_metadata(
            pyproject_path, required=explicitly_requested
        )
    except RuntimeError as e:
        # If explicitly requested and TOML parsing unavailable, re-raise
        if explicitly_requested:
            xmsg = (
                "pyproject.toml support was explicitly requested but "
                f"TOML parsing is unavailable. {e!s}"
            )
            raise RuntimeError(xmsg) from e
        # If not explicitly requested, this shouldn't happen (should return None)
        raise

    if metadata is None:
        # TOML parsing unavailable but not explicitly requested - warn and skip
        logger.warning(
            "pyproject.toml found but TOML parsing unavailable "
            "(Python 3.10 requires 'tomli'). "
            "Skipping metadata extraction. Install 'tomli' to enable, "
            "or explicitly set 'use_pyproject: false' to disable this warning."
        )
        # Create empty metadata object
        metadata = PyprojectMetadata()

    return metadata


def _apply_metadata_fields(
    resolved_cfg: dict[str, Any],
    metadata: PyprojectMetadata,
    pyproject_path: Path,
) -> None:
    """Apply extracted metadata fields to resolved config.

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        metadata: Extracted metadata
        pyproject_path: Path to pyproject.toml (for logging)
    """
    logger = get_logger()

    # Fill in missing fields (only if not already set in config)
    if metadata.version and not resolved_cfg.get("version"):
        # Note: version is not a build config field, but we'll store it
        # for use in build.py later
        resolved_cfg["_pyproject_version"] = metadata.version

    if metadata.name and not resolved_cfg.get("display_name"):
        resolved_cfg["display_name"] = metadata.name

    if metadata.description and not resolved_cfg.get("description"):
        resolved_cfg["description"] = metadata.description

    if metadata.license_text and not resolved_cfg.get("license_header"):
        resolved_cfg["license_header"] = metadata.license_text

    if metadata.has_any():
        logger.trace(f"[resolve_build_config] Extracted metadata from {pyproject_path}")


def _apply_pyproject_metadata(
    resolved_cfg: dict[str, Any],
    *,
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
    num_builds: int,
) -> None:
    """Extract and apply pyproject.toml metadata to resolved config.

    Handles all the logic for determining when to use pyproject.toml,
    path resolution, and filling in missing fields.

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        build_cfg: Original build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution
        num_builds: Number of builds in the root config
    """
    if not _should_use_pyproject(build_cfg, root_cfg, num_builds):
        return

    pyproject_path = _resolve_pyproject_path(build_cfg, root_cfg, config_dir)
    explicitly_requested = _is_explicitly_requested(build_cfg, root_cfg)

    metadata = _extract_pyproject_metadata_safe(
        pyproject_path, explicitly_requested=explicitly_requested
    )
    _apply_metadata_fields(resolved_cfg, metadata, pyproject_path)


def _load_gitignore_patterns(path: Path) -> list[str]:
    """Read .gitignore and return non-comment patterns."""
    patterns: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            clean_line = line.strip()
            if clean_line and not clean_line.startswith("#"):
                patterns.append(clean_line)
    return patterns


def _parse_include_with_dest(
    raw: str, context_root: Path
) -> tuple[IncludeResolved, bool]:
    """Parse include string with optional :dest suffix.

    Returns:
        (IncludeResolved, has_dest) tuple
    """
    has_dest = False
    path_str = raw
    dest_str = None

    # Handle "path:dest" format - split on last colon
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        path_part, dest_part = parts[0], parts[1]

        # Check if this is a Windows drive letter (C:, D:, etc.)
        # Drive letters are 1-2 chars, possibly with backslash
        is_drive_letter = len(path_part) <= 2 and (  # noqa: PLR2004
            len(path_part) == 1 or path_part.endswith("\\")
        )

        if not is_drive_letter:
            # Valid dest separator found
            path_str = path_part
            dest_str = dest_part
            has_dest = True

    # Normalize the path
    root, rel = _normalize_path_with_root(path_str, context_root)
    inc = make_includeresolved(rel, root, "cli")

    if has_dest and dest_str:
        inc["dest"] = Path(dest_str)

    return inc, has_dest


def _normalize_path_with_root(
    raw: Path | str,
    context_root: Path | str,
) -> tuple[Path, Path | str]:
    """Normalize a user-provided path (from CLI or config).

    - If absolute → treat that path as its own root.
      * `/abs/path/**` → root=/abs/path, rel="**"
      * `/abs/path/`   → root=/abs/path, rel="**"  (treat as contents)
      * `/abs/path`    → root=/abs/path, rel="."   (treat as literal)
    - If relative → root = context_root, path = raw (preserve string form)
    """
    logger = get_logger()
    raw_path = Path(raw)
    rel: Path | str

    # --- absolute path case ---
    if raw_path.is_absolute():
        # Split out glob or trailing slash intent
        raw_str = str(raw)
        if raw_str.endswith("/**"):
            root = Path(raw_str[:-3]).resolve()
            rel = "**"
        elif raw_str.endswith("/"):
            root = Path(raw_str[:-1]).resolve()
            rel = "**"  # treat directory as contents
        else:
            root = raw_path.resolve()
            rel = "."
    else:
        root = Path(context_root).resolve()
        # preserve literal string if user provided one
        rel = raw if isinstance(raw, str) else Path(raw)

    logger.trace(f"Normalized: raw={raw!r} → root={root}, rel={rel}")
    return root, rel


# --------------------------------------------------------------------------- #
# main per-build resolver
# --------------------------------------------------------------------------- #


def _resolve_includes(  # noqa: PLR0912
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> list[IncludeResolved]:
    logger = get_logger()
    logger.trace(
        f"[resolve_includes] Starting with"
        f" {len(resolved_cfg.get('include', []))} config includes"
    )

    includes: list[IncludeResolved] = []

    if getattr(args, "include", None):
        # Full override → relative to cwd
        for raw in args.include:
            inc, _ = _parse_include_with_dest(raw, cwd)
            includes.append(inc)

    elif "include" in resolved_cfg:
        # From config → relative to config_dir
        # Type narrowing: resolved_cfg is dict[str, Any], narrow the include list
        include_list: list[str | dict[str, str]] = cast(
            "list[str | dict[str, str]]", resolved_cfg["include"]
        )
        for raw in include_list:
            # Handle both string and object formats
            if isinstance(raw, dict):
                # Object format: {"path": "...", "dest": "..."}
                path_str = raw.get("path", "")
                dest_str = raw.get("dest")
                root, rel = _normalize_path_with_root(path_str, config_dir)
                inc = make_includeresolved(rel, root, "config")
                if dest_str:
                    # dest is relative to output dir, no normalization
                    inc["dest"] = Path(dest_str)
                includes.append(inc)
            else:
                # String format: "path/to/files"
                root, rel = _normalize_path_with_root(raw, config_dir)
                includes.append(make_includeresolved(rel, root, "config"))

    # Add-on includes (extend, not override)
    if getattr(args, "add_include", None):
        for raw in args.add_include:
            inc, _ = _parse_include_with_dest(raw, cwd)
            includes.append(inc)

    # unique path+root
    seen_inc: set[tuple[Path | str, Path]] = set()
    unique_inc: list[IncludeResolved] = []
    for i in includes:
        key = (i["path"], i["root"])
        if key not in seen_inc:
            seen_inc.add(key)
            unique_inc.append(i)

            # Check root existence
            if not i["root"].exists():
                logger.warning(
                    "Include root does not exist: %s (origin: %s)",
                    i["root"],
                    i["origin"],
                )

            # Check path existence
            if not has_glob_chars(str(i["path"])):
                full_path = i["root"] / i["path"]  # absolute paths override root
                if not full_path.exists():
                    logger.warning(
                        "Include path does not exist: %s (origin: %s)",
                        full_path,
                        i["origin"],
                    )

    return unique_inc


def _resolve_excludes(
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None,
) -> list[PathResolved]:
    logger = get_logger()
    logger.trace(
        f"[resolve_excludes] Starting with"
        f" {len(resolved_cfg.get('exclude', []))} config excludes"
    )

    excludes: list[PathResolved] = []

    def _add_excludes(paths: list[str], context: Path, origin: OriginType) -> None:
        # Exclude patterns (from CLI, config, or gitignore) should stay literal
        excludes.extend(make_pathresolved(raw, context, origin) for raw in paths)

    if getattr(args, "exclude", None):
        # Full override → relative to cwd
        # Keep CLI-provided exclude patterns as-is (do not resolve),
        # since glob patterns like "*.tmp" should match relative paths
        # beneath the include root, not absolute paths.
        _add_excludes(args.exclude, cwd, "cli")
    elif "exclude" in resolved_cfg:
        # From config → relative to config_dir
        _add_excludes(resolved_cfg["exclude"], config_dir, "config")

    # Add-on excludes (extend, not override)
    if getattr(args, "add_exclude", None):
        _add_excludes(args.add_exclude, cwd, "cli")

    # --- Merge .gitignore patterns into excludes if enabled ---
    # Determine whether to respect .gitignore
    if getattr(args, "respect_gitignore", None) is not None:
        respect_gitignore = args.respect_gitignore
    elif "respect_gitignore" in resolved_cfg:
        respect_gitignore = resolved_cfg["respect_gitignore"]
    else:
        # fallback — true by default, overridden by root config if needed
        respect_gitignore = (root_cfg or {}).get(
            "respect_gitignore",
            DEFAULT_RESPECT_GITIGNORE,
        )

    if respect_gitignore:
        gitignore_path = config_dir / ".gitignore"
        patterns = _load_gitignore_patterns(gitignore_path)
        if patterns:
            logger.trace(
                f"Adding {len(patterns)} .gitignore patterns from {gitignore_path}",
            )
        _add_excludes(patterns, config_dir, "gitignore")

    resolved_cfg["respect_gitignore"] = respect_gitignore

    # unique path+root
    seen_exc: set[tuple[Path | str, Path]] = set()
    unique_exc: list[PathResolved] = []
    for ex in excludes:
        key = (ex["path"], ex["root"])
        if key not in seen_exc:
            seen_exc.add(key)
            unique_exc.append(ex)

    return unique_exc


def _resolve_output(
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> PathResolved:
    logger = get_logger()
    logger.trace("[resolve_output] Resolving output directory")

    if getattr(args, "out", None):
        # Full override → relative to cwd
        root, rel = _normalize_path_with_root(args.out, cwd)
        out_wrapped = make_pathresolved(rel, root, "cli")
    elif "out" in resolved_cfg:
        # From config → relative to config_dir
        root, rel = _normalize_path_with_root(resolved_cfg["out"], config_dir)
        out_wrapped = make_pathresolved(rel, root, "config")
    else:
        root, rel = _normalize_path_with_root(DEFAULT_OUT_DIR, cwd)
        out_wrapped = make_pathresolved(rel, root, "default")

    return out_wrapped


def resolve_build_config(
    build_cfg: BuildConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None = None,
) -> BuildConfigResolved:
    """Resolve a single BuildConfig into a BuildConfigResolved.

    Applies CLI overrides, normalizes paths, merges gitignore behavior,
    and attaches provenance metadata.
    """
    logger = get_logger()
    logger.trace("[resolve_build_config] Starting resolution for build config")

    # Make a mutable copy
    resolved_cfg: dict[str, Any] = dict(build_cfg)

    # root provenance for all resolutions
    meta: MetaBuildConfigResolved = {
        "cli_root": cwd,
        "config_root": config_dir,
    }

    # --- Includes ---------------------------
    resolved_cfg["include"] = _resolve_includes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
    )
    logger.trace(
        f"[resolve_build_config] Resolved {len(resolved_cfg['include'])} include(s)"
    )

    # --- Excludes ---------------------------
    resolved_cfg["exclude"] = _resolve_excludes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
        root_cfg=root_cfg,
    )
    logger.trace(
        f"[resolve_build_config] Resolved {len(resolved_cfg['exclude'])} exclude(s)"
    )

    # --- Output ---------------------------
    resolved_cfg["out"] = _resolve_output(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
    )

    # ------------------------------
    # Log level
    # ------------------------------
    build_log = resolved_cfg.get("log_level")
    root_log = (root_cfg or {}).get("log_level")
    resolved_cfg["log_level"] = logger.determine_log_level(
        args=args, root_log_level=root_log, build_log_level=build_log
    )

    # ------------------------------
    # Strict config
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_strict = resolved_cfg.get("strict_config")
    root_strict = (root_cfg or {}).get("strict_config")
    if isinstance(build_strict, bool):
        resolved_cfg["strict_config"] = build_strict
    elif isinstance(root_strict, bool):
        resolved_cfg["strict_config"] = root_strict
    else:
        resolved_cfg["strict_config"] = DEFAULT_STRICT_CONFIG

    # ------------------------------
    # Use ruff
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_use_ruff = resolved_cfg.get("use_ruff")
    root_use_ruff = (root_cfg or {}).get("use_ruff")
    if isinstance(build_use_ruff, bool):
        resolved_cfg["use_ruff"] = build_use_ruff
    elif isinstance(root_use_ruff, bool):
        resolved_cfg["use_ruff"] = root_use_ruff
    else:
        resolved_cfg["use_ruff"] = DEFAULT_USE_RUFF

    # ------------------------------
    # Pyproject.toml metadata
    # ------------------------------
    num_builds = len((root_cfg or {}).get("builds", []))
    _apply_pyproject_metadata(
        resolved_cfg,
        build_cfg=build_cfg,
        root_cfg=root_cfg,
        config_dir=config_dir,
        num_builds=num_builds,
    )

    # ------------------------------
    # Attach provenance
    # ------------------------------
    resolved_cfg["__meta__"] = meta
    return cast_hint(BuildConfigResolved, resolved_cfg)


# --------------------------------------------------------------------------- #
# root-level resolver
# --------------------------------------------------------------------------- #


def resolve_config(
    root_input: RootConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> RootConfigResolved:
    """Fully resolve a loaded RootConfig into a ready-to-run RootConfigResolved.

    If invoked standalone, ensures the global logger reflects the resolved log level.
    If called after load_and_validate_config(), this is a harmless no-op re-sync."""
    logger = get_logger()
    root_cfg = cast_hint(RootConfig, dict(root_input))

    builds_input = root_cfg.get("builds", [])
    logger.trace(
        f"[resolve_config] Resolving root config with {len(builds_input)} build(s)"
    )

    # ------------------------------
    # Watch interval
    # ------------------------------
    env_watch = os.getenv(DEFAULT_ENV_WATCH_INTERVAL)
    if getattr(args, "watch", None) is not None:
        watch_interval = args.watch
    elif env_watch is not None:
        try:
            watch_interval = float(env_watch)
        except ValueError:
            logger.warning(
                "Invalid %s=%r, using default.", DEFAULT_ENV_WATCH_INTERVAL, env_watch
            )
            watch_interval = DEFAULT_WATCH_INTERVAL
    else:
        watch_interval = root_cfg.get("watch_interval", DEFAULT_WATCH_INTERVAL)

    logger.trace(f"[resolve_config] Watch interval resolved to {watch_interval}s")

    # ------------------------------
    # Log level
    # ------------------------------
    #  log_level: arg -> env -> build -> root -> default
    root_log = root_cfg.get("log_level")
    log_level = logger.determine_log_level(args=args, root_log_level=root_log)

    # --- sync runtime ---
    logger.setLevel(log_level)

    # ------------------------------
    # Resolve builds
    # ------------------------------
    resolved_builds = [
        resolve_build_config(b, args, config_dir, cwd, root_cfg) for b in builds_input
    ]

    # ------------------------------
    # Use ruff
    # ------------------------------
    use_ruff = root_cfg.get("use_ruff")
    if not isinstance(use_ruff, bool):
        use_ruff = DEFAULT_USE_RUFF

    resolved_root: RootConfigResolved = {
        "builds": resolved_builds,
        "strict_config": root_cfg.get("strict_config", False),
        "watch_interval": watch_interval,
        "log_level": log_level,
        "use_ruff": use_ruff,
    }

    return resolved_root
