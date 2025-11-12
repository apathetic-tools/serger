# src/serger/utils/utils_matching.py


import re
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path

from serger.config_types import PathResolved
from serger.logs import get_app_logger

from .utils_system import get_sys_version_info


@lru_cache(maxsize=512)
def _compile_glob_recursive(pattern: str) -> re.Pattern[str]:
    """
    Compile a glob pattern to regex, backporting recursive '**' on Python < 3.11.
    This translator handles literals, ?, *, **, and [] classes without relying on
    slicing fnmatch.translate() output, avoiding unbalanced parentheses.
    Always case-sensitive.
    """

    def _escape_lit(ch: str) -> str:
        # Escape regex metacharacters
        if ch in ".^$+{}[]|()\\":
            return "\\" + ch
        return ch

    i = 0
    n = len(pattern)
    pieces: list[str] = []
    while i < n:
        ch = pattern[i]

        # Character class: copy through closing ']'
        if ch == "[":
            j = i + 1
            if j < n and pattern[j] in "!^":
                j += 1
            # allow leading ']' inside class as a literal
            if j < n and pattern[j] == "]":
                j += 1
            while j < n and pattern[j] != "]":
                j += 1
            if j < n and pattern[j] == "]":
                # whole class, keep as-is (regex already)
                pieces.append(pattern[i : j + 1])
                i = j + 1
            else:
                # unmatched '[', treat literally
                pieces.append("\\[")
                i += 1
            continue

        # Recursive glob
        if ch == "*" and i + 1 < n and pattern[i + 1] == "*":
            # Collapse a run of consecutive '*' to detect '**'
            k = i + 2
            while k < n and pattern[k] == "*":
                k += 1
            # Treat any run >= 2 as recursive
            pieces.append(".*")
            i = k
            continue

        # Single-segment glob
        if ch == "*":
            pieces.append("[^/]*")
            i += 1
            continue

        # Single character
        if ch == "?":
            pieces.append("[^/]")
            i += 1
            continue

        # Path separator or literal
        pieces.append(_escape_lit(ch))
        i += 1

    inner = "".join(pieces)
    return re.compile(f"(?s:{inner})\\Z")


def fnmatchcase_portable(path: str, pattern: str) -> bool:
    """
    Case-sensitive glob pattern matching with Python 3.10 '**' backport.

    Uses fnmatchcase (case-sensitive) as the base, with backported support
    for recursive '**' patterns on Python 3.10.

    Args:
        path: The path to match against the pattern
        pattern: The glob pattern to match

    Returns:
        True if the path matches the pattern, False otherwise.
    """
    if get_sys_version_info() >= (3, 11) or "**" not in pattern:
        return fnmatchcase(path, pattern)
    return bool(_compile_glob_recursive(pattern).match(path))


def is_excluded_raw(  # noqa: PLR0911
    path: Path | str,
    exclude_patterns: list[str],
    root: Path | str,
) -> bool:
    """Smart matcher for normalized inputs.

    - Treats 'path' as relative to 'root' unless already absolute.
    - If 'root' is a file, match directly.
    - Handles absolute or relative glob patterns.

    Note:
    The function does not require `root` to exist; if it does not,
    a debug message is logged and matching is purely path-based.
    """
    logger = get_app_logger()
    root = Path(root).resolve()
    path = Path(path)

    logger.trace(
        f"[is_excluded_raw] Checking path={path} against"
        f" {len(exclude_patterns)} patterns"
    )

    # the callee really should deal with this, otherwise we might spam
    if not Path(root).exists():
        logger.debug("Exclusion root does not exist: %s", root)

    # If the root itself is a file, treat that as a direct exclusion target.
    if root.is_file():
        # If the given path resolves exactly to that file, exclude it.
        full_path = path if path.is_absolute() else (root.parent / path)
        return full_path.resolve() == root.resolve()

    # If no exclude patterns, nothing else to exclude
    if not exclude_patterns:
        return False

    # Otherwise, treat as directory root.
    full_path = path if path.is_absolute() else (root / path)

    try:
        rel = str(full_path.relative_to(root)).replace("\\", "/")
    except ValueError:
        # Path lies outside the root; skip matching
        return False

    for pattern in exclude_patterns:
        pat = pattern.replace("\\", "/")

        logger.trace(f"[is_excluded_raw] Testing pattern {pattern!r} against {rel}")

        # If pattern is absolute and under root, adjust to relative form
        if pat.startswith(str(root)):
            try:
                pat_rel = str(Path(pat).relative_to(root)).replace("\\", "/")
            except ValueError:
                pat_rel = pat  # not under root; treat as-is
            if fnmatchcase_portable(rel, pat_rel):
                logger.trace(f"[is_excluded_raw] MATCHED pattern {pattern!r}")
                return True

        # Otherwise treat pattern as relative glob
        if fnmatchcase_portable(rel, pat):
            logger.trace(f"[is_excluded_raw] MATCHED pattern {pattern!r}")
            return True

        # Optional directory-only semantics
        if pat.endswith("/") and rel.startswith(pat.rstrip("/") + "/"):
            logger.trace(f"[is_excluded_raw] MATCHED pattern {pattern!r}")
            return True

    return False


def is_excluded(path_entry: PathResolved, exclude_patterns: list[PathResolved]) -> bool:
    """High-level helper for internal use.
    Accepts PathResolved entries and delegates to the smart matcher.
    """
    logger = get_app_logger()
    path = path_entry["path"]
    root = path_entry["root"]
    # Patterns are always normalized to PathResolved["path"] under config_resolve
    patterns = [str(e["path"]) for e in exclude_patterns]
    result = is_excluded_raw(path, patterns, root)
    logger.trace(
        f"[is_excluded] path={path}, root={root},"
        f" patterns={len(patterns)}, excluded={result}"
    )
    return result
