# src/serger/utils.py


import json
import os
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import (
    Any,
    cast,
)

from .config_types import IncludeResolved, PathResolved
from .logs import get_logger


# --- types --------------------------------------------------------------------


@dataclass
class CapturedOutput:
    """Captured stdout, stderr, and merged streams."""

    stdout: StringIO
    stderr: StringIO
    merged: StringIO

    def __str__(self) -> str:
        """Human-friendly representation (merged output)."""
        return self.merged.getvalue()

    def as_dict(self) -> dict[str, str]:
        """Return contents as plain strings for serialization."""
        return {
            "stdout": self.stdout.getvalue(),
            "stderr": self.stderr.getvalue(),
            "merged": self.merged.getvalue(),
        }


# --- utils --------------------------------------------------------------------


def get_sys_version_info() -> tuple[int, int, int] | tuple[int, int, int, str, int]:
    return sys.version_info


def load_toml(path: Path, *, required: bool = False) -> dict[str, Any] | None:
    """Load and parse a TOML file, supporting Python 3.10 and 3.11+.

    Uses:
    - `tomllib` (Python 3.11+ standard library)
    - `tomli` (required for Python 3.10 - must be installed separately)

    Args:
        path: Path to TOML file
        required: If True, raise RuntimeError when tomli is missing on Python 3.10.
                  If False, return None when unavailable (caller handles gracefully).

    Returns:
        Parsed TOML data as a dictionary, or None if unavailable and not required

    Raises:
        FileNotFoundError: If the file doesn't exist
        RuntimeError: If required=True and neither tomllib nor tomli is available
        ValueError: If the file cannot be parsed
    """
    if not path.exists():
        xmsg = f"TOML file not found: {path}"
        raise FileNotFoundError(xmsg)

    # Try tomllib (Python 3.11+)
    try:
        import tomllib  # type: ignore[import-not-found] # noqa: PLC0415

        with path.open("rb") as f:
            return tomllib.load(f)  # type: ignore[no-any-return]
    except ImportError:
        pass

    # Try tomli (required for Python 3.10)
    try:
        import tomli  # type: ignore[import-not-found,unused-ignore] # noqa: PLC0415  # pyright: ignore[reportMissingImports]

        with path.open("rb") as f:
            return tomli.load(f)  # type: ignore[no-any-return,unused-ignore]  # pyright: ignore[reportUnknownReturnType]
    except ImportError:
        if required:
            xmsg = (
                "TOML parsing requires 'tomli' package on Python 3.10. "
                "Install it with: pip install tomli, or disable pyproject.toml support "
                "by setting 'use_pyproject: false' in your config."
            )
            raise RuntimeError(xmsg) from None
        return None


def is_running_under_pytest() -> bool:
    """Detect if code is running under pytest.

    Checks multiple indicators:
    - Environment variables set by pytest
    - Command-line arguments containing 'pytest'

    Returns:
        True if running under pytest, False otherwise
    """
    return (
        "pytest" in os.environ.get("_", "")
        or "PYTEST_CURRENT_TEST" in os.environ
        or any(
            "pytest" in arg
            for arg in sys.argv
            if isinstance(arg, str)  # pyright: ignore[reportUnnecessaryIsInstance]
        )
    )


