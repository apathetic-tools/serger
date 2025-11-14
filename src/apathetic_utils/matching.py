# src/serger/utils/utils_matching.py


import re
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path

from apathetic_logs import get_logger

from .system import get_sys_version_info


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


def is_excluded_raw(  # noqa: PLR0911, PLR0912, PLR0915, C901
    path: Path | str,
    exclude_patterns: list[str],
    root: Path | str,
) -> bool:
    """Smart matcher for normalized inputs.

    - Treats 'path' as relative to 'root' unless already absolute.
    - If 'root' is a file, match directly.
    - Handles absolute or relative glob patterns.

    Special behavior for patterns with '../':
    Unlike rsync/ruff (which don't support '../' in exclude patterns),
    serger allows patterns with '../' to explicitly match files outside
    the exclude root. This enables config files in subdirectories to
    exclude files elsewhere in the project. Patterns containing '../'
    are resolved relative to the exclude root, then matched against
    the absolute file path.

    Note:
    The function does not require `root` to exist; if it does not,
    a debug message is logged and matching is purely path-based.
    """
    logger = get_logger()
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
    full_path = full_path.resolve()

    # Try to get relative path for standard matching
    try:
        rel = str(full_path.relative_to(root)).replace("\\", "/")
        path_outside_root = False
    except ValueError:
        # Path lies outside the root
        path_outside_root = True
        # For patterns starting with **/, we can still match against filename
        # or absolute path. For other patterns, we need rel, so use empty string
        # as fallback (won't match non-**/ patterns)
        rel = ""

    for pattern in exclude_patterns:
        pat = pattern.replace("\\", "/")

        # Handle patterns starting with **/ - these should match even for files
        # outside the exclude root (matching rsync/ruff behavior)
        if pat.startswith("**/"):
            # For **/ patterns, match against:
            # 1. The file's name (e.g., **/__init__.py matches any __init__.py)
            # 2. The absolute path (for more complex patterns)
            file_name = full_path.name
            abs_path_str = str(full_path).replace("\\", "/")

            # Remove **/ prefix and match against filename
            pattern_suffix = pat[3:]  # Remove "**/" prefix
            if fnmatchcase_portable(file_name, pattern_suffix):
                logger.trace(
                    f"[is_excluded_raw] MATCHED **/ pattern {pattern!r} "
                    f"against filename {file_name}"
                )
                return True

            # Also try matching against absolute path
            # (for patterns like **/subdir/file.py)
            if fnmatchcase_portable(abs_path_str, pat):
                logger.trace(
                    f"[is_excluded_raw] MATCHED **/ pattern {pattern!r} "
                    f"against absolute path"
                )
                return True

            # Continue to next pattern if we're outside root and **/ didn't match
            if path_outside_root:
                continue

        # Handle patterns with ../ - serger-specific behavior to allow
        # patterns that explicitly navigate outside the exclude root
        if "../" in pat or pat.startswith("../"):
            # Resolve the pattern relative to the exclude root
            # We need to handle glob patterns (with **) by resolving the base
            # path and preserving the glob part
            try:
                abs_path_str = str(full_path).replace("\\", "/")

                # If pattern contains glob chars, split and resolve carefully
                if "*" in pat or "?" in pat or "[" in pat:
                    # Find the first glob character to split base from pattern
                    glob_chars = ["*", "?", "["]
                    first_glob_pos = min(
                        (pat.find(c) for c in glob_chars if c in pat),
                        default=len(pat),
                    )

                    # Split into base path (before glob) and pattern part
                    base_part = pat[:first_glob_pos].rstrip("/")
                    pattern_part = pat[first_glob_pos:]

                    # Resolve the base part relative to root
                    if base_part:
                        resolved_base = (root / base_part).resolve()
                        resolved_pattern_str = (
                            str(resolved_base).replace("\\", "/") + "/" + pattern_part
                        )
                    else:
                        # Pattern starts with glob, resolve root and prepend pattern
                        resolved_pattern_str = (
                            str(root).replace("\\", "/") + "/" + pattern_part
                        )
                else:
                    # No glob chars, resolve normally
                    resolved_pattern = (root / pat).resolve()
                    resolved_pattern_str = str(resolved_pattern).replace("\\", "/")

                # Match the resolved pattern against the absolute file path
                if fnmatchcase_portable(abs_path_str, resolved_pattern_str):
                    logger.trace(
                        f"[is_excluded_raw] MATCHED ../ pattern {pattern!r} "
                        f"(resolved to {resolved_pattern_str})"
                    )
                    return True
            except (ValueError, RuntimeError):
                # Pattern resolves outside filesystem or invalid, skip
                logger.trace(
                    f"[is_excluded_raw] Could not resolve ../ pattern {pattern!r}"
                )

        # If path is outside root and pattern doesn't start with **/ or
        # contain ../, skip
        if path_outside_root:
            continue

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
