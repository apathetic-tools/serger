# src/serger/main_config.py
"""Main function configuration and detection logic.

This module handles parsing of main_name configuration, finding main functions,
and managing __main__ block generation.
"""

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from serger.utils.utils_modules import derive_module_name


if TYPE_CHECKING:
    from serger.config import IncludeResolved, RootConfigResolved


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


def find_main_function(  # noqa: PLR0912
    *,
    config: "RootConfigResolved",
    file_paths: list[Path],
    module_sources: dict[str, str],
    module_names: list[str],
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
        module_names: List of module names in order
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

    module_to_file: dict[str, Path] = {}
    for file_path in file_paths:
        include = file_to_include.get(file_path)
        module_name = derive_module_name(file_path, package_root, include)

        # If package_root is a package directory, preserve package structure
        if is_package_dir and package_name_from_root:
            # Handle __init__.py special case: represents the package itself
            if file_path.name == "__init__.py" and file_path.parent == package_root:
                module_name = package_name_from_root
            else:
                # Prepend package name to preserve structure
                module_name = f"{package_name_from_root}.{module_name}"

        module_to_file[module_name] = file_path

    # Parse main_name to get module path and function name
    module_path_spec, function_name = parse_main_name(main_name)

    # Search strategy based on what's specified
    search_candidates: list[tuple[str, Path]] = []

    if main_name is not None:
        # main_name is set: use it
        if module_path_spec is not None:
            # Module path specified: search in that module/package
            # Match modules that start with the specified path
            search_candidates.extend(
                (mod_name, module_to_file[mod_name])
                for mod_name in sorted(module_names)
                if (
                    (
                        mod_name == module_path_spec
                        or mod_name.startswith(f"{module_path_spec}.")
                    )
                    and mod_name in module_to_file
                )
            )
        else:
            # Function name only: search across all packages
            search_candidates.extend(
                (mod_name, module_to_file[mod_name])
                for mod_name in sorted(module_names)
                if mod_name in module_to_file
            )
    elif package is not None:
        # main_name is None, but package is set: search in that package
        search_candidates.extend(
            (mod_name, module_to_file[mod_name])
            for mod_name in sorted(module_names)
            if (
                (mod_name == package or mod_name.startswith(f"{package}."))
                and mod_name in module_to_file
            )
        )
    # No main_name and no package: search in first package from include order
    elif detected_packages:
        first_package = sorted(detected_packages)[0]
        search_candidates.extend(
            (mod_name, module_to_file[mod_name])
            for mod_name in sorted(module_names)
            if (
                (mod_name == first_package or mod_name.startswith(f"{first_package}."))
                and mod_name in module_to_file
            )
        )
    else:
        # No packages detected: search all modules
        search_candidates.extend(
            (mod_name, module_to_file[mod_name])
            for mod_name in sorted(module_names)
            if mod_name in module_to_file
        )

    # Sort candidates by file priority
    # (__main__.py first, then __init__.py, then others)
    # Then by module name for determinism
    search_candidates.sort(key=lambda x: (_get_file_priority(x[1]), x[0]))

    # Search for function in candidates
    for mod_name, file_path in search_candidates:
        # Get module source (key includes .py suffix)
        module_key = f"{mod_name}.py"
        if module_key not in module_sources:
            continue

        source = module_sources[module_key]
        func_node = _find_function_in_source(source, function_name)
        if func_node is not None:
            return (function_name, file_path, mod_name)

    # Not found
    return None
