# src/serger/build.py


import contextlib
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from .config_types import BuildConfigResolved, IncludeResolved, PathResolved
from .constants import DEFAULT_DRY_RUN
from .logs import get_logger
from .stitch import (
    compute_module_order,
    extract_commit,
    extract_version,
    stitch_modules,
)
from .utils import cast_hint, has_glob_chars, is_excluded_raw


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
    logger = get_logger()
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
    logger = get_logger()
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
                logger.trace(f"[COLLECT] Excluded {file_path} by pattern {exc['path']}")
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
    logger = get_logger()
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
    logger = get_logger()
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
    build_cfg: BuildConfigResolved,
    root_path: Path,
) -> tuple[str, str, str]:
    """Extract version, commit, and build date for embedding.

    Args:
        build_cfg: Resolved build config
        root_path: Project root path

    Returns:
        Tuple of (version, commit, build_date)
    """
    # Use version from resolved config if available (from pyproject.toml),
    # otherwise fall back to extracting it directly
    version_raw = build_cfg.get("_pyproject_version")
    if version_raw and isinstance(version_raw, str):
        version = version_raw
    else:
        version = extract_version(root_path / "pyproject.toml")
    commit = extract_commit(root_path)
    build_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # If no version found, use timestamp as version
    if version == "unknown":
        version = build_date

    return version, commit, build_date


def run_build(  # noqa: PLR0915, PLR0912
    build_cfg: BuildConfigResolved,
) -> None:
    """Execute a single build task using a fully resolved config.

    Serger handles module stitching builds (combining Python modules into
    a single executable script). File copying is the responsibility of
    pocket-build, not serger.
    """
    logger = get_logger()
    dry_run = build_cfg.get("dry_run", DEFAULT_DRY_RUN)

    # Extract stitching fields from config
    package = build_cfg.get("package")
    order = build_cfg.get("order")
    license_header = build_cfg.get("license_header", "")
    out_entry = build_cfg["out"]

    # Skip if package is not provided (required for stitch builds)
    if not package:
        logger.warning(
            "Skipping build: 'package' field is required for "
            "stitch builds. This build does not have it. "
            "(File copying is handled by pocket-build, not serger.)"
        )
        return

    # Type checking - ensure correct types after narrowing
    if not isinstance(package, str):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = f"Invalid package name (expected str, got {type(package).__name__})"
        raise TypeError(xmsg)
    if order is not None and not isinstance(order, list):  # pyright: ignore[reportUnnecessaryIsInstance]
        xmsg = f"Invalid order (expected list, got {type(order).__name__})"
        raise TypeError(xmsg)

    # Determine output file path
    out_path = (out_entry["root"] / out_entry["path"]).resolve()
    if out_path.is_dir():
        out_path = out_path / f"{package}.py"

    if dry_run:
        logger.info("🧪 (dry-run) Would stitch %s to: %s", package, out_path)
        return

    # Collect included files using new collection functions
    includes = build_cfg.get("include", [])
    excludes = build_cfg.get("exclude", [])
    included_files, file_to_include = collect_included_files(includes, excludes)

    if not included_files:
        xmsg = "No files found matching include patterns"
        raise ValueError(xmsg)

    # Get config root for resolving order paths
    config_root = build_cfg["__meta__"]["config_root"]

    # Compute package root for module name derivation (needed for auto-discovery)
    package_root = find_package_root(included_files)

    # Resolve order paths (order is list[str] of paths, or None for auto-discovery)
    topo_paths: list[Path] | None = None
    if order is not None:
        # Use explicit order from config
        order_paths = resolve_order_paths(order, included_files, config_root)
        logger.debug("Using explicit order from config (%d entries)", len(order_paths))
    else:
        # Auto-discover order via topological sort
        logger.info("Auto-discovering module order via topological sort...")
        order_paths = compute_module_order(
            included_files, package_root, package, file_to_include
        )
        logger.debug("Auto-discovered order (%d modules)", len(order_paths))
        # When auto-discovered, order_paths IS the topological order, so we can reuse it
        topo_paths = order_paths

    # Resolve exclude_names to paths (exclude_names is list[str] of paths)
    exclude_names_raw = build_cfg.get("exclude_names", [])
    exclude_paths: list[Path] = []
    if exclude_names_raw:
        included_set = set(included_files)
        for exclude_name in cast("list[str]", exclude_names_raw):
            # Resolve path (absolute or relative to config_root)
            if Path(exclude_name).is_absolute():
                exclude_path = Path(exclude_name).resolve()
            else:
                exclude_path = (config_root / exclude_name).resolve()
            if exclude_path in included_set:
                exclude_paths.append(exclude_path)

    # Prepare config dict for stitch_modules
    display_name_raw = build_cfg.get("display_name", "")
    description_raw = build_cfg.get("description", "")
    repo_raw = build_cfg.get("repo", "")
    post_processing = build_cfg.get("post_processing")

    stitch_config: dict[str, object] = {
        "package": package,
        "order": order_paths,  # Pass resolved paths
        "exclude_names": exclude_paths,  # Pass resolved paths
        "display_name": display_name_raw,
        "description": description_raw,
        "repo": repo_raw,
        "topo_paths": topo_paths,  # Pre-computed topological order (if auto-discovered)
    }

    # Extract metadata for embedding (use package_root as root_path)
    version, commit, build_date = _extract_build_metadata(build_cfg, package_root)

    # Create parent directory if needed
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("🧵 Stitching %s → %s", package, out_path)

    try:
        stitch_modules(
            config=stitch_config,
            file_paths=included_files,
            package_root=package_root,
            file_to_include=file_to_include,
            out_path=out_path,
            license_header=license_header,
            version=version,
            commit=commit,
            build_date=build_date,
            post_processing=post_processing,
        )
        logger.info("✅ Stitch completed → %s\n", out_path)
    except RuntimeError as e:
        xmsg = f"Stitch build failed: {e}"
        raise RuntimeError(xmsg) from e


def run_all_builds(
    resolved_builds: list[BuildConfigResolved],
    *,
    dry_run: bool,
) -> None:
    logger = get_logger()
    root_level = logger.level_name
    logger.trace(f"[run_all_builds] Processing {len(resolved_builds)} build(s)")

    for i, build_cfg in enumerate(resolved_builds, 1):
        build_log_level = build_cfg.get("log_level")

        build_cfg["dry_run"] = dry_run

        # apply build-specific log level temporarily
        needs_override = build_log_level and build_log_level != root_level
        context = (
            logger.use_level(cast_hint(str, build_log_level))
            if needs_override
            else contextlib.nullcontext()
        )

        with context:
            if needs_override:
                logger.debug("Overriding log level → %s", build_log_level)

            logger.info("▶️  Build %d/%d", i, len(resolved_builds))
            run_build(build_cfg)

    logger.info("🎉 All builds complete.")
