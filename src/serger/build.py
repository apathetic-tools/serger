# src/serger/build.py


from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from apathetic_utils import (
    detect_packages_from_files,
    has_glob_chars,
    is_excluded_raw,
)

from .config import IncludeResolved, PathResolved, RootConfigResolved
from .constants import BUILD_TIMESTAMP_PLACEHOLDER, DEFAULT_DRY_RUN
from .logs import getAppLogger
from .stitch import (
    compute_module_order,
    extract_commit,
    is_serger_build,
    stitch_modules,
)
from .utils import shorten_path_for_display
from .utils.utils_validation import validate_required_keys


# --------------------------------------------------------------------------- #
# File collection functions (Phase 1)
# --------------------------------------------------------------------------- #


def expand_include_pattern(include: IncludeResolved) -> list[Path]:
    """Expand a single include pattern to a list of matching Python files.

    Args:
        include: Resolved include pattern with root and path

    Returns:
        List of resolved absolute paths to matching .py files
    """
    validate_required_keys(include, {"path", "root"}, "include")
    logger = getAppLogger()
    src_pattern = str(include["path"])
    root = Path(include["root"]).resolve()
    matches: list[Path] = []

    if src_pattern.endswith("/") and not has_glob_chars(src_pattern):
        logger.trace(
            f"[MATCH] Treating as trailing-slash directory include → {src_pattern!r}",
        )
        root_dir = root / src_pattern.rstrip("/")
        if root_dir.exists():
            all_files = [p for p in root_dir.rglob("*") if p.is_file()]
            matches = [p for p in all_files if p.suffix == ".py"]
        else:
            logger.trace(f"[MATCH] root_dir does not exist: {root_dir}")

    elif src_pattern.endswith("/**"):
        logger.trace(f"[MATCH] Treating as recursive include → {src_pattern!r}")
        root_dir = root / src_pattern.removesuffix("/**")
        if root_dir.exists():
            all_files = [p for p in root_dir.rglob("*") if p.is_file()]
            matches = [p for p in all_files if p.suffix == ".py"]
        else:
            logger.trace(f"[MATCH] root_dir does not exist: {root_dir}")

    elif has_glob_chars(src_pattern):
        logger.trace(f"[MATCH] Using glob() for pattern {src_pattern!r}")
        # Make pattern relative to root if it's absolute
        pattern_path = Path(src_pattern)
        if pattern_path.is_absolute():
            try:
                # Try to make it relative to root
                src_pattern = str(pattern_path.relative_to(root))
            except ValueError:
                # If pattern is not under root, use just the pattern name
                src_pattern = pattern_path.name
        all_matches = list(root.glob(src_pattern))
        matches = [p for p in all_matches if p.is_file() and p.suffix == ".py"]
        logger.trace(f"[MATCH] glob found {len(matches)} .py file(s)")

    else:
        logger.trace(f"[MATCH] Treating as literal include {root / src_pattern}")
        candidate = root / src_pattern
        if candidate.is_file() and candidate.suffix == ".py":
            matches = [candidate]

    # Resolve all paths to absolute
    resolved_matches = [p.resolve() for p in matches]

    for i, m in enumerate(resolved_matches):
        logger.trace(f"[MATCH]   {i + 1:02d}. {m}")

    return resolved_matches


