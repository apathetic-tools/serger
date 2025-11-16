# src/serger/main_config.py
"""Main function configuration and detection logic.

This module handles parsing of main_name configuration, finding main functions,
and managing __main__ block generation.
"""


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