def _strip_jsonc_comments(text: str) -> str:  # noqa: PLR0912
    """Strip comments from JSONC while preserving string contents.

    Handles //, #, and /* */ comments without modifying content inside strings.
    """
    result: list[str] = []
    in_string = False
    in_escape = False
    i = 0
    while i < len(text):
        ch = text[i]

        # Handle escape sequences in strings
        if in_escape:
            result.append(ch)
            in_escape = False
            i += 1
            continue

        if ch == "\\" and in_string:
            result.append(ch)
            in_escape = True
            i += 1
            continue

        # Toggle string state
        if ch in ('"', "'") and (not in_string or text[i - 1 : i] != "\\"):
            in_string = not in_string
            result.append(ch)
            i += 1
            continue

        # If in a string, keep everything
        if in_string:
            result.append(ch)
            i += 1
            continue

        # Outside strings: handle comments
        # Check for // comment (but skip URLs like http://)
        if (
            ch == "/"
            and i + 1 < len(text)
            and text[i + 1] == "/"
            and not (i > 0 and text[i - 1] == ":")
        ):
            # Skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                result.append("\n")
                i += 1
            continue

        # Check for # comment
        if ch == "#":
            # Skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                result.append("\n")
                i += 1
            continue

        # Check for block comments /* ... */
        if ch == "/" and i + 1 < len(text) and text[i + 1] == "*":
            # Skip to end of block comment
            i += 2
            while i + 1 < len(text):
                if text[i] == "*" and text[i + 1] == "/":
                    i += 2
                    break
                i += 1
            continue

        # Regular character
        result.append(ch)
        i += 1

    return "".join(result)


def load_jsonc(path: Path) -> dict[str, Any] | list[Any] | None:
    """Load JSONC (JSON with comments and trailing commas)."""
    logger = get_logger()
    logger.trace(f"[load_jsonc] Loading from {path}")

    if not path.exists():
        xmsg = f"JSONC file not found: {path}"
        raise FileNotFoundError(xmsg)

    if not path.is_file():
        xmsg = f"Expected a file: {path}"
        raise ValueError(xmsg)

    text = path.read_text(encoding="utf-8")
    text = _strip_jsonc_comments(text)

    # Remove trailing commas before } or ]
    text = re.sub(r",(?=\s*[}\]])", "", text)

    # Trim whitespace
    text = text.strip()

    if not text:
        # Empty or only comments → interpret as "no config"
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        xmsg = (
            f"Invalid JSONC syntax in {path}:"
            f" {e.msg} (line {e.lineno}, column {e.colno})"
        )
        raise ValueError(xmsg) from e

    # Guard against scalar roots (invalid config structure)
    if not isinstance(data, (dict, list)):
        xmsg = f"Invalid JSONC root type: {type(data).__name__}"
        raise ValueError(xmsg)  # noqa: TRY004

    # narrow type
    result = cast("dict[str, Any] | list[Any]", data)
    logger.trace(
        f"[load_jsonc] Loaded {type(result).__name__} with"
        f" {len(result) if hasattr(result, '__len__') else 'N/A'} items"
    )
    return result


def remove_path_in_error_message(inner_msg: str, path: Path) -> str:
    """Remove redundant file path mentions (and nearby filler)
    from error messages.

    Useful when wrapping a lower-level exception that already
    embeds its own file reference, so the higher-level message
    can use its own path without duplication.

    Example:
        "Invalid JSONC syntax in /abs/path/config.jsonc: Expecting value"
        → "Invalid JSONC syntax: Expecting value"

    """
    # Normalize both path and name for flexible matching
    full_path = str(path)
    filename = path.name

    # Common redundant phrases we might need to remove
    candidates = [
        f"in {full_path}",
        f"in '{full_path}'",
        f'in "{full_path}"',
        f"in {filename}",
        f"in '{filename}'",
        f'in "{filename}"',
        full_path,
        filename,
    ]

    clean_msg = inner_msg
    for pattern in candidates:
        clean_msg = clean_msg.replace(pattern, "").strip(": ").strip()

    # Normalize leftover spaces and colons
    clean_msg = re.sub(r"\s{2,}", " ", clean_msg)
    clean_msg = re.sub(r"\s*:\s*", ": ", clean_msg)

    return clean_msg


def plural(obj: Any) -> str:
    """Return 's' if obj represents a plural count.

    Accepts ints, floats, and any object implementing __len__().
    Returns '' for singular or zero.
    """
    count: int | float
    try:
        count = len(obj)
    except TypeError:
        # fallback for numbers or uncountable types
        count = obj if isinstance(obj, (int, float)) else 0
    return "s" if count != 1 else ""


