# src/serger/utils/utils_modules.py


from pathlib import Path

from apathetic_utils import get_glob_root, has_glob_chars

from serger.config.config_types import IncludeResolved
from serger.logs import getAppLogger
from serger.utils.utils_validation import validate_required_keys


def _interpret_dest_for_module_name(  # noqa: PLR0911
    file_path: Path,
    include_root: Path,
    include_pattern: str,
    dest: Path | str,
) -> Path:
    """Interpret dest parameter to compute virtual destination path for module name.

    This adapts logic from _compute_dest() but returns a path that can be used
    for module name derivation, not an actual file system destination.

    Args:
        file_path: The actual source file path
        include_root: Root directory for the include pattern
        include_pattern: Original include pattern string
        dest: Dest parameter (can be pattern, relative path, or explicit override)

    Returns:
        Virtual destination path that should be used for module name derivation
    """
    logger = getAppLogger()
    dest_path = Path(dest)
    include_root_resolved = Path(include_root).resolve()
    file_path_resolved = file_path.resolve()

    logger.trace(
        f"[DEST_INTERPRET] file={file_path}, root={include_root}, "
        f"pattern={include_pattern!r}, dest={dest}",
    )

    # If dest is absolute, use it directly
    if dest_path.is_absolute():
        result = dest_path.resolve()
        logger.trace(f"[DEST_INTERPRET] absolute dest → {result}")
        return result

    # Treat trailing slashes as if they implied recursive includes
    if include_pattern.endswith("/"):
        include_pattern = include_pattern.rstrip("/")
        try:
            rel = file_path_resolved.relative_to(
                include_root_resolved / include_pattern,
            )
            result = dest_path / rel
            logger.trace(
                f"[DEST_INTERPRET] trailing-slash include → rel={rel}, result={result}",
            )
            return result  # noqa: TRY300
        except ValueError:
            logger.trace("[DEST_INTERPRET] trailing-slash fallback (ValueError)")
            return dest_path / file_path.name

    # Handle glob patterns
    if has_glob_chars(include_pattern):
        # Special case: if dest is just a simple name (no path parts) and pattern
        # is a single-level file glob like "a/*.py" (one directory part, then /*.py),
        # use dest directly (explicit override)
        # This handles the case where dest is meant to override the entire module name
        dest_parts = list(dest_path.parts)
        # Count directory parts before the glob (split by / and count non-glob parts)
        pattern_dir_parts = include_pattern.split("/")
        # Remove the glob part (last part containing *)
        non_glob_parts = [
            p
            for p in pattern_dir_parts
            if "*" not in p and "?" not in p and "[" not in p
        ]
        is_single_level_glob = (
            len(dest_parts) == 1
            and len(non_glob_parts) == 1
            and include_pattern.endswith("/*.py")
            and not include_pattern.endswith("/*")
        )
        if is_single_level_glob:
            logger.trace(
                f"[DEST_INTERPRET] explicit dest override → {dest_path}",
            )
            return dest_path

        # For glob patterns, strip non-glob prefix
        prefix = get_glob_root(include_pattern)
        try:
            rel = file_path_resolved.relative_to(include_root_resolved / prefix)
            result = dest_path / rel
            logger.trace(
                f"[DEST_INTERPRET] glob include → prefix={prefix}, "
                f"rel={rel}, result={result}",
            )
            return result  # noqa: TRY300
        except ValueError:
            logger.trace("[DEST_INTERPRET] glob fallback (ValueError)")
            return dest_path / file_path.name

    # For literal includes, check if dest is a full path (ends with .py)
    # If so, use it directly; otherwise preserve structure relative to dest
    dest_str = str(dest_path)
    if dest_str.endswith(".py"):
        # Dest is a full path - use it directly
        logger.trace(
            f"[DEST_INTERPRET] literal include with full dest path → {dest_path}",
        )
        return dest_path

    # Dest is a directory prefix - preserve structure relative to dest
    try:
        rel = file_path_resolved.relative_to(include_root_resolved)
        result = dest_path / rel
        logger.trace(f"[DEST_INTERPRET] literal include → rel={rel}, result={result}")
        return result  # noqa: TRY300
    except ValueError:
        # Fallback when file_path isn't under include_root
        logger.trace(
            f"[DEST_INTERPRET] fallback (file not under root) → "
            f"using name={file_path.name}",
        )
        return dest_path / file_path.name


