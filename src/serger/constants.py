# src/serger/constants.py
"""Central constants used across the project."""

from typing import Any


RUNTIME_MODES = {
    "standalone",  # single stitched file
    "installed",  # poetry-installed / pip-installed / importable
    "zipapp",  # .pyz bundle
}

# --- env keys ---
DEFAULT_ENV_LOG_LEVEL: str = "LOG_LEVEL"
DEFAULT_ENV_RESPECT_GITIGNORE: str = "RESPECT_GITINGORE"
DEFAULT_ENV_WATCH_INTERVAL: str = "WATCH_INTERVAL"

# --- program defaults ---
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_WATCH_INTERVAL: float = 1.0  # seconds
DEFAULT_RESPECT_GITIGNORE: bool = True

# --- config defaults ---
DEFAULT_STRICT_CONFIG: bool = True
DEFAULT_OUT_DIR: str = "dist"
DEFAULT_DRY_RUN: bool = False
DEFAULT_USE_PYPROJECT: bool = True
DEFAULT_INTERNAL_IMPORTS: str = "strip"  # Remove internal imports (current behavior)
DEFAULT_EXTERNAL_IMPORTS: str = "top"  # Hoist external imports to top

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