@contextmanager
def capture_output() -> Iterator[CapturedOutput]:
    """Temporarily capture stdout and stderr.

    Any exception raised inside the block is re-raised with
    the captured output attached as `exc.captured_output`.

    Example:
    from serger.utils import capture_output
    from serger.cli import main

    with capture_output() as (out, err):
        exit_code = main(["--config", "my.cfg", "--dry-run"])

    result = {
        "exit_code": exit_code,
        "stdout": out.getvalue(),
        "stderr": err.getvalue(),
        "merged": merged.getvalue(),
    }

    """
    merged = StringIO()

    class TeeStream(StringIO):
        def write(self, s: str) -> int:
            merged.write(s)
            return super().write(s)

    buf_out, buf_err = TeeStream(), TeeStream()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err

    cap = CapturedOutput(stdout=buf_out, stderr=buf_err, merged=merged)
    try:
        yield cap
    except Exception as e:
        # Attach captured output to the raised exception for API introspection
        e.captured_output = cap  # type: ignore[attr-defined]
        raise
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def detect_runtime_mode() -> str:
    if getattr(sys, "frozen", False):
        return "frozen"
    if "__main__" in sys.modules and getattr(
        sys.modules["__main__"],
        __file__,
        "",
    ).endswith(".pyz"):
        return "zipapp"
    if "__STANDALONE__" in globals():
        return "standalone"
    return "installed"


def is_excluded(path_entry: PathResolved, exclude_patterns: list[PathResolved]) -> bool:
    """High-level helper for internal use.
    Accepts PathResolved entries and delegates to the smart matcher.
    """
    logger = get_logger()
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


def has_glob_chars(s: str) -> bool:
    return any(c in s for c in "*?[]")


def normalize_path_string(raw: str) -> str:
    r"""Normalize a user-supplied path string for cross-platform use.

    Industry-standard (Git/Node/Python) rules:
      - Treat both '/' and '\\' as valid separators and normalize all to '/'.
      - Replace escaped spaces ('\\ ') with real spaces.
      - Collapse redundant slashes (preserve protocol prefixes like 'file://').
      - Never resolve '.' or '..' or touch the filesystem.
      - Never raise for syntax; normalization is always possible.

    This is the pragmatic cross-platform normalization strategy used by
    Git, Node.js, and Python build tools.
    This function is purely lexical — it normalizes syntax, not filesystem state.
    """
    logger = get_logger()
    if not raw:
        return ""

    path = raw.strip()

    # Handle escaped spaces (common shell copy-paste)
    if "\\ " in path:
        fixed = path.replace("\\ ", " ")
        logger.warning("Normalizing escaped spaces in path: %r → %s", path, fixed)
        path = fixed

    # Normalize all backslashes to forward slashes
    path = path.replace("\\", "/")

    # Collapse redundant slashes (keep protocol //)
    collapsed_slashes = re.sub(r"(?<!:)//+", "/", path)
    if collapsed_slashes != path:
        logger.trace("Collapsed redundant slashes: %r → %r", path, collapsed_slashes)
        path = collapsed_slashes

    return path


def get_glob_root(pattern: str) -> Path:
    """Return the non-glob portion of a path like 'src/**/*.txt'.

    Normalizes paths to cross-platform.
    """
    if not pattern:
        return Path()

    # Normalize backslashes to forward slashes
    normalized = normalize_path_string(pattern)

    parts: list[str] = []
    for part in Path(normalized).parts:
        if re.search(r"[*?\[\]]", part):
            break
        parts.append(part)
    return Path(*parts) if parts else Path()


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
    logger = get_logger()
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
    logger = get_logger()
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


def code_porting_placeholder(msg: str, *, ret: bool = True) -> bool:
    """Used as a placeholder"""
    logger = get_logger()
    logger.trace("placeholder_functionality called: %s", msg)
    return ret
