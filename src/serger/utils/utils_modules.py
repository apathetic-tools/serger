# src/serger/utils/utils_modules.py


import re
from pathlib import Path

from apathetic_utils import has_glob_chars
from serger.config.config_types import IncludeResolved
from serger.logs import get_app_logger


def _non_glob_prefix(pattern: str) -> Path:
    """Return the non-glob leading portion of a pattern, as a Path."""
    parts: list[str] = []
    for part in Path(pattern).parts:
        if re.search(r"[*?\[\]]", part):
            break
        parts.append(part)
    return Path(*parts)


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
    logger = get_app_logger()
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
        prefix = _non_glob_prefix(include_pattern)
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


def derive_module_name(
    file_path: Path,
    package_root: Path,
    include: IncludeResolved | None = None,
) -> str:
    """Derive module name from file path for shim generation.

    Default behavior: Preserve directory structure from file path relative to
    package root. With dest: Preserve structure from dest path instead.

    Args:
        file_path: The file path to derive module name from
        package_root: Common root of all included files
        include: Optional include that produced this file (for dest access)

    Returns:
        Derived module name (e.g., "core.base" from "src/core/base.py")

    Raises:
        ValueError: If module name would be empty or invalid
    """
    logger = get_app_logger()
    file_path_resolved = file_path.resolve()
    package_root_resolved = package_root.resolve()

    # Check if include has dest override
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

    # Default: derive from file path relative to package root, preserving structure
    try:
        rel_path = file_path_resolved.relative_to(package_root_resolved)
    except ValueError:
        # File not under package root - use just filename
        logger.trace(
            f"[DERIVE] file={file_path} not under root={package_root}, using filename",
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