def derive_module_name(  # noqa: PLR0912, PLR0915, C901
    file_path: Path,
    package_root: Path,
    include: IncludeResolved | None = None,
    source_bases: list[str] | None = None,
    user_provided_source_bases: list[str] | None = None,
    detected_packages: set[str] | None = None,
) -> str:
    """Derive module name from file path for shim generation.

    Default behavior: Preserve directory structure from file path relative to
    package root. With dest: Preserve structure from dest path instead.
    With source_bases: For external files, derive relative to matching module_base.

    Args:
        file_path: The file path to derive module name from
        package_root: Common root of all included files
        include: Optional include that produced this file (for dest access)
        source_bases: Optional list of module base directories for external files
        user_provided_source_bases: Optional list of user-provided module bases
            (from config, excludes auto-discovered package directories)
        detected_packages: Optional set of detected package names for preserving
            package structure when module_base is a detected package

    Returns:
        Derived module name (e.g., "core.base" from "src/core/base.py")

    Raises:
        ValueError: If module name would be empty or invalid
    """
    logger = getAppLogger()
    file_path_resolved = file_path.resolve()
    package_root_resolved = package_root.resolve()

    # Check if include has dest override
    if include:
        validate_required_keys(include, {"path", "root"}, "include")
    if include and include.get("dest"):
        dest_raw = include.get("dest")
        # dest is Path | None, but we know it's truthy from the if check
        if dest_raw is None:
            # This shouldn't happen due to the if check, but satisfy type checker
            dest: Path | str = Path()
        else:
            dest = dest_raw  # dest_raw is Path here
        include_root = Path(include["root"]).resolve()
        include_pattern = str(include["path"])

        # Use _interpret_dest_for_module_name to get virtual destination path
        dest_path = _interpret_dest_for_module_name(
            file_path_resolved,
            include_root,
            include_pattern,
            dest,
        )

        # Convert dest path to module name, preserving directory structure
        # custom/sub/foo.py → custom.sub.foo
        parts = list(dest_path.parts)
        if parts and parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]  # Remove .py extension
        elif parts and parts[-1].endswith("/"):
            # Trailing slash means directory - use as-is but might need adjustment
            parts[-1] = parts[-1].rstrip("/")

        # Filter out empty parts and join
        parts = [p for p in parts if p]
        if not parts:
            xmsg = f"Cannot derive module name from dest path: {dest_path}"
            raise ValueError(xmsg)

        module_name = ".".join(parts)
        logger.trace(
            f"[DERIVE] file={file_path}, dest={dest} → module={module_name}",
        )
        return module_name

    # Check if file is under package_root
    package_root_rel: Path | None = None
    try:
        package_root_rel = file_path_resolved.relative_to(package_root_resolved)
        is_under_package_root = True
    except ValueError:
        is_under_package_root = False

    # Check source_bases if provided
    # If file is under both package_root and a module_base, prefer module_base
    # when it's more specific (deeper in the tree than package_root)
    # BUT: Don't use module_base if it's the file's parent directory
    # (would lose package name)
    # Use user_provided_source_bases for the fix (external files),
    # fall back to all source_bases for backward compatibility
    rel_path = None
    # Prefer user-provided source_bases (from config) over auto-discovered ones
    bases_to_use = (
        user_provided_source_bases if user_provided_source_bases else source_bases
    )
    if bases_to_use:
        file_parent = file_path_resolved.parent
        # Try each module_base in order (first match wins)
        for module_base_str in bases_to_use:
            module_base = Path(module_base_str).resolve()
            # Skip if module_base is the file's parent directory
            # (this would cause files in package dirs to lose their package name)
            if module_base == file_parent:
                logger.trace(
                    f"[DERIVE] file={file_path} parent={file_parent} equals "
                    f"module_base={module_base}, skipping (would lose package name)",
                )
                continue
            try:
                module_base_rel = file_path_resolved.relative_to(module_base)
                # Use module_base if:
                # 1. File is not under package_root, OR
                # 2. File is under both, but module_base is more specific (deeper)
                if not is_under_package_root:
                    rel_path = module_base_rel
                    logger.trace(
                        f"[DERIVE] file={file_path} not under root={package_root}, "
                        f"but under module_base={module_base}, using relative path",
                    )
                    break
                # Check if module_base is more specific (deeper) than package_root
                try:
                    module_base.relative_to(package_root_resolved)
                    # module_base is under package_root
                    # For files from installed_bases or external sources, prefer
                    # module_base even if not deeper (to get correct module names)
                    # Check if file is actually under this module_base
                    try:
                        file_path_resolved.relative_to(module_base)
                        # File is under module_base - use it for correct module name
                        rel_path = module_base_rel
                        # If module_base.name is a detected package AND it's not the
                        # package_root name, prepend it to preserve package structure
                        # (e.g., pkg1/sub/mod1.py -> pkg1.sub.mod1)
                        # But don't prepend if:
                        # 1. module_base is the package_root itself (double prefix)
                        # 2. module_base.name is a common directory name
                        #    (src, lib, site-packages)
                        # 3. The relative path already starts with module_base.name
                        should_prepend = False
                        if (
                            detected_packages
                            and module_base.name in detected_packages
                            and module_base.name != package_root_resolved.name
                        ):
                            # Don't prepend common directory names
                            common_dirs = {
                                "src",
                                "lib",
                                "site-packages",
                                "dist-packages",
                            }
                            if module_base.name not in common_dirs:
                                # Check if rel_path already starts with module_base.name
                                # (avoid double prefix like pkg1.pkg1.sub.mod1)
                                rel_parts = list(rel_path.parts)
                                if rel_parts:
                                    first_part = rel_parts[0]
                                    # Only prepend if first part is not module_base.name
                                    if first_part != module_base.name:
                                        should_prepend = True
                        if should_prepend:
                            # Prepend module_base.name to preserve package structure
                            rel_path = Path(module_base.name) / rel_path
                            logger.trace(
                                f"[DERIVE] file={file_path} under both "
                                f"root={package_root} and module_base={module_base}, "
                                f"using module_base (file is under module_base, "
                                f"prepending package {module_base.name})",
                            )
                        else:
                            logger.trace(
                                f"[DERIVE] file={file_path} under both "
                                f"root={package_root} and module_base={module_base}, "
                                f"using module_base (file is under module_base)",
                            )
                        break
                    except ValueError:
                        # File is not under this module_base, continue
                        pass
                    # module_base is at same level or higher, don't use it
                    # (preserve original behavior for files under package_root)
                except ValueError:
                    # module_base is not under package_root
                    # Only use it if file is also not under package_root
                    # (if file is under package_root, preserve original behavior)
                    if not is_under_package_root:
                        rel_path = module_base_rel
                        logger.trace(
                            f"[DERIVE] file={file_path} not under root={package_root}, "
                            f"but under module_base={module_base}, using module_base",
                        )
                        break
                    # File is under package_root but module_base is not
                    # Don't use module_base (preserve original behavior)
            except ValueError:
                # Not under this module_base, try next
                continue

    # If not using module_base, derive from file path relative to package root
    if rel_path is None:
        if is_under_package_root and package_root_rel is not None:
            rel_path = package_root_rel
            logger.trace(
                f"[DERIVE] file={file_path} under package_root={package_root}, "
                f"using relative path",
            )
        else:
            # File not under package root or any module_base - use just filename
            logger.trace(
                f"[DERIVE] file={file_path} not under root={package_root} "
                f"or any module_base, using filename",
            )
            rel_path = Path(file_path.name)

    # Convert path to module name, preserving directory structure
    # path/to/file.py → path.to.file
    parts = list(rel_path.parts)
    if parts and parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]  # Remove .py extension

    # Filter out empty parts
    parts = [p for p in parts if p]
    if not parts:
        xmsg = f"Cannot derive module name from file path: {file_path}"
        raise ValueError(xmsg)

    module_name = ".".join(parts)
    logger.trace(f"[DERIVE] file={file_path} → module={module_name}")
    return module_name
