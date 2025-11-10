"""Stitching logic for combining multiple Python modules into a single file.

This module handles the core functionality for stitching together modular
Python source files into a single executable script. It includes utilities for
import handling, code analysis, and assembly.
"""

import ast
import graphlib
import importlib
import os
import py_compile
import re
import subprocess
from pathlib import Path

from .logs import get_logger


def extract_version(pyproject_path: Path) -> str:
    """Extract version string from pyproject.toml.

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Version string, or "unknown" if not found
    """
    if not pyproject_path.exists():
        return "unknown"
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^\s*version\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else "unknown"


def extract_commit(root_path: Path) -> str:
    """Extract git commit hash.

    Only embeds commit hash if in CI or release tag context.

    Args:
        root_path: Project root directory

    Returns:
        Short commit hash, or "unknown (local build)" if not in CI
    """
    logger = get_logger()
    # Only embed commit hash if in CI or release tag context
    if not (os.getenv("CI") or os.getenv("GIT_TAG") or os.getenv("GITHUB_REF")):
        return "unknown (local build)"
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=root_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        logger.warning("git rev-parse failed: %s", e.stderr.strip())
    except FileNotFoundError:
        logger.warning("git not available in environment")

    return "unknown"


def split_imports(
    text: str,
    package_name: str,
) -> tuple[list[str], str]:
    """Extract external imports and body text using AST.

    Separates internal package imports from external imports, removing all
    imports from the function body (they'll be collected and deduplicated).

    Args:
        text: Python source code
        package_name: Root package name (e.g., "serger")

    Returns:
        Tuple of (external_imports, body_text) where external_imports is a
        list of import statement strings, and body_text is the source with
        all imports removed
    """
    logger = get_logger()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        logger.exception("Failed to parse file")
        return [], text

    lines = text.splitlines(keepends=True)
    external_imports: list[str] = []
    all_import_ranges: list[tuple[int, int]] = []

    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue

        start = node.lineno - 1
        end = getattr(node, "end_lineno", node.lineno)
        snippet = "".join(lines[start:end])

        # --- Determine whether it's internal ---
        is_internal = False
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level > 0 or mod.startswith(package_name):
                is_internal = True
        elif any(alias.name.startswith(package_name) for alias in node.names):
            is_internal = True

        # Always skip import lines from body, internal or not
        all_import_ranges.append((start, end))

        # Only keep non-internal imports for the top section
        if not is_internal:
            external_imports.append(snippet)

    # --- Remove *all* import lines from the body ---
    skip = {i for s, e in all_import_ranges for i in range(s, e)}
    body = "".join(line for i, line in enumerate(lines) if i not in skip)

    return external_imports, body


def strip_redundant_blocks(text: str) -> str:
    """Remove shebangs and __main__ guards from module code.

    Args:
        text: Python source code

    Returns:
        Source code with shebangs and __main__ blocks removed
    """
    text = re.sub(r"^#!.*\n", "", text)
    text = re.sub(
        r"(?s)\n?if\s+__name__\s*==\s*[\"']__main__[\"']\s*:\s*\n.*?$",
        "",
        text,
    )

    return text.strip()


def verify_compiles(path: Path) -> None:
    """Ensure the generated script compiles cleanly.

    Args:
        path: Path to generated Python script

    Raises:
        RuntimeError: If compilation fails
    """
    try:
        py_compile.compile(str(path), doraise=True)
        logger = get_logger()
        logger.info("Compiled successfully.")
    except py_compile.PyCompileError as e:
        msg = f"Syntax error in generated script: {e.msg}"
        raise RuntimeError(msg) from e


def detect_name_collisions(sources: dict[str, str]) -> None:
    """Detect top-level name collisions across modules.

    Checks for functions, classes, and simple assignments that would
    conflict when stitched together.

    Args:
        sources: Dict mapping module names to their source code

    Raises:
        RuntimeError: If collisions are detected
    """
    # list of harmless globals we don't mind having overwritten
    ignore = {
        "__all__",
        "__version__",
        "__author__",
        "__path__",
        "__package__",
        "__commit__",
    }

    symbols: dict[str, str] = {}  # name -> module
    collisions: list[tuple[str, str, str]] = []

    for mod, text in sources.items():
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                name = node.name
            elif isinstance(node, ast.Assign):
                # only consider simple names like x = ...
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if not targets:
                    continue
                name = targets[0]
            else:
                continue

            # skip known harmless globals
            if name in ignore:
                continue

            prev = symbols.get(name)
            if prev:
                collisions.append((name, prev, mod))
            else:
                symbols[name] = mod

    if collisions:
        collision_list = ", ".join(f"{name!r}" for name, _, _ in collisions)
        msg = f"Top-level name collisions detected: {collision_list}"
        raise RuntimeError(msg)