def collect_included_files(
    includes: list[IncludeResolved],
    excludes: list[PathResolved],
) -> tuple[list[Path], dict[Path, IncludeResolved]]:
    """Expand all include patterns and apply excludes.

    Args:
        includes: List of resolved include patterns
        excludes: List of resolved exclude patterns

    Returns:
        Tuple of (filtered file paths, mapping of file to its include)
    """
    for inc in includes:
        validate_required_keys(inc, {"path", "root"}, "include")
    for exc in excludes:
        validate_required_keys(exc, {"path", "root"}, "exclude")
    logger = getAppLogger()
    all_files: set[Path] = set()
    # Track which include produced each file (for dest parameter and exclude checking)
    file_to_include: dict[Path, IncludeResolved] = {}

    # Expand all includes
    for inc in includes:
        matches = expand_include_pattern(inc)
        for match in matches:
            all_files.add(match)
            file_to_include[match] = inc  # Store the include for dest access

    logger.trace(
        f"[COLLECT] Found {len(all_files)} file(s) from {len(includes)} include(s)",
    )

    # Apply excludes - each exclude has its own root!
    filtered: list[Path] = []
    for file_path in all_files:
        # Check file against all excludes, using each exclude's root
        is_excluded = False
        for exc in excludes:
            exclude_root = Path(exc["root"]).resolve()
            exclude_patterns = [str(exc["path"])]
            if is_excluded_raw(file_path, exclude_patterns, exclude_root):
                exc_display = shorten_path_for_display(exc)
                logger.trace(
                    "[COLLECT] Excluded %s by pattern %s",
                    file_path,
                    exc_display,
                )
                is_excluded = True
                break
        if not is_excluded:
            filtered.append(file_path)

    logger.trace(f"[COLLECT] After excludes: {len(filtered)} file(s)")

    return sorted(filtered), file_to_include


def _normalize_order_pattern(entry: str, config_root: Path) -> str:
    """Normalize an order entry pattern relative to config_root.

    Args:
        entry: Order entry (path, relative or absolute)
        config_root: Root directory for resolving relative paths

    Returns:
        Normalized pattern string relative to config_root
    """
    pattern_path = Path(entry)
    if pattern_path.is_absolute():
        try:
            return str(pattern_path.relative_to(config_root))
        except ValueError:
            return pattern_path.name
    return entry


def _collect_recursive_files(
    root_dir: Path,
    included_set: set[Path],
    explicitly_ordered: set[Path],
) -> list[Path]:
    """Collect Python files recursively from a directory.

    Args:
        root_dir: Directory to search recursively
        included_set: Set of included file paths to filter by
        explicitly_ordered: Set of already-ordered paths to exclude

    Returns:
        List of matching file paths
    """
    if not root_dir.exists():
        return []
    all_files = [p for p in root_dir.rglob("*") if p.is_file()]
    return [
        p.resolve()
        for p in all_files
        if p.suffix == ".py"
        and p.resolve() in included_set
        and p.resolve() not in explicitly_ordered
    ]


def _collect_glob_files(
    pattern_str: str,
    config_root: Path,
    included_set: set[Path],
    explicitly_ordered: set[Path],
) -> list[Path]:
    """Collect Python files matching a glob pattern.

    Args:
        pattern_str: Glob pattern string
        config_root: Root directory for glob
        included_set: Set of included file paths to filter by
        explicitly_ordered: Set of already-ordered paths to exclude

    Returns:
        List of matching file paths
    """
    all_matches = list(config_root.glob(pattern_str))
    return [
        p.resolve()
        for p in all_matches
        if p.is_file()
        and p.suffix == ".py"
        and p.resolve() in included_set
        and p.resolve() not in explicitly_ordered
    ]


def _handle_literal_file_path(
    entry: str,
    pattern_str: str,
    config_root: Path,
    included_set: set[Path],
    explicitly_ordered: set[Path],
    resolved: list[Path],
) -> bool:
    """Handle a literal file path entry.

    Args:
        entry: Original order entry string
        pattern_str: Normalized pattern string
        config_root: Root directory for resolving paths
        included_set: Set of included file paths
        explicitly_ordered: Set of already-ordered paths
        resolved: List to append resolved paths to

    Returns:
        True if handled as literal file, False if should continue pattern matching
    """
    logger = getAppLogger()
    candidate = config_root / pattern_str
    if candidate.exists() and candidate.is_dir():
        # Directory without trailing slash - treat as recursive
        return False

    # Treat as literal file path
    if candidate.is_absolute():
        path = candidate.resolve()
    else:
        path = (config_root / pattern_str).resolve()

    if path not in included_set:
        xmsg = (
            f"Order entry {entry!r} resolves to {path}, which is not in included files"
        )
        raise ValueError(xmsg)

    if path in explicitly_ordered:
        logger.warning(
            "Order entry %r (→ %s) appears multiple times in order list",
            entry,
            path,
        )
    else:
        resolved.append(path)
        explicitly_ordered.add(path)
        logger.trace("[ORDER] %r → %s", entry, path)
    return True


