# src/serger/utils/utils_files.py


import json
import re
from pathlib import Path
from typing import Any, cast

from apathetic_logs.logs import get_logger


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
                "by setting 'use_pyproject_metadata: false' in your config."
            )
            raise RuntimeError(xmsg) from None
        return None


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
