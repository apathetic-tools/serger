# src/serger/utils/utils_paths.py


from pathlib import Path

from serger.config.config_types import IncludeResolved, PathResolved


def shorten_path_for_display(
    path: Path | str | PathResolved | IncludeResolved,
    *,
    cwd: Path | None = None,
    config_dir: Path | None = None,
) -> str:
    """Shorten an absolute path for display purposes.

    Tries to make the path relative to cwd first, then config_dir, and picks
    the shortest result. If neither works, returns the absolute path as a string.

    If path is a PathResolved or IncludeResolved, resolves exclusively against
    its built-in `root` field (ignoring cwd and config_dir).

    Args:
        path: Path to shorten (can be Path, str, PathResolved, or IncludeResolved)
        cwd: Current working directory (optional, ignored for PathResolved/
            IncludeResolved)
        config_dir: Config directory (optional, ignored for PathResolved/
            IncludeResolved)

    Returns:
        Shortened path string (relative when possible, absolute otherwise)
    """
    # Handle PathResolved or IncludeResolved types
    if isinstance(path, dict) and "root" in path:
        # PathResolved or IncludeResolved - resolve against its root exclusively
        root = Path(path["root"]).resolve()
        path_val = path["path"]
        # Resolve path relative to root
        path_obj = (root / path_val).resolve()
        # Try to make relative to root
        try:
            rel_to_root = str(path_obj.relative_to(root))
        except ValueError:
            # Not relative to root, return absolute
            return str(path_obj)
        else:
            if rel_to_root:
                return rel_to_root
            return "."

    # Handle regular Path or str
    path_obj = Path(path).resolve()

    candidates: list[str] = []

    # Try relative to cwd
    if cwd:
        cwd_resolved = Path(cwd).resolve()
        try:
            rel_to_cwd = str(path_obj.relative_to(cwd_resolved))
            candidates.append(rel_to_cwd)
        except ValueError:
            pass

    # Try relative to config_dir
    if config_dir:
        config_dir_resolved = Path(config_dir).resolve()
        try:
            rel_to_config = str(path_obj.relative_to(config_dir_resolved))
            candidates.append(rel_to_config)
        except ValueError:
            pass

    # If we have candidates, pick the shortest one
    if candidates:
        return min(candidates, key=len)

    # Fall back to absolute path
    return str(path_obj)


def shorten_paths_for_display(
    paths: (
        list[Path]
        | list[str]
        | list[PathResolved]
        | list[IncludeResolved]
        | list[Path | str | PathResolved | IncludeResolved]
    ),
    *,
    cwd: Path | None = None,
    config_dir: Path | None = None,
) -> list[str]:
    """Shorten a list of paths for display purposes.

    Applies shorten_path_for_display to each path in the list. Can handle
    mixed types (Path, str, PathResolved, IncludeResolved).

    Args:
        paths: List of paths to shorten (can be Path, str, PathResolved, or
            IncludeResolved, or a mix)
        cwd: Current working directory (optional, ignored for PathResolved/
            IncludeResolved)
        config_dir: Config directory (optional, ignored for PathResolved/
            IncludeResolved)

    Returns:
        List of shortened path strings
    """
    return [
        shorten_path_for_display(path, cwd=cwd, config_dir=config_dir) for path in paths
    ]