def resolve_order_paths(
    order: list[str],
    included_files: list[Path],
    config_root: Path,
) -> list[Path]:
    """Resolve order entries (paths) to actual file paths.

    Supports multiple pattern formats:
    - Explicit file paths: "src/serger/utils.py"
    - Non-recursive glob: "src/serger/*" (matches direct children only)
    - Recursive directory: "src/serger/" (trailing slash = recursive)
    - Recursive pattern: "src/serger/**" (explicit recursive)
    - Directory without slash: "src/serger" (if directory exists, recursive)

    Wildcard patterns are expanded to match all remaining files in included_files
    that haven't been explicitly ordered yet. Matched files are sorted alphabetically.

    Args:
        order: List of order entries (paths, relative or absolute, or glob patterns)
        included_files: List of included file paths to validate against
        config_root: Root directory for resolving relative paths

    Returns:
        Ordered list of resolved file paths

    Raises:
        ValueError: If an order entry resolves to a path not in included files
    """
    logger = getAppLogger()
    included_set = set(included_files)
    resolved: list[Path] = []
    explicitly_ordered: set[Path] = set()

    for entry in order:
        pattern_str = _normalize_order_pattern(entry, config_root)
        matching_files: list[Path] = []

        # Handle different directory pattern formats
        # (matching expand_include_pattern behavior)
        if pattern_str.endswith("/") and not has_glob_chars(pattern_str):
            # Trailing slash directory: "src/serger/" → recursive match
            logger.trace("[ORDER] Treating as trailing-slash directory: %r", entry)
            root_dir = config_root / pattern_str.rstrip("/")
            matching_files = _collect_recursive_files(
                root_dir, included_set, explicitly_ordered
            )
            if not matching_files:
                logger.trace("[ORDER] Directory does not exist: %s", root_dir)

        elif pattern_str.endswith("/**"):
            # Explicit recursive pattern: "src/serger/**" → recursive match
            logger.trace("[ORDER] Treating as recursive pattern: %r", entry)
            root_dir = config_root / pattern_str.removesuffix("/**")
            matching_files = _collect_recursive_files(
                root_dir, included_set, explicitly_ordered
            )
            if not matching_files:
                logger.trace("[ORDER] Directory does not exist: %s", root_dir)

        elif has_glob_chars(pattern_str):
            # Glob pattern: "src/serger/*" → non-recursive glob
            logger.trace("[ORDER] Expanding glob pattern: %r", entry)
            matching_files = _collect_glob_files(
                pattern_str, config_root, included_set, explicitly_ordered
            )

        else:
            # Literal path (no glob chars, no trailing slash)
            candidate = config_root / pattern_str
            if candidate.exists() and candidate.is_dir():
                # Directory without trailing slash: "src/serger" → recursive match
                logger.trace("[ORDER] Treating as directory: %r", entry)
                matching_files = _collect_recursive_files(
                    candidate, included_set, explicitly_ordered
                )
            # Try to handle as literal file path
            elif _handle_literal_file_path(
                entry,
                pattern_str,
                config_root,
                included_set,
                explicitly_ordered,
                resolved,
            ):
                continue  # Skip pattern expansion logic

        # Sort matching files alphabetically for consistent ordering
        matching_files.sort()

        for path in matching_files:
            resolved.append(path)
            explicitly_ordered.add(path)
            logger.trace("[ORDER] %r → %s (pattern match)", entry, path)

        if not matching_files:
            logger.trace("[ORDER] Pattern %r matched no files", entry)

    return resolved


