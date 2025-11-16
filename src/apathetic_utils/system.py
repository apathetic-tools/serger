# src/serger/utils/utils_system.py


import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import StringIO


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


# --- system utilities --------------------------------------------------------


def get_sys_version_info() -> tuple[int, int, int] | tuple[int, int, int, str, int]:
    return sys.version_info


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


def detect_runtime_mode() -> str:  # noqa: PLR0911
    if getattr(sys, "frozen", False):
        return "frozen"
    if "__main__" in sys.modules and getattr(
        sys.modules["__main__"],
        __file__,
        "",
    ).endswith(".pyz"):
        return "zipapp"
    # Check for standalone mode in multiple locations
    # 1. Current module's globals (for when called from within standalone script)
    if "__STANDALONE__" in globals():
        return "standalone"
    # 2. Check package module's globals (when loaded via importlib)
    # The standalone script is loaded as the "serger" package
    pkg_mod = sys.modules.get("serger")
    if pkg_mod is not None and hasattr(pkg_mod, "__STANDALONE__"):
        return "standalone"
    # 3. Check __main__ module's globals (for script execution)
    if "__main__" in sys.modules:
        main_mod = sys.modules["__main__"]
        if hasattr(main_mod, "__STANDALONE__"):
            return "standalone"
    return "installed"


@contextmanager
def capture_output() -> Iterator[CapturedOutput]:
    """Temporarily capture stdout and stderr.

    Any exception raised inside the block is re-raised with
    the captured output attached as `exc.captured_output`.

    Example:
    from serger.utils import capture_output
    from serger.cli import main

    with capture_output() as cap:
        exit_code = main(["--config", "my.cfg", "--dry-run"])

    result = {
        "exit_code": exit_code,
        "stdout": cap.stdout.getvalue(),
        "stderr": cap.stderr.getvalue(),
        "merged": cap.merged.getvalue(),
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