def verify_all_modules_listed(
    src_dir: Path, order_names: list[str], exclude_names: list[str]
) -> None:
    """Ensure all .py files in src_dir are listed in order or exclude names.

    Args:
        src_dir: Source directory containing modules
        order_names: List of module names to stitch
        exclude_names: List of module names to exclude

    Raises:
        RuntimeError: If unlisted files are found
    """
    all_files = sorted(
        p.name for p in src_dir.glob("*.py") if not p.name.startswith("__")
    )

    order_files = [f"{n}.py" for n in order_names]
    exclude_files = [f"{n}.py" for n in exclude_names]
    known = set(order_files + exclude_files)
    unknown = [f for f in all_files if f not in known]

    if unknown:
        unknown_list = ", ".join(unknown)
        msg = f"Unlisted source files detected: {unknown_list}"
        raise RuntimeError(msg)


def compute_module_order(
    src_dir: Path, order_names: list[str], package_name: str
) -> list[str]:
    """Compute correct module order based on import dependencies.

    Uses topological sorting of internal imports to determine the correct
    order for stitching.

    Args:
        src_dir: Source directory containing modules
        order_names: Initial/desired module order
        package_name: Root package name

    Returns:
        Topologically sorted list of module names

    Raises:
        RuntimeError: If circular imports are detected
    """
    deps: dict[str, set[str]] = {name: set() for name in order_names}

    for name in order_names:
        path = src_dir / f"{name}.py"
        if not path.exists():
            continue

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(package_name):
                    dep = mod.split(".")[-1]
                    if dep in deps and dep != name:
                        deps[name].add(dep)

    # detect circular imports first
    try:
        sorter = graphlib.TopologicalSorter(deps)
        topo = list(sorter.static_order())
    except graphlib.CycleError as e:
        msg = f"Circular dependency detected: {e.args[1] if e.args else 'unknown'}"
        raise RuntimeError(msg) from e

    return topo


def suggest_order_mismatch(
    order_names: list[str], package_name: str, src_dir: Path
) -> None:
    """Warn if module order violates dependencies.

    Args:
        order_names: List of module names in intended order
        package_name: Root package name
        src_dir: Source directory containing modules
    """
    logger = get_logger()
    topo = compute_module_order(src_dir, order_names, package_name)

    # compare order_names to topological sort
    mismatched = [
        n for n in order_names if n in topo and topo.index(n) != order_names.index(n)
    ]
    if mismatched:
        logger.warning("Possible module misordering detected:")
        for n in mismatched:
            logger.warning("  - %s appears before one of its dependencies", n)
        logger.warning("Suggested order: %s", ", ".join(topo))


def verify_no_broken_imports(final_text: str, package_name: str) -> None:
    """Verify all internal imports have been resolved in stitched script.

    Args:
        final_text: Final stitched script text
        package_name: Root package name

    Raises:
        RuntimeError: If unresolved imports remain
    """
    pattern = re.compile(rf"\bimport {package_name}\.(\w+)")
    broken = {
        m.group(1)
        for m in pattern.finditer(final_text)
        if f"# === {m.group(1)}.py ===" not in final_text
    }
    if broken:
        broken_list = ", ".join(f"{package_name}.{mod}" for mod in sorted(broken))
        msg = f"Unresolved internal imports: {broken_list}"
        raise RuntimeError(msg)


def force_mtime_advance(path: Path, seconds: float = 1.0, max_tries: int = 50) -> None:
    """Reliably bump a file's mtime, preserving atime and nanosecond precision.

    Ensures the change is visible before returning, even on lazy filesystems.
    We often can't use os.sleep or time.sleep because we monkeypatch it.

    Args:
        path: Path to file whose mtime to advance
        seconds: How many seconds to advance mtime
        max_tries: Maximum number of attempts

    Raises:
        AssertionError: If mtime could not be advanced after max_tries
    """
    real_time = importlib.import_module("time")  # immune to monkeypatch
    old_m = path.stat().st_mtime_ns
    ns_bump = int(seconds * 1_000_000_000)
    new_m: int = old_m

    for _attempt in range(max_tries):
        st = path.stat()
        os.utime(path, ns=(int(st.st_atime_ns), int(st.st_mtime_ns + ns_bump)))
        os.sync()  # flush kernel metadata

        new_m = path.stat().st_mtime_ns
        if new_m > old_m:
            return  # ✅ success
        real_time.sleep(0.00001)  # 10 µs pause before recheck

    xmsg = (
        f"bump_mtime({path}) failed to advance mtime after {max_tries} attempts "
        f"(old={old_m}, new={new_m})",
    )
    raise AssertionError(xmsg)
