# src/serger/actions.py
import re
import subprocess
import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path

from apathetic_utils import load_toml

from .build import collect_included_files
from .config import RootConfigResolved
from .constants import DEFAULT_WATCH_INTERVAL
from .logs import getAppLogger
from .meta import Metadata
from .utils.utils_validation import validate_required_keys


def _collect_included_files(resolved: RootConfigResolved) -> list[Path]:
    """Collect all include globs into a unique list of files.

    Uses collect_included_files() from build.py for consistency.
    Watch mode respects excludes from config.
    """
    # include and exclude are optional, but if present they need validation
    # Validation happens inside collect_included_files
    includes = resolved.get("include", [])
    excludes = resolved.get("exclude", [])
    # Collect files (watch mode respects excludes from config)
    files, _file_to_include = collect_included_files(includes, excludes)

    # Return unique sorted list
    return sorted(set(files))


def watch_for_changes(
    rebuild_func: Callable[[], None],
    resolved: RootConfigResolved,
    interval: float = DEFAULT_WATCH_INTERVAL,
) -> None:
    """Poll file modification times and rebuild when changes are detected.

    Features:
    - Skips files inside the build's output directory.
    - Re-expands include patterns every loop to detect newly created files.
    - Polling interval defaults to 1 second (tune 0.5–2.0 for balance).
    Stops on KeyboardInterrupt.
    """
    logger = getAppLogger()
    logger.info(
        "👀 Watching for changes (interval=%.2fs)... Press Ctrl+C to stop.", interval
    )

    # discover at start
    included_files = _collect_included_files(resolved)

    mtimes: dict[Path, float] = {
        f: f.stat().st_mtime for f in included_files if f.exists()
    }

    # Collect output path to ignore (can be directory or file)
    validate_required_keys(resolved, {"out"}, "resolved config")
    validate_required_keys(resolved["out"], {"path", "root"}, "resolved['out']")
    out_path = (resolved["out"]["root"] / resolved["out"]["path"]).resolve()

    rebuild_func()  # initial build

    try:
        while True:
            time.sleep(interval)

            # 🔁 re-expand every tick so new/removed files are tracked
            included_files = _collect_included_files(resolved)

            logger.trace(f"[watch] Checking {len(included_files)} files for changes")

            changed: list[Path] = []
            for f in included_files:
                # skip files that are inside or equal to the output path
                if f == out_path or f.is_relative_to(out_path):
                    continue  # ignore output files/folders
                old_m = mtimes.get(f)
                if not f.exists():
                    if old_m is not None:
                        changed.append(f)
                        mtimes.pop(f, None)
                    continue
                new_m = f.stat().st_mtime
                if old_m is None or new_m > old_m:
                    changed.append(f)
                    mtimes[f] = new_m

            if changed:
                logger.info(
                    "\n🔁 Detected %d modified file(s). Rebuilding...", len(changed)
                )
                rebuild_func()
                # refresh timestamps after rebuild
                mtimes = {f: f.stat().st_mtime for f in included_files if f.exists()}
    except KeyboardInterrupt:
        logger.info("\n🛑 Watch stopped.")


def _get_metadata_from_header(script_path: Path) -> tuple[str, str]:
    """Extract version and commit from stitched script.

    Prefers in-file constants (__version__, __commit__) if present;
    falls back to commented header tags.
    """
    logger = getAppLogger()
    version = "unknown"
    commit = "unknown"

    logger.trace("reading commit from header: %s", script_path)

    with suppress(Exception):
        text = script_path.read_text(encoding="utf-8")

        # --- Prefer Python constants if defined ---
        const_version = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
        const_commit = re.search(r"__commit__\s*=\s*['\"]([^'\"]+)['\"]", text)
        if const_version:
            version = const_version.group(1)
        if const_commit:
            commit = const_commit.group(1)

        # --- Fallback: header lines ---
        if version == "unknown" or commit == "unknown":
            for line in text.splitlines():
                if line.startswith("# Version:") and version == "unknown":
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("# Commit:") and commit == "unknown":
                    commit = line.split(":", 1)[1].strip()

    return version, commit


def get_metadata() -> Metadata:
    """Return (version, commit) tuple for this tool.

    - Stitched script → parse from header
    - Source package → read pyproject.toml + git
    """
    script_path = Path(__file__)
    logger = getAppLogger()
    logger.trace("get_metadata ran from: %s", Path(__file__).resolve())

    # --- Heuristic: stitched script lives outside `src/` ---
    if globals().get("__STITCHED__", False):
        version, commit = _get_metadata_from_header(script_path)
        logger.trace(f"got stitched version {version} with commit {commit}")
        return Metadata(version, commit)

    # --- Modular / source package case ---

    # Source package case
    version = "unknown"
    commit = "unknown"

    # Try pyproject.toml for version
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        logger.trace(f"trying to read metadata from {pyproject}")
        data = load_toml(pyproject, required=False)
        if data:
            project = data.get("project", {})
            version = project.get("version", "unknown")
            if version != "unknown":
                logger.trace(f"extracted version from pyproject.toml: {version}")

    # Try git for commit
    with suppress(Exception):
        logger.trace("trying to get commit from git")
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()

    logger.trace(f"got package version {version} with commit {commit}")
    return Metadata(version, commit)