def find_package_root(file_paths: list[Path]) -> Path:
    """Compute common root (lowest common ancestor) of all file paths.

    Args:
        file_paths: List of file paths

    Returns:
        Common root path (lowest common ancestor)

    Raises:
        ValueError: If no common root can be found or list is empty
    """
    if not file_paths:
        xmsg = "Cannot find package root: no file paths provided"
        raise ValueError(xmsg)

    # Resolve all paths to absolute
    resolved_paths = [p.resolve() for p in file_paths]

    # Find common prefix by comparing path parts
    first_parts = list(resolved_paths[0].parts)
    common_parts: list[str] = []

    # For single file, exclude the filename itself (return parent directory)
    if len(resolved_paths) == 1:
        # Remove the last part (filename) for single file case
        common_parts = first_parts[:-1] if len(first_parts) > 1 else first_parts
    else:
        # For multiple files, find common prefix
        for i, part in enumerate(first_parts):
            # Check if all other paths have the same part at this position
            if all(
                i < len(list(p.parts)) and list(p.parts)[i] == part
                for p in resolved_paths[1:]
            ):
                common_parts.append(part)
            else:
                break

    if not common_parts:
        # No common prefix - use filesystem root
        return Path(resolved_paths[0].anchor)

    return Path(*common_parts)


# --------------------------------------------------------------------------- #
# internal helper
# --------------------------------------------------------------------------- #


def _extract_build_metadata(
    *,
    build_cfg: RootConfigResolved,
    project_root: Path,
    git_root: Path | None = None,
    disable_timestamp: bool = False,
) -> tuple[str, str, str]:
    """Extract version, commit, and build date for embedding.

    Args:
        build_cfg: Resolved build config
        project_root: Project root path (for finding pyproject.toml)
        git_root: Git repository root path (for finding .git, defaults to project_root)
        disable_timestamp: If True, use placeholder instead of real timestamp

    Returns:
        Tuple of (version, commit, build_date)
    """
    # Priority order for version:
    # 1. version from resolved config (user version -> pyproject version, resolved
    #    during config resolution if pyproject metadata was enabled)
    # 2. timestamp as last resort
    # Note: Version is fully resolved during config resolution, so we just need
    # to check the resolved config and fall back to timestamp if not set
    version = build_cfg.get("version")
    # Use git_root for commit extraction (project root), fallback to project_root
    commit_path = git_root if git_root is not None else project_root
    logger = getAppLogger()
    logger.trace(
        "_extract_build_metadata: project_root=%s, git_root=%s, commit_path=%s",
        project_root,
        git_root,
        commit_path,
    )
    commit = extract_commit(commit_path)
    logger.trace("_extract_build_metadata: extracted commit=%s", commit)

    if disable_timestamp:
        build_date = BUILD_TIMESTAMP_PLACEHOLDER
        # If still no version found, use placeholder as version
        if not version or version == "unknown":
            version = BUILD_TIMESTAMP_PLACEHOLDER
    else:
        build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        # If still no version found, use timestamp as version
        if not version or version == "unknown":
            version = build_date

    return version, commit, build_date


