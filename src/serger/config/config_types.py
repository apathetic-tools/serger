# src/serger/config/config_types.py


from pathlib import Path
from typing import Literal, TypedDict

from typing_extensions import NotRequired


OriginType = Literal["cli", "config", "plugin", "default", "code", "gitignore", "test"]

# default: force_strip
# Implemented: "force_strip", "keep", "strip", "assign"
InternalImportMode = Literal["force_strip", "strip", "keep", "assign"]
# default: force_top
# Implemented: "force_top", "top", "keep", "force_strip", "strip"
# Not yet implemented: "assign"
ExternalImportMode = Literal[
    "force_top", "top", "keep", "force_strip", "strip", "assign"
]


# Post-processing configuration types
class ToolConfig(TypedDict, total=False):
    command: str  # executable name (optional - defaults to key if missing)
    args: list[str]  # command arguments (optional, replaces defaults)
    path: str  # custom executable path
    options: list[str]  # additional CLI arguments (appends to args)


class PostCategoryConfig(TypedDict, total=False):
    enabled: bool  # default: True
    priority: list[str]  # tool names in priority order
    tools: NotRequired[dict[str, ToolConfig]]  # per-tool overrides


class PostProcessingConfig(TypedDict, total=False):
    enabled: bool  # master switch, default: True
    category_order: list[str]  # order to run categories
    categories: NotRequired[dict[str, PostCategoryConfig]]  # category definitions


# Resolved types - all fields are guaranteed to be present with final values
class ToolConfigResolved(TypedDict):
    command: str  # executable name (defaults to tool_label if not specified)
    args: list[str]  # command arguments (always present)
    path: str | None  # custom executable path (None if not specified)
    options: list[str]  # additional CLI arguments (empty list if not specified)


class PostCategoryConfigResolved(TypedDict):
    enabled: bool  # always present
    priority: list[str]  # always present (may be empty)
    tools: dict[str, ToolConfigResolved]  # always present (may be empty dict)


class PostProcessingConfigResolved(TypedDict):
    enabled: bool
    category_order: list[str]
    categories: dict[str, PostCategoryConfigResolved]


class PathResolved(TypedDict):
    path: Path | str  # absolute or relative to `root`, or a pattern
    root: Path  # canonical origin directory for resolution
    pattern: NotRequired[str]  # the original pattern matching this path

    # meta only
    origin: OriginType  # provenance


class IncludeResolved(PathResolved):
    dest: NotRequired[Path]  # optional override for target name


class MetaBuildConfigResolved(TypedDict):
    # sources of parameters
    cli_root: Path
    config_root: Path


class IncludeConfig(TypedDict):
    path: str
    dest: NotRequired[str]


class BuildConfig(TypedDict, total=False):
    include: list[str | IncludeConfig]
    exclude: list[str]

    # optional per-build override
    strict_config: bool
    out: str
    respect_gitignore: bool
    log_level: str

    # Single-build convenience (propagated upward)
    watch_interval: float
    post_processing: PostProcessingConfig  # Post-processing configuration

    # Pyproject.toml integration
    use_pyproject: bool  # Whether to pull metadata from pyproject.toml
    pyproject_path: str  # Path to pyproject.toml (overrides root default)

    # Stitching configuration
    package: str  # Package name for imports (e.g., "serger")
    # Explicit module order for stitching (optional; auto-discovered if not provided)
    order: list[str]
    license_header: str  # License header text for stitched output
    display_name: str  # Display name for header (defaults to package)
    description: str  # Description for header (defaults to blank)
    repo: str  # Repository URL for header (optional)
    # Import handling configuration
    internal_imports: InternalImportMode  # How to handle internal package imports
    external_imports: ExternalImportMode  # How to handle external imports


class RootConfig(TypedDict, total=False):
    builds: list[BuildConfig]

    # Defaults that cascade into each build
    log_level: str
    out: str
    respect_gitignore: bool

    # runtime behavior
    strict_config: bool
    watch_interval: float
    post_processing: PostProcessingConfig  # Post-processing configuration

    # Pyproject.toml integration
    use_pyproject: bool  # Whether to pull metadata from pyproject.toml (default: true)
    pyproject_path: str  # Path to pyproject.toml (fallback for single builds)

    # Import handling defaults (cascade into builds)
    internal_imports: InternalImportMode  # How to handle internal package imports
    external_imports: ExternalImportMode  # How to handle external imports


class BuildConfigResolved(TypedDict):
    include: list[IncludeResolved]
    exclude: list[PathResolved]

    # optional per-build override
    strict_config: bool
    out: PathResolved
    respect_gitignore: bool
    log_level: str

    # runtime flag (CLI only, not persisted in normal configs)
    dry_run: bool

    # global provenance (optional, for audit/debug)
    __meta__: MetaBuildConfigResolved

    # Stitching fields (optional - present if this is a stitch build)
    package: NotRequired[str]
    order: NotRequired[list[str]]
    license_header: NotRequired[str]
    display_name: NotRequired[str]
    description: NotRequired[str]
    repo: NotRequired[str]
    post_processing: NotRequired[
        PostProcessingConfigResolved
    ]  # Post-processing configuration
    internal_imports: NotRequired[InternalImportMode]  # How to handle internal imports
    external_imports: NotRequired[ExternalImportMode]  # How to handle external imports


class RootConfigResolved(TypedDict):
    builds: list[BuildConfigResolved]

    # runtime behavior
    log_level: str
    strict_config: bool
    watch_interval: float
    post_processing: PostProcessingConfigResolved
