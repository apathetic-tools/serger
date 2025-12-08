# src/serger/utils/utils_paths.py


from pathlib import Path

from apathetic_utils import shorten_path

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
    # Collect non-None bases
    bases: list[str | Path] = []
    if cwd:
        bases.append(cwd)
    if config_dir:
        bases.append(config_dir)

    # Use apathetic_utils.shorten_path - it already returns absolute path
    # when path is not under any base (common_len <= 1)
    if bases:
        return shorten_path(path, bases)
    # No bases provided, return absolute path
    return str(Path(path).resolve())


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
