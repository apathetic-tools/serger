# src/serger/utils/utils_types.py


from pathlib import Path
from typing import (
    cast,
)

from serger.config.config_types import IncludeResolved, OriginType, PathResolved


def _root_resolved(
    path: Path | str,
    root: Path | str,
    pattern: str | None,
    origin: OriginType,
) -> dict[str, object]:
    # Preserve raw string if available (to keep trailing slashes)
    raw_path = path if isinstance(path, str) else str(path)
    result: dict[str, object] = {
        "path": raw_path,
        "root": Path(root).resolve(),
        "origin": origin,
    }
    if pattern is not None:
        result["pattern"] = pattern
    return result


def make_pathresolved(
    path: Path | str,
    root: Path | str = ".",
    origin: OriginType = "code",
    *,
    pattern: str | None = None,
) -> PathResolved:
    """Quick helper to build a PathResolved entry."""
    # mutate class type
    return cast("PathResolved", _root_resolved(path, root, pattern, origin))


def make_includeresolved(
    path: Path | str,
    root: Path | str = ".",
    origin: OriginType = "code",
    *,
    pattern: str | None = None,
    dest: Path | str | None = None,
) -> IncludeResolved:
    """Create an IncludeResolved entry with optional dest override."""
    entry = _root_resolved(path, root, pattern, origin)
    if dest is not None:
        entry["dest"] = Path(dest)
    # mutate class type
    return cast("IncludeResolved", entry)
