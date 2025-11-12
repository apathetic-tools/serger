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

from .config_types import IncludeResolved, PostProcessingConfigResolved
from .logs import get_logger
from .meta import PROGRAM_PACKAGE
from .utils import derive_module_name, load_toml
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


def split_imports(  # noqa: C901, PLR0915
    text: str,
    package_names: list[str],
) -> tuple[list[str], str]:
    """Extract external imports and body text using AST.

    Separates internal package imports from external imports, removing all
    imports from the function body (they'll be collected and deduplicated).
    Recursively finds imports at all levels, including inside functions.

    Args:
        text: Python source code
        package_names: List of package names to treat as internal
            (e.g., ["serger", "other"])

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

    def find_parent(
        node: ast.AST,
        tree: ast.AST,
        target_type: type[ast.AST] | tuple[type[ast.AST], ...],
    ) -> ast.AST | None:
        """Find if a node is inside a specific parent type by tracking parent nodes."""
        # Build a mapping of child -> parent
        parent_map: dict[ast.AST, ast.AST] = {}

        def build_parent_map(parent: ast.AST) -> None:
            """Recursively build parent mapping."""
            for child in ast.iter_child_nodes(parent):
                parent_map[child] = parent
                build_parent_map(child)

        build_parent_map(tree)

        # Walk up the parent chain to find target type
        current: ast.AST | None = node
        while current is not None:
            if isinstance(current, target_type):
                # Type checker can't infer the specific type from isinstance check
                # We know it's the target_type due to the isinstance check
                return current  # mypy: ignore[return-value]
            current = parent_map.get(current)
        return None

    def has_no_move_comment(snippet: str) -> bool:
        """Check if import has a # serger: no-move comment."""
        # Look for # serger: no-move or # serger:no-move (with or without space)
        pattern = r"#\s*serger\s*:\s*no-move"
        return bool(re.search(pattern, snippet, re.IGNORECASE))

    def collect_imports(node: ast.AST) -> None:  # noqa: PLR0912
        """Recursively collect all import nodes from the AST."""
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            snippet = "".join(lines[start:end])

            # Check for # serger: no-move comment
            if has_no_move_comment(snippet):
                # Keep import in place - don't add to external_imports or ranges
                return

            # --- Determine whether it's internal ---
            is_internal = False
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level > 0:
                    is_internal = True
                else:
                    # Check if module starts with any of the package names
                    for pkg in package_names:
                        if mod.startswith(pkg):
                            is_internal = True
                            break
            else:
                # Check if any alias starts with any of the package names
                for pkg in package_names:
                    if any(alias.name.startswith(pkg) for alias in node.names):
                        is_internal = True
                        break

            # Check if import is inside if TYPE_CHECKING block
            type_checking_block = find_parent(node, tree, ast.If)
            if (
                type_checking_block
                and isinstance(type_checking_block, ast.If)
                and isinstance(type_checking_block.test, ast.Name)
                and type_checking_block.test.id == "TYPE_CHECKING"
                and len(type_checking_block.body) == 1
            ):
                # If this is the only statement in the if block, remove entire block
                type_start = type_checking_block.lineno - 1
                type_end = getattr(
                    type_checking_block, "end_lineno", type_checking_block.lineno
                )
                all_import_ranges.append((type_start, type_end))
                return  # Skip this import, entire block will be removed

            # Always remove internal imports (they break in stitched mode)
            if is_internal:
                all_import_ranges.append((start, end))
            else:
                # External: hoist module-level to top, keep function-local in place
                is_module_level = not find_parent(
                    node, tree, (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                if is_module_level:
                    # Module-level external import - hoist to top section
                    import_text = snippet.strip()
                    if import_text:
                        if not import_text.endswith("\n"):
                            import_text += "\n"
                        external_imports.append(import_text)
                        all_import_ranges.append((start, end))
                # Function-local external imports stay in place (not added to ranges)

        # Recursively visit child nodes
        for child in ast.iter_child_nodes(node):
            collect_imports(child)

    # Collect all imports recursively
    for node in tree.body:
        collect_imports(node)

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
    file_paths: list[Path], order_paths: list[Path], exclude_paths: list[Path]
) -> None:
    """Ensure all included files are listed in order or exclude paths.

    Args:
        file_paths: List of all included file paths
        order_paths: List of file paths in stitch order
        exclude_paths: List of file paths to exclude

    Raises:
        RuntimeError: If unlisted files are found
    """
    file_set = set(file_paths)
    order_set = set(order_paths)
    exclude_set = set(exclude_paths)
    known = order_set | exclude_set
    unknown = file_set - known

    if unknown:
        unknown_list = ", ".join(str(p) for p in sorted(unknown))
        msg = f"Unlisted source files detected: {unknown_list}"
        raise RuntimeError(msg)


def compute_module_order(  # noqa: C901, PLR0912, PLR0915
    file_paths: list[Path],
    package_root: Path,
    package_name: str,
    file_to_include: dict[Path, IncludeResolved],
) -> list[Path]:
    """Compute correct module order based on import dependencies.

    Uses topological sorting of internal imports to determine the correct
    order for stitching.

    Args:
        file_paths: List of file paths in initial order
        package_root: Common root of all included files
        package_name: Root package name
        file_to_include: Mapping of file path to its include (for dest access)

    Returns:
        Topologically sorted list of file paths

    Raises:
        RuntimeError: If circular imports are detected
    """
    logger = get_logger()
    # Map file paths to derived module names
    file_to_module: dict[Path, str] = {}
    module_to_file: dict[str, Path] = {}
    for file_path in file_paths:
        include = file_to_include.get(file_path)
        module_name = derive_module_name(file_path, package_root, include)
        file_to_module[file_path] = module_name
        module_to_file[module_name] = file_path

    # Detect all packages from module names (for multi-package support)
    detected_packages: set[str] = {package_name}  # Always include configured package
    for module_name in file_to_module.values():
        if "." in module_name:
            pkg = module_name.split(".", 1)[0]
            detected_packages.add(pkg)

    # Build dependency graph using derived module names
    deps: dict[str, set[str]] = {file_to_module[fp]: set() for fp in file_paths}

    for file_path in file_paths:
        module_name = file_to_module[file_path]
        if not file_path.exists():
            continue

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                # Handle relative imports (node.level > 0)
                if node.level > 0:
                    # Resolve relative import to absolute module name
                    # e.g., from .constants in serger.actions -> serger.constants
                    current_parts = module_name.split(".")
                    # Go up 'level' levels from current module
                    if node.level > len(current_parts):
                        # Relative import goes beyond package root, skip
                        continue
                    base_parts = current_parts[: -node.level]
                    if node.module:
                        # Append the module name
                        mod_parts = node.module.split(".")
                        resolved_mod = ".".join(base_parts + mod_parts)
                    else:
                        # from . import something - use base only
                        resolved_mod = ".".join(base_parts)
                    mod = resolved_mod
                else:
                    # Absolute import
                    mod = node.module or ""

                # Check if import starts with any detected package, or if it's a
                # relative import that resolved to a module name without package prefix
                matched_package = None
                is_relative_resolved = node.level > 0 and mod and "." not in mod

                for pkg in detected_packages:
                    # Match only if mod equals pkg or starts with pkg + "."
                    # This prevents false matches where a module name happens to
                    # start with a package name (e.g., "foo_bar" matching "foo")
                    if mod == pkg or mod.startswith(pkg + "."):
                        matched_package = pkg
                        break

                logger.trace(
                    "[DEPS] %s imports %s: mod=%s, matched_package=%s, "
                    "is_relative_resolved=%s",
                    module_name,
                    node.module or "",
                    mod,
                    matched_package,
                    is_relative_resolved,
                )

                # If relative import resolved to a simple name (no dots), check if it
                # matches any module name directly (for same-package imports)
                if not matched_package and is_relative_resolved:
                    # Check if the resolved module name matches any module directly
                    logger.trace(
                        "[DEPS] Relative import in %s: resolved_mod=%s, checking deps",
                        module_name,
                        mod,
                    )
                    for dep_module in deps:
                        # Match if dep_module equals mod or starts with mod.
                        if (
                            dep_module == mod or dep_module.startswith(mod + ".")
                        ) and dep_module != module_name:
                            logger.trace(
                                "[DEPS] Found dependency: %s -> %s (from %s)",
                                module_name,
                                dep_module,
                                mod,
                            )
                            deps[module_name].add(dep_module)
                    continue  # Skip the package-based matching below

                if matched_package:
                    # Handle nested imports: package.core.base -> core.base
                    # Remove package prefix and check if it matches any module
                    mod_suffix = (
                        mod[len(matched_package) + 1 :]
                        if mod.startswith(matched_package + ".")
                        else mod[len(matched_package) :]
                        if mod == matched_package
                        else ""
                    )
                    if mod_suffix:
                        # Check if this matches any derived module name
                        # Match both the suffix (for same-package imports)
                        # and full module name (for cross-package imports)
                        for dep_module in deps:
                            # Match if: dep_module equals mod_suffix or mod
                            # or dep_module starts with mod_suffix or mod
                            prefix_tuple = (mod_suffix + ".", mod + ".")
                            matches = dep_module in (
                                mod_suffix,
                                mod,
                            ) or dep_module.startswith(prefix_tuple)
                            if matches and dep_module != module_name:
                                deps[module_name].add(dep_module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name
                    # Check if import starts with any detected package
                    matched_package = None
                    for pkg in detected_packages:
                        if mod.startswith(pkg):
                            matched_package = pkg
                            break

                    if matched_package:
                        # Handle nested imports
                        mod_suffix = (
                            mod[len(matched_package) + 1 :]
                            if mod.startswith(matched_package + ".")
                            else mod[len(matched_package) :]
                            if mod == matched_package
                            else ""
                        )
                        if mod_suffix:
                            # Check if this matches any derived module name
                            # Match both the suffix (for same-package imports)
                            # and full module name (for cross-package imports)
                            for dep_module in deps:
                                prefix_tuple = (mod_suffix + ".", mod + ".")
                                matches = dep_module in (
                                    mod_suffix,
                                    mod,
                                ) or dep_module.startswith(prefix_tuple)
                                if matches and dep_module != module_name:
                                    deps[module_name].add(dep_module)

    # detect circular imports first
    try:
        sorter = graphlib.TopologicalSorter(deps)
        topo_modules = list(sorter.static_order())
    except graphlib.CycleError as e:
        msg = f"Circular dependency detected: {e.args[1] if e.args else 'unknown'}"
        raise RuntimeError(msg) from e

    # Convert back to file paths
    topo_paths = [module_to_file[mod] for mod in topo_modules if mod in module_to_file]
    return topo_paths


def suggest_order_mismatch(
    order_paths: list[Path],
    package_root: Path,
    package_name: str,
    file_to_include: dict[Path, IncludeResolved],
    topo_paths: list[Path] | None = None,
) -> None:
    """Warn if module order violates dependencies.

    Args:
        order_paths: List of file paths in intended order
        package_root: Common root of all included files
        package_name: Root package name
        file_to_include: Mapping of file path to its include (for dest access)
        topo_paths: Optional pre-computed topological order. If provided,
                    skips recomputing the order. If None, computes it via
                    compute_module_order.
    """
    logger = get_logger()
    if topo_paths is None:
        topo_paths = compute_module_order(
            order_paths, package_root, package_name, file_to_include
        )

    # compare order_paths to topological sort
    mismatched = [
        p
        for p in order_paths
        if p in topo_paths and topo_paths.index(p) != order_paths.index(p)
    ]
    if mismatched:
        logger.warning("Possible module misordering detected:")

        for p in mismatched:
            include = file_to_include.get(p)
            module_name = derive_module_name(p, package_root, include)
            logger.warning("  - %s appears before one of its dependencies", module_name)
        topo_modules = [
            derive_module_name(p, package_root, file_to_include.get(p))
            for p in topo_paths
        ]
        logger.warning("Suggested order: %s", ", ".join(topo_modules))


def verify_no_broken_imports(final_text: str, package_name: str) -> None:
    """Verify all internal imports have been resolved in stitched script.

    Args:
        final_text: Final stitched script text
        package_name: Root package name

    Raises:
        RuntimeError: If unresolved imports remain
    """
    # Pattern for nested imports: package.core.base or package.core
    # Matches: import package.module or import package.sub.module
    import_pattern = re.compile(rf"\bimport {re.escape(package_name)}\.([\w.]+)")
    # Pattern for from imports: from package.core import base or
    # from package.core.base import something
    from_pattern = re.compile(rf"\bfrom {re.escape(package_name)}\.([\w.]+)\s+import")

    broken: set[str] = set()

    # Check import statements
    for m in import_pattern.finditer(final_text):
        mod_suffix = m.group(1)
        # Check if module is in the stitched output
        # Header format: # === module_name === (may contain dots for nested modules)
        header_pattern = re.compile(rf"# === {re.escape(mod_suffix)} ===")
        if not header_pattern.search(final_text):
            broken.add(f"{package_name}.{mod_suffix}")

    # Check from ... import statements
    for m in from_pattern.finditer(final_text):
        mod_suffix = m.group(1)
        # Check if module is in the stitched output
        header_pattern = re.compile(rf"# === {re.escape(mod_suffix)} ===")
        if not header_pattern.search(final_text):
            broken.add(f"{package_name}.{mod_suffix}")

    if broken:
        broken_list = ", ".join(sorted(broken))
        msg = f"Unresolved internal imports: {broken_list}"
        raise RuntimeError(msg)


def _find_package_root_for_file(file_path: Path) -> Path | None:
    """Find the package root for a file by walking up looking for __init__.py.

    Starting from the file's directory, walks up the directory tree while
    we find __init__.py files. The topmost directory with __init__.py is
    the package root.

    Args:
        file_path: Path to the Python file

    Returns:
        Path to the package root directory, or None if not found
    """
    logger = get_logger()
    current_dir = file_path.parent.resolve()
    last_package_dir: Path | None = None

    logger.trace(
        "[PKG_ROOT] Finding package root for %s, starting from %s",
        file_path.name,
        current_dir,
    )

    # Walk up from the file's directory
    while True:
        # Check if current directory has __init__.py
        init_file = current_dir / "__init__.py"
        if init_file.exists():
            # This directory is part of a package
            last_package_dir = current_dir
            logger.trace(
                "[PKG_ROOT] Found __init__.py at %s (package root so far: %s)",
                current_dir,
                last_package_dir,
            )
        else:
            # This directory doesn't have __init__.py, so we've gone past the package
            # Return the last directory that had __init__.py
            logger.trace(
                "[PKG_ROOT] No __init__.py at %s, package root: %s",
                current_dir,
                last_package_dir,
            )
            return last_package_dir

        # Move up one level
        parent = current_dir.parent
        if parent == current_dir:
            # Reached filesystem root
            logger.trace(
                "[PKG_ROOT] Reached filesystem root, package root: %s",
                last_package_dir,
            )
            return last_package_dir
        current_dir = parent


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
    file_paths: list[Path],
    package_root: Path,
    package_name: str,
    file_to_include: dict[Path, IncludeResolved],
) -> tuple[dict[str, str], OrderedDict[str, None], list[str], list[str]]:
    """Collect and process module sources from file paths.

    Args:
        file_paths: List of file paths to stitch (in order)
        package_root: Common root of all included files
        package_name: Root package name
        file_to_include: Mapping of file path to its include (for dest access)

    Returns:
        Tuple of (module_sources, all_imports, parts, derived_module_names)
    """
    logger = get_logger()
    all_imports: OrderedDict[str, None] = OrderedDict()
    module_sources: dict[str, str] = {}
    parts: list[str] = []
    derived_module_names: list[str] = []

    # Reserve imports for shim system and main entry point
    all_imports.setdefault("import sys\n", None)  # For shim system and main()
    all_imports.setdefault("import types\n", None)  # For shim system (ModuleType)

    # First pass: collect all module names to detect packages
    all_module_names: list[str] = []
    for file_path in file_paths:
        if not file_path.exists():
            logger.warning("Skipping missing file: %s", file_path)
            continue
        include = file_to_include.get(file_path)
        module_name = derive_module_name(file_path, package_root, include)
        all_module_names.append(module_name)

    # Detect all packages from module names
    detected_packages: set[str] = {package_name}  # Always include configured package
    for module_name in all_module_names:
        if "." in module_name:
            pkg = module_name.split(".", 1)[0]
            detected_packages.add(pkg)

    # Convert to sorted list for consistent behavior
    package_names_list = sorted(detected_packages)

    for file_path in file_paths:
        if not file_path.exists():
            logger.warning("Skipping missing file: %s", file_path)
            continue

        # Derive module name from file path
        include = file_to_include.get(file_path)
        module_name = derive_module_name(file_path, package_root, include)
        derived_module_names.append(module_name)

        module_text = file_path.read_text(encoding="utf-8")
        module_text = strip_redundant_blocks(module_text)
        module_sources[f"{module_name}.py"] = module_text

        # Extract imports - pass all detected package names
        external_imports, module_body = split_imports(module_text, package_names_list)
        for imp in external_imports:
            all_imports.setdefault(imp, None)

        # Create module section - use derived module name in header
        header = f"# === {module_name} ==="
        parts.append(f"\n{header}\n{module_body.strip()}\n\n")

        logger.trace("Processed module: %s (from %s)", module_name, file_path)

    return module_sources, all_imports, parts, derived_module_names


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


def _build_final_script(  # noqa: C901, PLR0912, PLR0913, PLR0915
    *,
    package_name: str,
    all_imports: OrderedDict[str, None],
    parts: list[str],
    order_names: list[str],
    order_paths: list[Path] | None = None,
    package_root: Path | None = None,
    file_to_include: dict[Path, IncludeResolved] | None = None,
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
        order_paths: Optional list of file paths corresponding to order_names
        package_root: Optional common root of all included files
        file_to_include: Optional mapping of file path to its include
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
    # Group modules by their immediate parent package
    # For "serger.utils.utils_text", the parent package is "serger.utils"
    # For "serger.cli", the parent package is "serger"
    # Include all modules (matching installed package behavior)
    #
    # IMPORTANT: Module names in order_names are relative to package_root
    # (e.g., "utils.utils_text"), but shims need full paths
    # (e.g., "serger.utils.utils_text").
    # Prepend package_name to all module names for shim generation.
    # Note: If specific modules should be excluded, use the 'exclude' config option
    shim_names_raw = list(order_names)

    # Detect packages by looking at file system structure (__init__.py files)
    # This is more reliable than guessing from module names
    # Map module names to their actual package roots
    module_to_package_root: dict[str, Path | None] = {}
    detected_packages: set[str] = {package_name}  # Always include configured package

    if order_paths and package_root and file_to_include:
        logger.trace(
            "[PKG_DETECT] Detecting packages from file system structure "
            "(__init__.py files)"
        )
        # Create mapping from module names to file paths
        name_to_path: dict[str, Path] = {}
        for file_path in order_paths:
            include = file_to_include.get(file_path)
            module_name = derive_module_name(file_path, package_root, include)
            name_to_path[module_name] = file_path

        # For each module, find its package root by walking up looking for __init__.py
        for module_name in shim_names_raw:
            if module_name in name_to_path:
                file_path = name_to_path[module_name]
                file_pkg_root = _find_package_root_for_file(file_path)
                module_to_package_root[module_name] = file_pkg_root

                # Determine if this file is from a different package
                # A file is from a different package if its package root is:
                # 1. Not the same as package_root, AND
                # 2. Not a subdirectory of package_root
                #    (i.e., it's a sibling or unrelated)
                if file_pkg_root and file_pkg_root != package_root:
                    try:
                        # Check if file_pkg_root is a subdirectory of package_root
                        rel_path = file_pkg_root.relative_to(package_root)
                        # If it's a direct child (one level deep), it might be
                        # a sibling package like pkg1/ and pkg2/ under a common root
                        if len(rel_path.parts) == 1:
                            # It's a direct child - check if it's a different package
                            # by comparing the package root name to package_name
                            pkg_name_from_path = file_pkg_root.name
                            if (
                                pkg_name_from_path
                                and pkg_name_from_path != package_name
                            ):
                                logger.trace(
                                    "[PKG_DETECT] Detected separate package %s "
                                    "(sibling of %s) from file %s",
                                    pkg_name_from_path,
                                    package_name,
                                    file_path,
                                )
                                detected_packages.add(pkg_name_from_path)
                            else:
                                logger.trace(
                                    "[PKG_DETECT] %s is subpackage of %s "
                                    "(file_pkg_root=%s, package_root=%s)",
                                    module_name,
                                    package_name,
                                    file_pkg_root,
                                    package_root,
                                )
                        # If it's deeper (len > 1), it's a subpackage
                        else:
                            logger.trace(
                                "[PKG_DETECT] %s is nested subpackage of %s (depth=%d)",
                                module_name,
                                package_name,
                                len(rel_path.parts),
                            )
                    except ValueError:
                        # file_pkg_root is not under package_root,
                        # so it's a different package
                        # Extract package name from the file's package root
                        pkg_name_from_path = file_pkg_root.name
                        if pkg_name_from_path and pkg_name_from_path != package_name:
                            logger.trace(
                                "[PKG_DETECT] Detected separate package %s "
                                "(unrelated to %s) from file %s",
                                pkg_name_from_path,
                                package_name,
                                file_path,
                            )
                            detected_packages.add(pkg_name_from_path)
                elif file_pkg_root == package_root:
                    logger.trace(
                        "[PKG_DETECT] %s is in main package %s",
                        module_name,
                        package_name,
                    )
                else:
                    logger.trace(
                        "[PKG_DETECT] %s: no package root found (file_pkg_root=None)",
                        module_name,
                    )

    # Also detect packages from module names
    # (as fallback when __init__.py detection fails)
    # Only do this if we didn't successfully detect packages from file system
    # (i.e., if module_to_package_root is empty or all values are None)
    if not module_to_package_root or all(
        v is None for v in module_to_package_root.values()
    ):
        logger.debug(
            "Package detection: __init__.py files not found, "
            "falling back to module name detection"
        )
        # Fallback: detect packages from module names
        for module_name in shim_names_raw:
            if "." in module_name:
                pkg = module_name.split(".", 1)[0]
                # Only add if it's clearly a different package (not a subpackage)
                # We can't reliably distinguish, so be conservative and only add
                # if it's different from package_name
                if pkg != package_name:
                    logger.trace(
                        "[PKG_DETECT] Fallback: detected package %s "
                        "from module name %s",
                        pkg,
                        module_name,
                    )
                    detected_packages.add(pkg)

    # Prepend package_name to create full module paths
    # Module names are relative to package_root, so we need to prepend package_name
    # to get the full import path
    # (e.g., "utils.utils_text" -> "serger.utils.utils_text")
    # However, if module names already start with package_name or another package,
    # don't double-prefix (for multi-package scenarios)
    shim_names: list[str] = []
    for name in shim_names_raw:
        # If name already equals package_name, it's the root module itself
        if name == package_name:
            full_name = package_name
        # If name already starts with package_name, use it as-is
        elif name.startswith(f"{package_name}."):
            full_name = name
        # If name contains dots and starts with a different detected package,
        # it's from another package (multi-package scenario) - use as-is
        elif "." in name:
            first_part = name.split(".", 1)[0]
            # If first part is a detected package different from package_name,
            # it's from another package - use as-is
            if first_part in detected_packages and first_part != package_name:
                full_name = name
            else:
                # Likely a subpackage - prepend package_name
                full_name = f"{package_name}.{name}"
        else:
            # Top-level module under package: prepend package_name
            full_name = f"{package_name}.{name}"
        shim_names.append(full_name)

    # Group modules by their parent package
    # parent_package -> list of (module_name, is_direct_child)
    # is_direct_child means the module is directly under this package
    # (not nested deeper)
    packages: dict[str, list[tuple[str, bool]]] = {}
    # parent_pkg -> [(module_name, is_direct)]

    for module_name in shim_names:
        if "." not in module_name:
            # Top-level module, parent is the root package
            parent = package_name
            is_direct = True
        else:
            # Find the parent package (everything except the last component)
            name_parts = module_name.split(".")
            parent = ".".join(name_parts[:-1])
            is_direct = True  # This module is directly under its parent

        if parent not in packages:
            packages[parent] = []
        packages[parent].append((module_name, is_direct))

    # Collect all package names (both intermediate and top-level)
    all_packages: set[str] = set()
    for module_name in shim_names:
        name_parts = module_name.split(".")
        # Add all package prefixes
        # (e.g., for "serger.utils.utils_text" add "serger" and "serger.utils")
        for i in range(1, len(name_parts)):
            pkg = ".".join(name_parts[:i])
            all_packages.add(pkg)
        # Also add the top-level package if module has dots
        if "." in module_name:
            all_packages.add(name_parts[0])
    # Add root package if not already present
    all_packages.add(package_name)

    # Sort packages by depth (shallowest first) to create parents before children
    sorted_packages = sorted(all_packages, key=lambda p: p.count("."))

    # Generate shims for each package
    # Each package gets its own module object to maintain proper isolation
    shim_blocks: list[str] = []
    shim_blocks.append("# --- import shims for single-file runtime ---")
    # Note: types and sys are imported at the top level (see all_imports)

    # First pass: Create all package modules and set up parent-child relationships
    for pkg_name in sorted_packages:
        # Get or create the package module
        shim_blocks.append(f"_pkg = {pkg_name!r}")
        shim_blocks.append("# Get existing module if we are imported as a module")
        shim_blocks.append("_mod = sys.modules.get(_pkg)")
        shim_blocks.append("# Create module object if executed as script")
        shim_blocks.append("if not _mod:")
        shim_blocks.append("    _mod = types.ModuleType(_pkg)")
        shim_blocks.append("    sys.modules[_pkg] = _mod")

        # If this is a nested package, set it as an attribute on its parent
        if "." in pkg_name:
            parent_pkg = ".".join(pkg_name.split(".")[:-1])
            child_name = pkg_name.split(".")[-1]
            shim_blocks.append(
                f"# Set {pkg_name!r} as attribute on parent {parent_pkg!r}"
            )
            shim_blocks.append(f"_parent = sys.modules.get({parent_pkg!r})")
            shim_blocks.append("if _parent:")
            shim_blocks.append(f"    setattr(_parent, {child_name!r}, _mod)")
            shim_blocks.append("del _parent")

        shim_blocks.append("del _pkg, _mod")
        shim_blocks.append("")

    # Second pass: Copy attributes and register modules
    # Process in any order since all modules are now created
    for pkg_name in sorted_packages:
        if pkg_name not in packages:
            continue  # Skip packages that don't have any modules

        shim_blocks.append(f"_pkg = {pkg_name!r}")
        shim_blocks.append("_mod = sys.modules.get(_pkg)")
        shim_blocks.append("if _mod:")
        # Copy attributes from all modules that belong to this package
        # All modules under a package share the same module object,
        # so all their attributes should be on this module
        # Include all attributes (matching installed package behavior)
        shim_blocks.append("    # Copy attributes from all modules under this package")
        shim_blocks.append("    _globals = globals()")
        shim_blocks.append("    _items = [(k, v) for k, v in _globals.items()]")
        shim_blocks.append("    for _key, _value in _items:")
        shim_blocks.append("        setattr(_mod, _key, _value)")
        shim_blocks.append("    del _globals, _items")

        # Register all modules that belong to this package
        # All modules under a package share the same module object
        module_names_for_pkg = [name for name, _ in packages[pkg_name]]
        if module_names_for_pkg:
            shim_blocks.append("    # Register all modules under this package")
            # Module names already have full paths (with package_name prefix),
            # but ensure they're correctly formatted for registration
            # If name equals pkg_name, it's the root module itself
            full_module_names = [
                (
                    name
                    if (name == pkg_name or name.startswith(f"{pkg_name}."))
                    else f"{pkg_name}.{name}"
                )
                for name in module_names_for_pkg
            ]
            module_names_str = ", ".join(repr(name) for name in full_module_names)
            shim_blocks.append(f"    for _name in [{module_names_str}]:")
            shim_blocks.append("        sys.modules[_name] = _mod")
            shim_blocks.append("    # Set submodules as attributes on parent package")
            shim_blocks.append("    # This allows 'import parent.submodule' to work")
            shim_blocks.append(
                "    # Only set if not already present (avoid overwriting functions)"
            )
            for full_name in full_module_names:
                if full_name != pkg_name and full_name.startswith(f"{pkg_name}."):
                    # Extract the submodule name (last component)
                    submodule_name = full_name.split(".")[-1]
                    shim_blocks.append(f"    if not hasattr(_mod, {submodule_name!r}):")
                    shim_blocks.append(
                        f"        setattr(_mod, {submodule_name!r}, _mod)"
                    )

        shim_blocks.append("del _pkg, _mod")
        shim_blocks.append("")

    shim_text = "\n".join(shim_blocks)

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
        "    sys.exit(main(sys.argv[1:]))\n"
    )


def stitch_modules(  # noqa: PLR0915, PLR0912, C901
    *,
    config: dict[str, object],
    file_paths: list[Path],
    package_root: Path,
    file_to_include: dict[Path, IncludeResolved],
    out_path: Path,
    license_header: str = "",
    version: str = "unknown",
    commit: str = "unknown",
    build_date: str = "unknown",
    post_processing: PostProcessingConfigResolved | None = None,
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
    8. Optionally runs post-processing tools (static checker, formatter, import sorter)

    Args:
        config: BuildConfigResolved with stitching fields (package, order).
                Must include 'package' field for stitching. 'order' is optional
                and will be auto-discovered via topological sort if not provided.
        file_paths: List of file paths to stitch (in order)
        package_root: Common root of all included files
        file_to_include: Mapping of file path to its include (for dest access)
        out_path: Path where final stitched script should be written
        license_header: Optional license header text for generated script
        version: Version string to embed in script metadata
        commit: Commit hash to embed in script metadata
        build_date: Build timestamp to embed in script metadata
        post_processing: Post-processing configuration (if None, skips post-processing)

    Raises:
        RuntimeError: If any validation or stitching step fails
        AssertionError: If mtime advancing fails
    """
    logger = get_logger()

    package_name_raw = config.get("package", "unknown")
    order_paths_raw = config.get("order", [])
    exclude_paths_raw = config.get("exclude_names", [])

    # Type guards for mypy/pyright
    if not isinstance(package_name_raw, str):
        msg = "Config 'package' must be a string"
        raise TypeError(msg)
    if not isinstance(order_paths_raw, list):
        msg = "Config 'order' must be a list"
        raise TypeError(msg)
    if not isinstance(exclude_paths_raw, list):
        msg = "Config 'exclude_names' must be a list"
        raise TypeError(msg)

    # Cast to known types after type guards
    package_name = package_name_raw
    # order and exclude_names are already resolved to Path objects in run_build()
    # Convert to Path objects explicitly

    order_paths: list[Path] = []
    for item in order_paths_raw:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, str):
            order_paths.append(Path(item))
        elif isinstance(item, Path):
            order_paths.append(item)

    exclude_paths: list[Path] = []
    for item in exclude_paths_raw:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, str):
            exclude_paths.append(Path(item))
        elif isinstance(item, Path):
            exclude_paths.append(item)

    if not package_name or package_name == "unknown":
        msg = "Config must specify 'package' for stitching"
        raise RuntimeError(msg)

    if not order_paths:
        msg = (
            "No modules found for stitching. "
            "Either specify 'order' in config or ensure 'include' patterns match files."
        )
        raise RuntimeError(msg)

    logger.info("Starting stitch process for package: %s", package_name)

    # --- Validation Phase ---
    logger.debug("Validating module listing...")
    verify_all_modules_listed(file_paths, order_paths, exclude_paths)

    logger.debug("Checking module order consistency...")
    # Use pre-computed topological order if available (from auto-discovery)
    topo_paths_raw = config.get("topo_paths")
    topo_paths: list[Path] | None = None
    if topo_paths_raw is not None and isinstance(topo_paths_raw, list):
        topo_paths = []
        # Type narrowing: after isinstance check, cast to help type inference
        for item in cast("list[str | Path]", topo_paths_raw):
            if isinstance(item, str):
                topo_paths.append(Path(item))
            elif isinstance(item, Path):  # pyright: ignore[reportUnnecessaryIsInstance]
                topo_paths.append(item)
    suggest_order_mismatch(
        order_paths, package_root, package_name, file_to_include, topo_paths
    )

    # --- Collection Phase ---
    logger.debug("Collecting module sources...")
    module_sources, all_imports, parts, derived_module_names = _collect_modules(
        order_paths, package_root, package_name, file_to_include
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
        order_names=derived_module_names,
        order_paths=order_paths,
        package_root=package_root,
        file_to_include=file_to_include,
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

    # Post-processing: tools, compilation checks, and verification
    post_stitch_processing(out_path, post_processing=post_processing)

    logger.info(
        "Successfully stitched %d modules into %s",
        len(parts),
        out_path,
    )
