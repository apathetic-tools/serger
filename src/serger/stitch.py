# src/serger/stitch.py
"""Stitching logic for combining multiple Python modules into a single file.

This module handles the core functionality for stitching together modular
Python source files into a single executable script. It includes utilities for
import handling, code analysis, and assembly.
"""

import ast
import graphlib
import importlib
import json
import os
import re
import subprocess
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .logs import get_logger
from .meta import PROGRAM_PACKAGE
from .utils import is_running_under_pytest, load_toml
from .verify_script import post_stitch_processing


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


@dataclass
class PyprojectMetadata:
    """Metadata extracted from pyproject.toml."""

    name: str = ""
    version: str = ""
    description: str = ""
    license_text: str = ""

    def has_any(self) -> bool:
        """Check if any metadata was found."""
        return bool(self.name or self.version or self.description or self.license_text)


def extract_pyproject_metadata(
    pyproject_path: Path, *, required: bool = False
) -> PyprojectMetadata | None:
    """Extract metadata from pyproject.toml file.

    Extracts name, version, description, and license from the [project] section.
    Uses load_toml() utility which supports Python 3.10 and 3.11+.

    Args:
        pyproject_path: Path to pyproject.toml file
        required: If True, raise RuntimeError when tomli is missing on Python 3.10.
                  If False, return None when unavailable.

    Returns:
        PyprojectMetadata with extracted fields (empty strings if not found),
        or None if unavailable

    Raises:
        RuntimeError: If required=True and TOML parsing is unavailable
    """
    if not pyproject_path.exists():
        return PyprojectMetadata()

    try:
        data = load_toml(pyproject_path, required=required)
        if data is None:
            # TOML parsing unavailable and not required
            return None
        project = data.get("project", {})
    except (FileNotFoundError, ValueError):
        # If parsing fails, return empty metadata
        return PyprojectMetadata()

    # Extract fields from parsed TOML
    name = project.get("name", "")
    version = project.get("version", "")
    description = project.get("description", "")

    # Handle license (can be string or dict with "file" key)
    license_text = ""
    license_val = project.get("license")
    if isinstance(license_val, str):
        license_text = license_val
    elif isinstance(license_val, dict) and "file" in license_val:
        file_val = license_val.get("file")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if isinstance(file_val, str):
            filename = file_val
        else:
            filename = str(file_val) if file_val is not None else "LICENSE"  # pyright: ignore[reportUnknownArgumentType]
        license_text = f"See {filename} if distributed alongside this script"

    return PyprojectMetadata(
        name=name if isinstance(name, str) else "",
        version=version if isinstance(version, str) else "",
        description=description if isinstance(description, str) else "",
        license_text=license_text,
    )


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


def _collect_modules(
    src_dir: Path, order_names: list[str], package_name: str
) -> tuple[dict[str, str], OrderedDict[str, None], list[str]]:
    """Collect and process module sources.

    Args:
        src_dir: Directory containing Python modules
        order_names: List of module names in stitch order
        package_name: Root package name

    Returns:
        Tuple of (module_sources, all_imports, parts)
    """
    logger = get_logger()
    all_imports: OrderedDict[str, None] = OrderedDict()
    module_sources: dict[str, str] = {}
    parts: list[str] = []

    # Reserve import for shim system
    all_imports.setdefault("import sys\n", None)

    for module_name in order_names:
        module_path = src_dir / f"{module_name}.py"
        if not module_path.exists():
            logger.warning("Skipping missing module: %s.py", module_name)
            continue

        module_text = module_path.read_text(encoding="utf-8")
        module_text = strip_redundant_blocks(module_text)
        module_sources[f"{module_name}.py"] = module_text

        # Extract imports
        external_imports, module_body = split_imports(module_text, package_name)
        for imp in external_imports:
            all_imports.setdefault(imp, None)

        # Create module section
        header = f"# === {module_name}.py ==="
        parts.append(f"\n{header}\n{module_body.strip()}\n\n")

        logger.debug("Processed module: %s", module_name)

    return module_sources, all_imports, parts


def _format_header_line(
    *,
    display_name: str,
    description: str,
    package_name: str,
) -> str:
    """Format the header text based on config values.

    Rules:
    - Both provided: "DisplayName — Description"
    - Only name: "DisplayName"
    - Nothing: "package_name"
    - Only description: "package_name — Description"

    Args:
        display_name: Optional display name from config
        description: Optional description from config
        package_name: Package name (fallback)

    Returns:
        Formatted header text (without "# " prefix or trailing newline)
    """
    # Use display_name if provided, otherwise fall back to package_name
    name = display_name.strip() if display_name else package_name
    desc = description.strip() if description else ""

    if name and desc:
        return f"{name} — {desc}"
    if name:
        return f"{name}"
    # default to package_name
    return f"{package_name}"


