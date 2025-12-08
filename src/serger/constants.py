# src/serger/constants.py
"""Central constants used across the project."""

from typing import Any


RUNTIME_MODES = {
    "stitched",  # single concatenated file wiht module-shims
    "package",  # poetry-installed / pip-installed / importable
    "zipapp",  # .pyz bundle
}

# --- env keys ---
DEFAULT_ENV_LOG_LEVEL: str = "LOG_LEVEL"
DEFAULT_ENV_RESPECT_GITIGNORE: str = "RESPECT_GITIGNORE"
DEFAULT_ENV_WATCH_INTERVAL: str = "WATCH_INTERVAL"
DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP: str = "DISABLE_BUILD_TIMESTAMP"

# --- program defaults ---
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_WATCH_INTERVAL: float = 1.0  # seconds
DEFAULT_RESPECT_GITIGNORE: bool = True

# --- config defaults ---
DEFAULT_STRICT_CONFIG: bool = True
DEFAULT_OUT_DIR: str = "dist"
DEFAULT_DRY_RUN: bool = False
DEFAULT_USE_PYPROJECT_METADATA: bool = True

# Import handling defaults keyed by stitch mode
# These defaults are chosen based on how each stitching mode works:

# INTERNAL_IMPORTS:
#   - "raw": "force_strip" - Raw mode concatenates all files into a single namespace.
#     Internal imports (e.g., "from .utils import helper") are stripped because all
#     code is in the same namespace and can reference each other directly.
#   - "class": "assign" - Class mode wraps each module in a class namespace.
#     Internal imports must be transformed to class attribute access (e.g.,
#     "from .utils import helper" becomes "helper = _Module_utils.helper").
#     The "assign" mode handles this transformation automatically.
#   - "exec": "keep" - Exec mode uses exec() with separate module objects in
#     sys.modules, each with proper __package__ attributes. Relative imports work
#     correctly in this setup, so they should be kept as-is.
DEFAULT_INTERNAL_IMPORTS: dict[str, str] = {
    "raw": "force_strip",
    "class": "assign",
    "exec": "keep",
}

# EXTERNAL_IMPORTS:
#   - All modes use "top" - External imports (e.g., "import os", "from pathlib
#     import Path") must be available at module level for all stitching modes.
#     Hoisting them to the top ensures they're accessible throughout the stitched
#     file, whether code is concatenated (raw), wrapped in classes (class), or
#     executed in separate namespaces (exec).
DEFAULT_EXTERNAL_IMPORTS: dict[str, str] = {
    "raw": "top",
    "class": "top",
    "exec": "top",
}
DEFAULT_STITCH_MODE: str = "raw"  # Raw concatenation (default stitching mode)
DEFAULT_MODULE_MODE: str = "multi"  # Generate shims for all detected packages
DEFAULT_SHIM: str = "all"  # Generate shims for all modules (default shim setting)
DEFAULT_COMMENTS_MODE: str = "keep"  # Keep all comments (default comments mode)
DEFAULT_DOCSTRING_MODE: str = "keep"  # Keep all docstrings (default docstring mode)
DEFAULT_SOURCE_BASES: list[str] = [
    "src",
    "lib",
    "packages",
]  # Default directories to search for packages
DEFAULT_MAIN_MODE: str = "auto"  # Automatically detect and generate __main__ block
DEFAULT_MAIN_NAME: str | None = None  # Auto-detect main function (default)
DEFAULT_DISABLE_BUILD_TIMESTAMP: bool = False  # Use real timestamps by default
BUILD_TIMESTAMP_PLACEHOLDER: str = "<build-timestamp>"  # Placeholder
DEFAULT_LICENSE_FALLBACK: str = (
    "All rights reserved. See additional license files if distributed "
    "alongside this file for additional terms."
)

# --- build detection defaults ---
# Lines to read when checking for "# Build Tool: serger" comment
BUILD_TOOL_FIND_MAX_LINES: int = 200

# --- post-processing defaults ---
DEFAULT_CATEGORY_ORDER: list[str] = ["static_checker", "formatter", "import_sorter"]

# Type: dict[str, dict[str, Any]] - matches PostCategoryConfig structure
# All tool commands are defined in tools dict for consistency (supports custom labels)
# Note: This is the raw default structure; it gets resolved to
# PostCategoryConfigResolved
DEFAULT_CATEGORIES: dict[str, dict[str, Any]] = {
    "static_checker": {
        "enabled": True,
        "priority": ["ruff"],
        "tools": {
            "ruff": {
                "args": ["check", "--fix"],
            },
        },
    },
    "formatter": {
        "enabled": True,
        "priority": ["ruff", "black"],
        "tools": {
            "ruff": {
                "args": ["format"],
            },
            "black": {
                "args": ["format"],
            },
        },
    },
    "import_sorter": {
        "enabled": True,
        "priority": ["ruff", "isort"],
        "tools": {
            "ruff": {
                "args": ["check", "--select", "I", "--fix"],
            },
            "isort": {
                "args": ["--fix"],
            },
        },
    },
}