def run_build(  # noqa: C901, PLR0915, PLR0912
    build_cfg: RootConfigResolved,
) -> None:
    """Execute a single build task using a fully resolved config.

    Serger handles module stitching builds (combining Python modules into
    a single executable script). File copying is the responsibility of
    pocket-build, not serger.
    """
    validate_required_keys(
        build_cfg,
        {
            "out",
            "__meta__",
            "post_processing",
            "external_imports",
            "stitch_mode",
            "comments_mode",
            "docstring_mode",
        },
        "build_cfg",
    )
    logger = getAppLogger()
    dry_run = build_cfg.get("dry_run", DEFAULT_DRY_RUN)
    validate = build_cfg.get("validate", False)

    # Extract stitching fields from config
    package = build_cfg.get("package")
    order = build_cfg.get("order")
    license_text = build_cfg.get("license", "")
    out_entry = build_cfg["out"]

    # Collect included files to check if this is a stitch build
    includes = build_cfg.get("include", [])
    excludes = build_cfg.get("exclude", [])
    # Validation happens inside collect_included_files
    logger.trace(
        "🔍 [DEBUG] Collecting files - includes: %s, excludes: %s",
        includes,
        excludes,
    )
    included_files, file_to_include = collect_included_files(includes, excludes)
    logger.trace(
        "🔍 [DEBUG] Collected %d files: %s",
        len(included_files),
        included_files[:5] if included_files else [],
    )

    # Safety net: Defensive check for missing package
    # This is a minimal safety check for:
    #   - Direct calls to run_build() (bypassing CLI validation)
    #   - Edge cases where validation might have been missed
    # Primary validation with detailed error messages happens in _validate_package()
    # in cli.py, which runs early in the CLI flow after config resolution.
    # Note: Package is only required for stitch builds (which need includes).
    # If there are no included files, package is not required.
    if included_files:
        if not package:
            xmsg = (
                "Package name is required for stitch builds. "
                "This should have been caught during validation. "
                "If you're calling run_build() directly, ensure package is set "
                "in the config."
            )
            raise ValueError(xmsg)

        # Type checking - ensure correct types after narrowing
        if not isinstance(package, str):  # pyright: ignore[reportUnnecessaryIsInstance]
            xmsg = f"Invalid package name (expected str, got {type(package).__name__})"
            raise TypeError(xmsg)
    if order is not None and not isinstance(order, list):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = f"Invalid order (expected list, got {type(order).__name__})"
        raise TypeError(xmsg)

    # Determine output file path
    validate_required_keys(out_entry, {"path", "root"}, "build_cfg['out']")
    out_path = (out_entry["root"] / out_entry["path"]).resolve()
    # Check if it's a directory (exists and is dir) or should be treated as one
    # If path doesn't exist and has no .py extension, treat as directory
    # Use the resolved path string to check for .py extension
    # (handles absolute paths correctly)
    out_path_str = str(out_path)
    is_directory = out_path.is_dir() or (
        not out_path.exists() and not out_path_str.endswith(".py")
    )
    # Only use package for output path if we have included files (stitch build)
    if is_directory and included_files and package:
        out_path = out_path / f"{package}.py"

    # --- Validate-config exit point ---
    # Exit after file collection but before expensive stitching work
    if validate:
        # Build summary (accounting for output already shown)
        summary_parts: list[str] = []
        if included_files:
            summary_parts.append(f"{len(included_files)} file(s) collected")
            if package:
                summary_parts.append(f"package: {package}")
        else:
            summary_parts.append("no files (not a stitch build)")
        if out_path:
            meta = build_cfg["__meta__"]
            out_display = shorten_path_for_display(
                out_path,
                cwd=meta.get("cli_root"),
                config_dir=meta.get("config_root"),
            )
            summary_parts.append(f"output: {out_display}")
        logger.info("✓ Configuration is valid (%s)", " • ".join(summary_parts))
        return

    if not included_files:
        # No files to stitch - this is not a stitch build
        # Return early (package validation already skipped above)
        logger.trace(
            "🔍 [DEBUG] No included files - returning early without creating output"
        )
        return

    # At this point, we have included_files, so package must be set and valid
    # (validated above). Type guard for type checker.
    if not package or not isinstance(package, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = (
            "Package must be set when included_files exist. "
            "This should have been caught during validation."
        )
        raise ValueError(xmsg)

    # Safety check: Don't overwrite files that aren't serger builds
    # (fail fast before doing expensive work)
    # Compute once and pass down to avoid recomputation
    max_lines = build_cfg.get("build_tool_find_max_lines")
    is_serger_build_result = not out_path.exists() or is_serger_build(
        out_path, max_lines=max_lines
    )
    if out_path.exists() and not is_serger_build_result:
        xmsg = (
            f"Refusing to overwrite {out_path} because it does not appear "
            "to be a serger-generated build. If you want to overwrite this "
            "file, please delete it first or rename it."
        )
        raise RuntimeError(xmsg)

    # Get config root for resolving order paths and validating module_actions
    validate_required_keys(
        build_cfg["__meta__"], {"config_root"}, "build_cfg['__meta__']"
    )
    config_root = build_cfg["__meta__"]["config_root"]

    # Validate and normalize module_actions if present
    # (needed when module_actions are set after config resolution, e.g., in tests)
    # Import here to avoid circular dependency
    from serger.config.config_resolve import (  # noqa: PLC0415
        validate_and_normalize_module_actions,
    )

    module_actions_raw = build_cfg.get("module_actions")
    if module_actions_raw:
        module_actions = validate_and_normalize_module_actions(
            module_actions_raw,
            config_dir=config_root,
        )
        # Update build_cfg with validated actions
        build_cfg["module_actions"] = module_actions
    else:
        module_actions = []

    # Collect files from source_path in module_actions
    source_path_files: set[Path] = set()
    for action in module_actions:
        if "source_path" in action:
            affects_val = action.get("affects", "shims")
            if "stitching" in affects_val or affects_val == "both":
                source_path_str = action["source_path"]
                source_path_resolved = Path(source_path_str).resolve()

                # Validate file exists (should have been validated in config resolution)
                if not source_path_resolved.exists():
                    # This should not happen if validation worked, but check anyway
                    msg = (
                        f"source_path file does not exist: {source_path_resolved}. "
                        f"This should have been caught during config validation."
                    )
                    raise ValueError(msg)

                source_path_files.add(source_path_resolved)

                # Add to file_to_include if not already present
                if source_path_resolved not in file_to_include:
                    # Create a synthetic IncludeResolved for this file
                    # Use the file's parent directory as root
                    synthetic_include: IncludeResolved = {
                        "path": str(source_path_resolved),
                        "root": source_path_resolved.parent,
                        "origin": "code",  # Mark as code-generated
                    }
                    file_to_include[source_path_resolved] = synthetic_include

    # Merge source_path files into included_files
    all_included_files = sorted(set(included_files) | source_path_files)

    # Resolve exclude_names to paths (exclude_names is list[str] of paths)
    # Do this early so we can exclude them before package detection
    exclude_names_raw = build_cfg.get("exclude_names", [])
    exclude_paths: list[Path] = []
    if exclude_names_raw:
        included_set = set(all_included_files)
        for exclude_name in cast("list[str]", exclude_names_raw):
            # Resolve path (absolute or relative to config_root)
            if Path(exclude_name).is_absolute():
                exclude_path = Path(exclude_name).resolve()
            else:
                exclude_path = (config_root / exclude_name).resolve()
            if exclude_path in included_set:
                exclude_paths.append(exclude_path)

    # Filter out excluded files to get final set for stitching
    # Note: source_path files override excludes (they're added after initial collection)
    # and should not be filtered out by exclude_paths
    exclude_set = set(exclude_paths)
    # Remove source_path files from exclude_set to ensure they're not filtered out
    exclude_set -= source_path_files
    final_files = [f for f in all_included_files if f not in exclude_set]

    if not final_files:
        xmsg = "No files remaining after exclusions"
        raise ValueError(xmsg)

    # Warn about files outside project directory
    cwd = Path.cwd().resolve()
    config_root_resolved = Path(config_root).resolve()
    # Get source_bases and installed_bases to check if file is in them
    source_bases = build_cfg.get("source_bases", [])
    installed_bases = build_cfg.get("installed_bases", [])
    # Convert to Path objects for comparison
    source_base_paths = [Path(base).resolve() for base in source_bases]
    installed_base_paths = [Path(base).resolve() for base in installed_bases]
    for file_path in final_files:
        file_path_resolved = file_path.resolve()
        # Check if file is inside source_bases or installed_bases
        is_in_source_bases = any(
            file_path_resolved.is_relative_to(base_path)
            for base_path in source_base_paths
        )
        is_in_installed_bases = any(
            file_path_resolved.is_relative_to(base_path)
            for base_path in installed_base_paths
        )
        # Check if file is outside both config_root and CWD
        is_outside_config = not file_path_resolved.is_relative_to(config_root_resolved)
        is_outside_cwd = not file_path_resolved.is_relative_to(cwd)
        # Only warn if outside config/CWD AND not in source_bases or installed_bases
        should_warn = (
            is_outside_config
            and is_outside_cwd
            and not is_in_source_bases
            and not is_in_installed_bases
        )
        if should_warn:
            logger.warning(
                "Including file outside project directory: %s "
                "(config root: %s, CWD: %s)",
                file_path_resolved,
                config_root_resolved,
                cwd,
            )

    # Compute package root for module name derivation (needed for auto-discovery)
    package_root = find_package_root(final_files)

    # Detect packages once from final files (after all exclusions)
    logger.debug("Detecting packages from included files (after exclusions)...")
    source_bases = build_cfg.get("source_bases", [])
    # Save user-provided source_bases (from config, before adding discovered ones)
    # Filter out package directories (those with __init__.py) as they shouldn't be used
    # for module name derivation (would lose package name)
    user_provided_source_bases: list[str] = []
    for base_str in source_bases:
        base_path = Path(base_str)
        # Skip if this is a package directory (has __init__.py)
        # Package directories extracted from includes shouldn't be used for derivation
        if (base_path / "__init__.py").exists():
            logger.trace(
                "[MODULE_BASES] Skipping package directory for user-provided bases: %s",
                base_str,
            )
            continue
        user_provided_source_bases.append(base_str)
    detected_packages, discovered_parent_dirs = detect_packages_from_files(
        final_files, package, source_bases=source_bases
    )

    # Add discovered package parent directories to source_bases (lowest priority)
    if discovered_parent_dirs:
        # Deduplicate while preserving order (add at end)
        seen_bases = set(source_bases)
        for parent_dir in discovered_parent_dirs:
            if parent_dir not in seen_bases:
                seen_bases.add(parent_dir)
                source_bases.append(parent_dir)
                logger.debug(
                    "[MODULE_BASES] Added discovered package parent directory: %s",
                    parent_dir,
                )
                # Also add to user_provided_source_bases if it's not a package directory
                # (discovered parent directories are typically not package directories)
                parent_path = Path(parent_dir)
                if (
                    not (parent_path / "__init__.py").exists()
                    and parent_dir not in user_provided_source_bases
                ):
                    user_provided_source_bases.append(parent_dir)
                    logger.trace(
                        "[MODULE_BASES] Added discovered parent directory to "
                        "user_provided_source_bases: %s",
                        parent_dir,
                    )
        # Update build_cfg with extended source_bases
        build_cfg["source_bases"] = source_bases

    # Now detect base directories in source_bases as packages if they contain
    # detected packages (must happen after source_bases is fully populated)
    # This handles cases where a directory in source_bases contains packages
    # but doesn't have __init__.py itself (namespace packages)
    # Re-detect packages now that source_bases is fully populated
    # This will pick up base directories that are now in source_bases
    detected_packages_updated, _ = detect_packages_from_files(
        final_files, package, source_bases=source_bases
    )
    # Merge any newly detected packages
    if detected_packages_updated != detected_packages:
        newly_detected = detected_packages_updated - detected_packages
        if newly_detected:
            detected_packages = detected_packages_updated
            logger.debug(
                "[MODULE_BASES] Detected additional packages after adding "
                "discovered bases: %s",
                sorted(newly_detected),
            )
    # Store user-provided source_bases (filtered) for use in derive_module_name
    # This excludes package directories extracted from includes
    # Use dict update to avoid TypedDict type error for internal field
    build_cfg_dict: dict[str, object] = build_cfg  # type: ignore[assignment]
    build_cfg_dict["_user_provided_source_bases"] = (
        user_provided_source_bases if user_provided_source_bases else []
    )

    # Resolve order paths (order is list[str] of paths, or None for auto-discovery)
    topo_paths: list[Path] | None = None
    if order is not None:
        # Use explicit order from config (filtered to final_files)
        order_paths = resolve_order_paths(order, final_files, config_root)
        logger.debug("Using explicit order from config (%d entries)", len(order_paths))
        # Add source_path files that aren't already in order_paths
        order_paths_set = set(order_paths)
        for source_path_file in sorted(source_path_files):
            if source_path_file not in order_paths_set:
                order_paths.append(source_path_file)
                logger.debug("Added source_path file to order: %s", source_path_file)
    else:
        # Auto-discover order via topological sort (using final_files)
        logger.info("Auto-discovering module order via topological sort...")
        order_paths = compute_module_order(
            final_files,
            package_root,
            package,
            file_to_include,
            detected_packages=detected_packages,
            source_bases=source_bases,
            user_provided_source_bases=user_provided_source_bases,
        )
        logger.debug("Auto-discovered order (%d modules)", len(order_paths))
        # When auto-discovered, order_paths IS the topological order, so we can reuse it
        topo_paths = order_paths

    # Prepare config dict for stitch_modules
    # post_processing, external_imports, stitch_mode, comments_mode already validated
    display_name_raw = build_cfg.get("display_name", "")
    description_raw = build_cfg.get("description", "")
    repo_raw = build_cfg.get("repo", "")
    post_processing = build_cfg["post_processing"]
    external_imports = build_cfg["external_imports"]
    stitch_mode = build_cfg["stitch_mode"]
    module_mode = build_cfg["module_mode"]
    shim = build_cfg.get("shim", "all")
    comments_mode = build_cfg["comments_mode"]
    docstring_mode = build_cfg["docstring_mode"]
    # module_actions already validated and normalized above

    stitch_config: dict[str, object] = {
        "package": package,
        "order": order_paths,  # Pass resolved paths (already excludes exclude_paths)
        "exclude_names": exclude_paths,  # Pass resolved paths (for validation)
        "display_name": display_name_raw,
        "description": description_raw,
        "repo": repo_raw,
        "topo_paths": topo_paths,  # Pre-computed topological order (if auto-discovered)
        "external_imports": external_imports,
        "stitch_mode": stitch_mode,
        "module_mode": module_mode,
        "shim": shim,
        "module_actions": module_actions,
        "comments_mode": comments_mode,
        "docstring_mode": docstring_mode,
        "main_mode": build_cfg.get("main_mode", "auto"),
        "main_name": build_cfg.get("main_name"),
        "detected_packages": detected_packages,  # Pre-detected packages
        "source_bases": source_bases,  # For package detection fallback
        "_user_provided_source_bases": build_cfg.get(
            "_user_provided_source_bases", []
        ),  # User-provided (filtered) for derive_module_name
        "__meta__": build_cfg["__meta__"],  # For config_dir access in fallback
    }

    # Extract metadata for embedding
    # Use config_root for finding pyproject.toml (project root) and for git
    config_root = build_cfg["__meta__"]["config_root"]
    # Resolve to absolute path for git operations
    git_root = config_root.resolve()
    disable_timestamp = build_cfg.get("disable_build_timestamp", False)
    version, commit, build_date = _extract_build_metadata(
        build_cfg=build_cfg,
        project_root=config_root,
        git_root=git_root,  # Use resolved project root for git operations
        disable_timestamp=disable_timestamp,
    )

    # Create parent directory if needed (skip in dry-run)
    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)

    # Dry-run exit: simulate full pre-stitch pipeline, exit before stitching
    if dry_run:
        # Build comprehensive summary
        dry_run_summary_parts: list[str] = []
        dry_run_summary_parts.append(f"Package: {package}")
        dry_run_summary_parts.append(f"Files: {len(final_files)} module(s)")
        dry_run_summary_parts.append(f"Output: {out_path}")

        # Add detected packages (if verbose/debug)
        if detected_packages:
            packages_str = ", ".join(sorted(detected_packages))
            logger.debug("Detected packages: %s", packages_str)

        # Add order resolution method
        order_method = "explicit" if order is not None else "auto-discovered"
        logger.debug("Order: %s (%d modules)", order_method, len(order_paths))

        logger.info("🧪 (dry-run) Would stitch: %s", " • ".join(dry_run_summary_parts))
        return

    meta = build_cfg["__meta__"]
    out_display = shorten_path_for_display(
        out_path,
        cwd=meta.get("cli_root"),
        config_dir=meta.get("config_root"),
    )
    logger.trace(
        "🔍 [DEBUG] About to stitch - out_path: %s, out_display: %s",
        out_path,
        out_display,
    )
    logger.info("🧵 Stitching %s → %s", package, out_display)

    try:
        stitch_modules(
            config=stitch_config,
            file_paths=included_files,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            license_text=license_text,
            version=version,
            commit=commit,
            build_date=build_date,
            post_processing=post_processing,
            is_serger_build=is_serger_build_result,
        )
        logger.brief("✅ Stitch completed → %s\n", out_display)
    except RuntimeError as e:
        xmsg = f"Stitch build failed: {e}"
        raise RuntimeError(xmsg) from e