def _build_final_script(  # noqa: PLR0913
    *,
    package_name: str,
    all_imports: OrderedDict[str, None],
    parts: list[str],
    order_names: list[str],
    license_header: str,
    version: str,
    commit: str,
    build_date: str,
    display_name: str = "",
    description: str = "",
    repo: str = "",
) -> str:
    """Build the final stitched script.

    Args:
        package_name: Root package name
        all_imports: Collected external imports
        parts: Module code sections
        order_names: List of module names (for shim generation)
        license_header: License header text
        version: Version string
        commit: Commit hash
        build_date: Build timestamp
        display_name: Optional display name for header
        description: Optional description for header
        repo: Optional repository URL for header

    Returns:
        Final script text
    """
    logger = get_logger()
    logger.debug("Building final script...")

    # Separate __future__ imports
    future_imports: OrderedDict[str, None] = OrderedDict()
    for imp in list(all_imports.keys()):
        if imp.strip().startswith("from __future__"):
            future_imports.setdefault(imp, None)
            del all_imports[imp]

    future_block = "".join(future_imports.keys())
    import_block = "".join(all_imports.keys())

    # Generate import shims
    shim_names = [n for n in order_names if not n.startswith("_")]
    shim_block = [
        "# --- import shims for single-file runtime ---",
        f"_pkg = {package_name!r}",
        "_mod = sys.modules.get(f'{_pkg}_single') or sys.modules.get(_pkg)",
        "if _mod:",
        *[f"    sys.modules[f'{{_pkg}}.{name}'] = _mod" for name in shim_names],
        "del _pkg, _mod",
        "",
    ]
    shim_text = "\n".join(shim_block)

    # Generate formatted header line
    header_line = _format_header_line(
        display_name=display_name,
        description=description,
        package_name=package_name,
    )

    # Build license/header section
    # Prefix each line of the license header with "# " if provided
    license_section = ""
    if license_header:
        lines = license_header.strip().split("\n")
        prefixed_lines = [f"# {line}" for line in lines]
        license_section = "\n".join(prefixed_lines) + "\n"
    repo_line = f"# Repo: {repo}\n" if repo else ""

    return (
        "#!/usr/bin/env python3\n"
        f"# {header_line}\n"
        f"{license_section}"
        f"# Version: {version}\n"
        f"# Commit: {commit}\n"
        f"# Build Date: {build_date}\n"
        f"{repo_line}"
        "\n# ruff: noqa: E402\n"
        "\n"
        f"{future_block}\n"
        '"""\n'
        f"{header_line}\n"
        "This single-file version is auto-generated from modular sources.\n"
        f"Version: {version}\n"
        f"Commit: {commit}\n"
        f"Built: {build_date}\n"
        '"""\n\n'
        f"{import_block}\n"
        "\n"
        # constants come *after* imports to avoid breaking __future__ rules
        f"__version__ = {json.dumps(version)}\n"
        f"__commit__ = {json.dumps(commit)}\n"
        f"__build_date__ = {json.dumps(build_date)}\n"
        f"__STANDALONE__ = True\n"
        f"__STITCH_SOURCE__ = {json.dumps(PROGRAM_PACKAGE)}\n"
        "\n"
        "\n" + "\n".join(parts) + "\n"
        f"{shim_text}\n"
        "\nif __name__ == '__main__':\n"
        "    import sys\n"
        "    sys.exit(main(sys.argv[1:]))\n"
    )


