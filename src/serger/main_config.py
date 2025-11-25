# src/serger/main_config.py
"""Main function configuration and detection logic.

This module handles parsing of main_name configuration, finding main functions,
and managing __main__ block generation.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

from serger.utils.utils_modules import derive_module_name


if TYPE_CHECKING:
    from serger.config import IncludeResolved, RootConfigResolved


@dataclass
class MainBlock:
    """Represents a detected __main__ block.

    Attributes:
        content: The full content of the __main__ block (including the if statement)
        file_path: Path to the file containing the block
        module_name: Module name derived from the file path
    """

    content: str
    file_path: Path
    module_name: str


def parse_main_name(main_name: str | None) -> tuple[str | None, str]:
    """Parse main_name syntax to extract module path and function name.

    Syntax rules:
    - With dots (module/package path): `::` is optional
      - `mypkg.subpkg` → module `mypkg.subpkg`, function `main` (default)
      - `mypkg.subpkg::` → module `mypkg.subpkg`, function `main` (explicit)
      - `mypkg.subpkg::entry` → module `mypkg.subpkg`, function `entry`
    - Without dots (single name): `::` is required to indicate package
      - `mypkg::` → package `mypkg`, function `main` (default)
      - `mypkg::entry` → package `mypkg`, function `entry`
      - `mypkg` → function name `mypkg` (search across all packages)
      - `main` → function name `main` (search across all packages)

    Args:
        main_name: The main_name configuration value (can be None)

    Returns:
        Tuple of (module_path, function_name):
        - module_path: Module/package path (None if function name only)
        - function_name: Function name to search for (defaults to "main")
    """
    # If None, return (None, "main") for auto-detection
    if main_name is None:
        return (None, "main")

    # If contains `::`, split on it
    if "::" in main_name:
        parts = main_name.split("::", 1)
        module_path = parts[0] if parts[0] else None
        function_name = parts[1] if parts[1] else "main"
        return (module_path, function_name)

    # If no `::`, check for dots
    if "." in main_name:
        # Contains dots: treat as module path, function defaults to "main"
        return (main_name, "main")

    # No dots and no `::`: treat as function name, module path is None
    return (None, main_name)


def _extract_top_level_function_names(source: str) -> set[str]:
    """Extract all top-level function names from source code.

    This is a "dumb extraction" function that only extracts function names.
    It does not filter by name - that's handled by the usage function.

    Args:
        source: Python source code to analyze

    Returns:
        Set of top-level function names (both sync and async)
    """
    try:
        tree = ast.parse(source)
        function_names: set[str] = set()
        # Only search top-level functions (direct children of module)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.add(node.name)
        return function_names  # noqa: TRY300
    except (SyntaxError, ValueError):
        return set()


def _find_function_in_source(
    source: str, function_name: str
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find a top-level function definition in source code.

    Args:
        source: Python source code
        function_name: Name of function to find

    Returns:
        Function node if found, None otherwise
    """
    try:
        tree = ast.parse(source)
        # Only search top-level functions (direct children of module)
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == function_name
            ):
                return node
    except (SyntaxError, ValueError):
        pass
    return None


def _get_file_priority(file_path: Path) -> int:
    """Get priority for file search order.

    Lower numbers = higher priority.
    Priority: __main__.py (0) < __init__.py (1) < other files (2)

    Args:
        file_path: File path to check

    Returns:
        Priority value (lower = higher priority)
    """
    if file_path.name == "__main__.py":
        return 0
    if file_path.name == "__init__.py":
        return 1
    return 2


def detect_function_parameters(
    function_node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> bool:
    """Detect if a function has any parameters.

    Checks for positional parameters, *args, **kwargs, and default values.

    Args:
        function_node: AST node for the function definition

    Returns:
        True if function has any parameters, False otherwise
    """
    args = function_node.args

    # Check for any type of parameter
    return bool(
        args.args  # Positional parameters
        or args.vararg is not None  # *args
        or args.kwarg is not None  # **kwargs
        or args.kwonlyargs  # Keyword-only arguments
        or (
            args.kw_defaults and any(d is not None for d in args.kw_defaults)
        )  # Keyword-only args with defaults
    )


def find_main_function(  # noqa: PLR0912, C901, PLR0915
    *,
    config: "RootConfigResolved",
    file_paths: list[Path],
    module_sources: dict[str, str],
    module_names: list[str],  # noqa: ARG001  # Unused: we derive from module_to_file instead
    package_root: Path,
    file_to_include: dict[Path, "IncludeResolved"],
    detected_packages: set[str],
) -> tuple[str, Path, str] | None:
    """Find the main function based on configuration.

    Search order:
    1. If `main_name` is set, use it (with fallback logic)
    2. If `package` is set, search in that package
    3. Search in first package from include order

    Args:
        config: Resolved configuration with main_mode and main_name
        file_paths: List of file paths being stitched (in order)
        module_sources: Mapping of module name to source code
        module_names: List of module names in order (unused, kept for API)
        package_root: Common root of all included files
        file_to_include: Mapping of file path to its include
        detected_packages: Pre-detected package names

    Returns:
        Tuple of (function_name, source_file, module_path) if found, None otherwise
    """
    main_mode = config.get("main_mode", "auto")
    main_name = config.get("main_name")
    package = config.get("package")

    # If main_mode is "none", don't search
    if main_mode == "none":
        return None

    # Build mapping from module names to file paths
    # Also handle package_root being a package directory itself
    is_package_dir = (package_root / "__init__.py").exists()
    package_name_from_root: str | None = None
    if is_package_dir:
        package_name_from_root = package_root.name
    # Also treat as package directory if package_root.name matches package
    # (even without __init__.py, files in package_root are submodules of package)
    elif package is not None and package_root.name == package:
        package_name_from_root = package_root.name
        is_package_dir = True  # Treat as package directory for module naming

    # Check if any files have imports that reference the package name
    # (indicates files are part of that package structure)
    has_package_imports = False
    if (
        package is not None
        and package_root.name != package
        and package_root.name in ("src", "lib", "app", "package", "packages")
    ):
        # Quick check: see if any file imports from the package
        for file_path in file_paths:
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                # Check for imports that reference the package name
                if f"from {package}" in content or f"import {package}" in content:
                    has_package_imports = True
                    break
            except Exception:  # noqa: BLE001, S110
                # If we can't read the file, skip the check
                pass

    # Extract source_bases from config for external files
    # source_bases is validated and normalized to list[str] in config resolution
    # It's always present in RootConfigResolved, but .get() returns object | None
    source_bases_raw = config.get("source_bases")
    source_bases: list[str] | None = None
    if source_bases_raw is not None:  # pyright: ignore[reportUnnecessaryComparison]
        # Type narrowing: config is RootConfigResolved where source_bases is list[str]
        # Cast is safe because source_bases is validated in config resolution
        # mypy sees cast as redundant, but pyright needs it for type narrowing
        source_bases = [str(mb) for mb in cast("list[str]", source_bases_raw)]  # type: ignore[redundant-cast]  # pyright: ignore[reportUnnecessaryCast]

    module_to_file: dict[str, Path] = {}
    for file_path in file_paths:
        include = file_to_include.get(file_path)
        module_name = derive_module_name(
            file_path, package_root, include, source_bases=source_bases
        )

        # If package_root is a package directory, preserve package structure
        if is_package_dir and package_name_from_root:
            # Handle __init__.py special case: represents the package itself
            if file_path.name == "__init__.py" and file_path.parent == package_root:
                module_name = package_name_from_root
            else:
                # Prepend package name to preserve structure
                module_name = f"{package_name_from_root}.{module_name}"
        # If package name is provided but package_root.name doesn't match,
        # still prepend package name to ensure correct module structure
        # (e.g., files in src/ but package is testpkg -> testpkg.utils)
        # Only do this if package_root is a common project subdirectory
        # (like src, lib, app) AND files have imports that reference the package
        elif (
            package is not None
            and package_root.name != package
            and not module_name.startswith(f"{package}.")
            and has_package_imports
            and module_name != package
        ):
            # Prepend package name to module name
            module_name = f"{package}.{module_name}"

        module_to_file[module_name] = file_path

    # Parse main_name to get module path and function name
    module_path_spec, function_name = parse_main_name(main_name)

    # Use module_to_file.keys() instead of module_names to ensure we use
    # the correct module names (with package prefix if applicable)
    available_module_names = sorted(module_to_file.keys())

    # Search strategy based on what's specified
    search_candidates: list[tuple[str, Path]] = []

    if main_name is not None:
        # main_name is set: use it
        if module_path_spec is not None:
            # Module path specified: search in that module/package
            # Match modules that start with the specified path
            search_candidates.extend(
                (mod_name, module_to_file[mod_name])
                for mod_name in available_module_names
                if (
                    mod_name == module_path_spec
                    or mod_name.startswith(f"{module_path_spec}.")
                )
            )
        else:
            # Function name only: search across all packages
            search_candidates.extend(
                (mod_name, module_to_file[mod_name])
                for mod_name in available_module_names
            )
    elif package is not None:
        # main_name is None, but package is set: search in that package
        search_candidates.extend(
            (mod_name, module_to_file[mod_name])
            for mod_name in available_module_names
            if mod_name == package or mod_name.startswith(f"{package}.")
        )
    # No main_name and no package: search in first package from include order
    elif detected_packages:
        first_package = sorted(detected_packages)[0]
        search_candidates.extend(
            (mod_name, module_to_file[mod_name])
            for mod_name in available_module_names
            if mod_name == first_package or mod_name.startswith(f"{first_package}.")
        )
    else:
        # No packages detected: search all modules
        search_candidates.extend(
            (mod_name, module_to_file[mod_name]) for mod_name in available_module_names
        )

    # Sort candidates by file priority
    # (__main__.py first, then __init__.py, then others)
    # Then by module name for determinism
    search_candidates.sort(key=lambda x: (_get_file_priority(x[1]), x[0]))

    # Extract function names from all candidates (one parse per candidate)
    # Then filter to only candidates that have the function name
    for mod_name, file_path in search_candidates:
        # Get module source (key includes .py suffix)
        module_key = f"{mod_name}.py"
        if module_key not in module_sources:
            continue

        source = module_sources[module_key]
        # Extract function names (parses AST once)
        function_names = _extract_top_level_function_names(source)
        # Filter: only keep candidates that have the function name
        if function_name in function_names:
            # Return first matching candidate (already sorted by priority)
            return (function_name, file_path, mod_name)

    # Not found
    return None


def _is_main_guard(node: ast.If) -> bool:  # noqa: PLR0911
    """Check if an if statement is a __main__ guard.

    Args:
        node: AST If node to check

    Returns:
        True if this is a __main__ guard, False otherwise
    """
    # Check if condition is: __name__ == '__main__'
    if not isinstance(node.test, ast.Compare):
        return False

    compare = node.test
    if len(compare.ops) != 1:
        return False

    if not isinstance(compare.ops[0], ast.Eq):
        return False

    # Check left side is __name__
    if not isinstance(compare.left, ast.Name):
        return False
    if compare.left.id != "__name__":
        return False

    # Check right side is '__main__' or "__main__"
    if len(compare.comparators) != 1:
        return False

    comparator = compare.comparators[0]
    if isinstance(comparator, ast.Constant):
        return comparator.value == "__main__"

    return False


def _extract_main_guards(source: str) -> list[tuple[int, int | None]]:
    """Extract line ranges for __main__ guard blocks.

    This is a "dumb extraction" function that only extracts line ranges.
    It does not extract block content - that's handled by the usage function.

    Args:
        source: Python source code to analyze

    Returns:
        List of (start_line, end_line) tuples where:
        - start_line: 1-indexed line number where the guard starts
        - end_line: 1-indexed line number (exclusive) where the guard ends,
          or None if end_lineno is not available (Python < 3.8)
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []

    guards: list[tuple[int, int | None]] = []

    # Find all top-level if statements that are __main__ guards
    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                # Python 3.8+ has end_lineno
                start_line = node.lineno  # 1-indexed
                end_line = node.end_lineno  # 1-indexed (exclusive)
                guards.append((start_line, end_line))
            elif hasattr(node, "lineno"):
                # Python < 3.8 or no end_lineno
                start_line = node.lineno  # 1-indexed
                guards.append((start_line, None))
            # If no lineno, skip (shouldn't happen in valid AST)

    return guards


def detect_main_blocks(  # noqa: PLR0912
    *,
    file_paths: list[Path],
    package_root: Path,
    file_to_include: dict[Path, "IncludeResolved"],
    detected_packages: set[str],  # noqa: ARG001
) -> list[MainBlock]:
    """Detect all __main__ blocks in the provided file paths.

    Args:
        file_paths: List of file paths to check (in order)
        package_root: Common root of all included files
        file_to_include: Mapping of file path to its include
        detected_packages: Pre-detected package names
            (unused, kept for API consistency)

    Returns:
        List of MainBlock objects, one for each detected __main__ block
    """
    main_blocks: list[MainBlock] = []

    # Build mapping from module names to file paths
    # Also handle package_root being a package directory itself
    is_package_dir = (package_root / "__init__.py").exists()
    package_name_from_root: str | None = None
    if is_package_dir:
        package_name_from_root = package_root.name

    for file_path in file_paths:
        if not file_path.exists():
            continue

        # Read file content
        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Extract main guard line ranges (parses AST once)
        guard_ranges = _extract_main_guards(source)

        # Extract block content from line ranges (usage logic)
        for start_line, end_line in guard_ranges:
            # Convert 1-indexed line numbers to 0-indexed for slicing
            start_idx = start_line - 1  # 0-indexed
            block_content: str | None = None

            if end_line is not None:
                # Python 3.8+ has end_lineno
                lines = source.splitlines(keepends=True)
                if start_idx < len(lines) and end_line <= len(lines):
                    block_lines = lines[start_idx:end_line]
                    block_content = "".join(block_lines).rstrip()
                else:
                    # Fallback: use regex to find block
                    block_content = _extract_main_block_regex(source)
            else:
                # Python < 3.8 or no end_lineno: use regex fallback
                block_content = _extract_main_block_regex(source)

            if block_content:
                # Derive module name
                include = file_to_include.get(file_path)
                module_name = derive_module_name(file_path, package_root, include)

                # If package_root is a package directory, preserve package structure
                if is_package_dir and package_name_from_root:
                    # Handle __init__.py special case: represents the package itself
                    if (
                        file_path.name == "__init__.py"
                        and file_path.parent == package_root
                    ):
                        module_name = package_name_from_root
                    else:
                        # Prepend package name to preserve structure
                        module_name = f"{package_name_from_root}.{module_name}"

                main_blocks.append(
                    MainBlock(
                        content=block_content,
                        file_path=file_path,
                        module_name=module_name,
                    )
                )
                # Only take the first __main__ block per file
                break

    return main_blocks


def _extract_main_block_regex(source: str) -> str:
    """Extract __main__ block using regex (fallback method).

    Args:
        source: Source code to search

    Returns:
        Extracted block content, or empty string if not found
    """
    # Pattern matches: if __name__ == '__main__': ... (to end of file)
    # Using (?s) for dotall mode (match newlines)
    pattern = (
        r"(?s)(if\s+__name__\s*==\s*[\"']__main__[\"']\s*:\s*\n.*?)"
        r"(?=\n\n|\n[A-Za-z_#@]|\Z)"
    )
    match = re.search(pattern, source)
    if match:
        return match.group(1).rstrip()
    return ""


def select_main_block(
    *,
    main_blocks: list[MainBlock],
    main_function_result: tuple[str, Path, str] | None,
    file_paths: list[Path],
    module_names: list[str],  # noqa: ARG001
) -> MainBlock | None:
    """Select which __main__ block to keep based on priority.

    Priority order:
    1. Block in same module/file as main function
    2. Block in same package as main function
    3. Block in earliest include (by include order)

    Args:
        main_blocks: List of all detected __main__ blocks
        main_function_result: Result from find_main_function()
            (function_name, file_path, module_path) or None
        file_paths: List of file paths in include order
        module_names: List of module names in include order
            (unused, kept for API consistency)

    Returns:
        Selected MainBlock to keep, or None if no block should be kept
    """
    if not main_blocks:
        return None

    # If we have a main function, use it to determine priority
    if main_function_result is not None:
        _function_name, main_file_path, main_module_path = main_function_result

        # Priority 1: Block in same module/file as main function
        for block in main_blocks:
            if block.file_path == main_file_path:
                return block

        # Priority 2: Block in same package as main function
        # Extract package from main_module_path (everything before last dot)
        if "." in main_module_path:
            main_package = main_module_path.rsplit(".", 1)[0]
            for block in main_blocks:
                if block.module_name == main_package or block.module_name.startswith(
                    f"{main_package}."
                ):
                    return block

    # Priority 3: Block in earliest include (by include order)
    # Build mapping from file paths to their index in include order
    file_to_index = {file_path: i for i, file_path in enumerate(file_paths)}

    # Find block with earliest file index
    earliest_block: MainBlock | None = None
    earliest_index = len(file_paths)  # Start with max index

    for block in main_blocks:
        block_index = file_to_index.get(block.file_path, len(file_paths))
        if block_index < earliest_index:
            earliest_index = block_index
            earliest_block = block

    return earliest_block


@dataclass
class FunctionCollision:
    """Represents a function name collision.

    Attributes:
        module_name: Module name where the collision occurs
        function_name: Name of the colliding function
        is_main: Whether this is the main function (should not be renamed)
    """

    module_name: str
    function_name: str
    is_main: bool


def detect_collisions(
    *,
    main_function_result: tuple[str, Path, str] | None,
    module_sources: dict[str, str],
    module_names: list[str],
) -> list[FunctionCollision]:
    """Detect function name collisions with the main function.

    After module actions are applied, check if multiple functions exist
    with the same name as the main function.

    Args:
        main_function_result: Result from find_main_function()
            (function_name, file_path, module_path) or None
        module_sources: Mapping of module name to source code
        module_names: List of module names in order

    Returns:
        List of FunctionCollision objects for all functions with the same name
        as the main function. The main function itself is marked with is_main=True.
    """
    if main_function_result is None:
        return []

    main_function_name, _main_file_path, main_module_path = main_function_result

    collisions: list[FunctionCollision] = []

    # Search all modules for functions with the same name
    for module_name in sorted(module_names):
        module_key = f"{module_name}.py"
        if module_key not in module_sources:
            continue

        source = module_sources[module_key]
        func_node = _find_function_in_source(source, main_function_name)
        if func_node is not None:
            is_main = module_name == main_module_path
            collisions.append(
                FunctionCollision(
                    module_name=module_name,
                    function_name=main_function_name,
                    is_main=is_main,
                )
            )

    return collisions


def rename_function_in_source(source: str, old_name: str, new_name: str) -> str:
    """Rename a function definition in source code.

    Only renames the function definition, not calls to the function.
    Uses AST to find and rename the function definition.

    Args:
        source: Python source code
        old_name: Current function name
        new_name: New function name

    Returns:
        Modified source code with function renamed
    """
    try:
        tree = ast.parse(source)
        # Find the function definition and rename it
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == old_name
            ):
                node.name = new_name
                break

        # Convert back to source code
        # Use ast.unparse if available (Python 3.9+), otherwise use regex fallback
        try:
            unparsed = ast.unparse(tree)
            # ast.unparse removes leading whitespace, so if the original had
            # indentation, we need to preserve it. For module-level functions,
            # this shouldn't be an issue, but we check anyway.
            # If the original source had the function at column 0, unparsed should too
            stripped_source = source.strip()
            if stripped_source.startswith(("def ", "async def ")):
                # Module-level function - unparsed should be correct
                return unparsed
            # Otherwise, try to preserve indentation from original
            # Find the indentation of the function in the original source
            lines = source.splitlines()
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith(("def ", "async def ")) and old_name in stripped:
                    indent = line[: len(line) - len(stripped)]
                    # Apply same indentation to unparsed result
                    unparsed_lines = unparsed.splitlines()
                    if unparsed_lines:
                        # Find the function definition line in unparsed
                        for i, unparsed_line in enumerate(unparsed_lines):
                            if new_name in unparsed_line and unparsed_line.startswith(
                                ("def ", "async def ")
                            ):
                                unparsed_lines[i] = indent + unparsed_line.lstrip()
                                return "\n".join(unparsed_lines)
                    break
            # If loop completes (with or without break), return unparsed
            return unparsed  # noqa: TRY300
        except AttributeError:
            # Python < 3.9: use regex fallback
            # Match function definition with any indentation
            pattern = rf"^(\s*)(async\s+)?def\s+{re.escape(old_name)}\s*\("
            replacement = rf"\1\2def {new_name}("
            return re.sub(pattern, replacement, source, flags=re.MULTILINE)
    except (SyntaxError, ValueError):
        # If parsing fails, return original source
        return source


def generate_auto_renames(
    *,
    collisions: list[FunctionCollision],
    main_function_result: tuple[str, Path, str],
) -> dict[str, str]:
    """Generate auto-rename mappings for colliding functions.

    Creates rename mappings for all colliding functions except the main one.
    Renames to main_1, main_2, etc.

    Args:
        collisions: List of all function collisions
        main_function_result: Result from find_main_function()
            (function_name, file_path, module_path)

    Returns:
        Dictionary mapping module_name -> new_function_name for functions
        that should be renamed. Only includes non-main functions.
    """
    main_function_name, _main_file_path, _main_module_path = main_function_result

    # Filter out the main function itself
    non_main_collisions = [c for c in collisions if not c.is_main]

    if not non_main_collisions:
        return {}

    # Generate rename mappings: main_1, main_2, etc.
    renames: dict[str, str] = {}
    counter = 1
    for collision in sorted(non_main_collisions, key=lambda c: c.module_name):
        new_name = f"{main_function_name}_{counter}"
        renames[collision.module_name] = new_name
        counter += 1

    return renames