def stitch_modules(  # noqa: PLR0915
    *,
    config: dict[str, object],
    src_dir: Path,
    out_path: Path,
    license_header: str = "",
    version: str = "unknown",
    commit: str = "unknown",
    build_date: str = "unknown",
    use_ruff: bool | None = None,
) -> None:
    """Orchestrate stitching of multiple Python modules into a single file.

    This is the main entry point for the stitching process. It coordinates all
    stitching utilities to produce a single, self-contained Python script from
    modular sources.

    The function:
    1. Validates configuration completeness
    2. Verifies all modules are listed and dependencies are consistent
    3. Collects and deduplicates external imports
    4. Assembles modules in correct order
    5. Detects name collisions
    6. Generates final script with metadata
    7. Verifies the output compiles
    8. Optionally runs ruff formatting and linting if available

    Args:
        config: BuildConfigResolved with stitching fields (package, order).
                Must include 'package' and 'include' fields for stitching.
        src_dir: Directory containing Python modules to stitch
        out_path: Path where final stitched script should be written
        license_header: Optional license header text for generated script
        version: Version string to embed in script metadata
        commit: Commit hash to embed in script metadata
        build_date: Build timestamp to embed in script metadata
        use_ruff: Whether to run ruff on the stitched file if available.
                  If None, auto-detects test environment and disables ruff during tests.
                  Defaults to True in non-test environments.

    Raises:
        RuntimeError: If any validation or stitching step fails
        AssertionError: If mtime advancing fails

    Example:
        >>> from pathlib import Path
        >>> from serger.config_types import BuildConfigResolved
        >>> config = {
        ...     "package": "mymodule",
        ...     "order": ["base", "utils", "main"],
        ...     "include": [
        ...         {"path": "base.py", "root": Path("src")},
        ...         {"path": "utils.py", "root": Path("src")},
        ...         {"path": "main.py", "root": Path("src")},
        ...     ],
        ...     "exclude": [],
        ... }
        >>> stitch_modules(
        ...     config=config,
        ...     src_dir=Path("src"),
        ...     out_path=Path("dist/mymodule.py"),
        ...     version="1.0.0",
        ... )
    """
    logger = get_logger()

    # Auto-detect test environment and disable ruff if not explicitly set
    if use_ruff is None:
        # Disable ruff in test environments to avoid reformatting test outputs
        use_ruff = not is_running_under_pytest()

    package_name_raw = config.get("package", "unknown")
    order_names_raw = config.get("order", [])
    exclude_names_raw = config.get("exclude_names", [])

    # Type guards for mypy/pyright
    if not isinstance(package_name_raw, str):
        msg = "Config 'package' must be a string"
        raise TypeError(msg)
    if not isinstance(order_names_raw, list):
        msg = "Config 'order' must be a list"
        raise TypeError(msg)
    if not isinstance(exclude_names_raw, list):
        msg = "Config 'exclude_names' must be a list"
        raise TypeError(msg)

    # Cast to known types after type guards
    package_name = package_name_raw
    order_names = cast("list[str]", order_names_raw)
    exclude_names = cast("list[str]", exclude_names_raw)

    if not package_name or package_name == "unknown":
        msg = "Config must specify 'package' for stitching"
        raise RuntimeError(msg)

    if not order_names:
        msg = "Config must specify 'order' (module names) for stitching"
        raise RuntimeError(msg)

    logger.info("Starting stitch process for package: %s", package_name)

    # --- Validation Phase ---
    logger.debug("Validating module listing...")
    verify_all_modules_listed(src_dir, order_names, exclude_names)

    logger.debug("Checking module order consistency...")
    suggest_order_mismatch(order_names, package_name, src_dir)

    # --- Collection Phase ---
    logger.debug("Collecting module sources...")
    module_sources, all_imports, parts = _collect_modules(
        src_dir, order_names, package_name
    )

    # --- Collision Detection ---
    logger.debug("Detecting name collisions...")
    detect_name_collisions(module_sources)

    # --- Final Assembly ---
    # Extract display configuration
    display_name_raw = config.get("display_name", "")
    description_raw = config.get("description", "")
    repo_raw = config.get("repo", "")

    # Type guards
    if not isinstance(display_name_raw, str):
        display_name_raw = ""
    if not isinstance(description_raw, str):
        description_raw = ""
    if not isinstance(repo_raw, str):
        repo_raw = ""

    final_script = _build_final_script(
        package_name=package_name,
        all_imports=all_imports,
        parts=parts,
        order_names=order_names,
        license_header=license_header,
        version=version,
        commit=commit,
        build_date=build_date,
        display_name=display_name_raw,
        description=description_raw,
        repo=repo_raw,
    )

    # --- Verification ---
    logger.debug("Verifying assembled script...")
    verify_no_broken_imports(final_script, package_name)

    # --- Output ---
    logger.debug("Writing output file: %s", out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_script, encoding="utf-8")
    out_path.chmod(0o755)

    # Advance mtime to ensure visibility across filesystems
    logger.debug("Advancing mtime...")
    force_mtime_advance(out_path)

    # Post-processing: ruff, compilation checks, and verification
    post_stitch_processing(out_path, use_ruff=use_ruff)

    logger.info(
        "Successfully stitched %d modules into %s",
        len(parts),
        out_path,
    )
