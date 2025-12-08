# src/serger/config/config_types.py


from pathlib import Path
from typing import Literal, TypedDict

from typing_extensions import NotRequired


OriginType = Literal["cli", "config", "plugin", "default", "code", "gitignore", "test"]


InternalImportMode = Literal["force_strip", "strip", "keep", "assign"]
ExternalImportMode = Literal["force_top", "top", "keep", "force_strip", "strip"]
StitchMode = Literal["raw", "class", "exec"]
ModuleMode = Literal[
    "none", "multi", "force", "force_flat", "unify", "unify_preserve", "flat"
]
ShimSetting = Literal["all", "public", "none"]
MainMode = Literal["none", "auto"]
# Module actions configuration types
ModuleActionType = Literal["move", "copy", "delete", "rename", "none"]
ModuleActionMode = Literal["preserve", "flatten"]
ModuleActionScope = Literal["original", "shim"]
ModuleActionAffects = Literal["shims", "stitching", "both"]
ModuleActionCleanup = Literal["auto", "error", "ignore"]


class ModuleActionFull(TypedDict, total=False):
    source: str  # required
    source_path: NotRequired[str]  # optional filesystem path
    dest: NotRequired[str]  # required for move/copy
    action: NotRequired[ModuleActionType]  # default: "move"
    mode: NotRequired[ModuleActionMode]  # default: "preserve"
    # default: "shim" for user, "original" for mode-generated
    scope: NotRequired[ModuleActionScope]
    affects: NotRequired[ModuleActionAffects]  # default: "shims"
    cleanup: NotRequired[ModuleActionCleanup]  # default: "auto"


# Simple format: dict[str, str | None]
ModuleActionSimple = dict[str, str | None]

# Union type for config
ModuleActions = ModuleActionSimple | list[ModuleActionFull]

CommentsMode = Literal["keep", "ignores", "inline", "strip"]
# DocstringMode can be a simple string mode or a dict for per-location control
DocstringModeSimple = Literal["keep", "strip", "public"]
DocstringModeLocation = Literal["module", "class", "function", "method"]
DocstringMode = DocstringModeSimple | dict[DocstringModeLocation, DocstringModeSimple]


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


class RootConfig(TypedDict, total=False):
    include: list[str | IncludeConfig]
    exclude: list[str]

    # Optional per-build overrides
    strict_config: bool
    out: str
    respect_gitignore: bool
    log_level: str

    # Runtime behavior
    watch_interval: float
    post_processing: PostProcessingConfig  # Post-processing configuration

    # Pyproject.toml integration
    use_pyproject_metadata: bool  # Whether to pull metadata from pyproject.toml
    pyproject_path: str  # Path to pyproject.toml (overrides root default)

    # Version (overrides pyproject version)
    version: str  # Version string (optional, falls back to pyproject.toml if not set)

    # Stitching configuration
    package: str  # Package name for imports (e.g., "serger")
    # Explicit module order for stitching (optional; auto-discovered if not provided)
    order: list[str]
    # License text or dict with file/text/expression
    license: str | dict[str, str | list[str]]
    license_files: list[str]  # Additional license files (glob patterns)
    display_name: str  # Display name for header (defaults to package)
    description: str  # Description for header (defaults to blank)
    authors: str  # Authors for header (optional, can fallback to pyproject.toml)
    repo: str  # Repository URL for header (optional)
    custom_header: str  # Custom header text (overrides display_name/description)
    file_docstring: str  # Custom file docstring (overrides auto-generated docstring)
    # Import handling configuration
    internal_imports: InternalImportMode  # How to handle internal package imports
    external_imports: ExternalImportMode  # How to handle external imports
    # Stitching mode: how to combine modules into a single file
    # - "raw": Concatenate all files together (default)
    # - "class": Namespace files within classes (not yet implemented)
    # - "exec": Namespace files within module shims using exec() (not yet implemented)
    stitch_mode: StitchMode
    # Module mode: how to generate import shims for stitched runtime
    # - "none": No shims generated
    # - "multi": Generate shims for all detected packages (default)
    # - "force": Replace root package but keep subpackages (e.g., pkg1.sub -> mypkg.sub)
    # - "force_flat": Flatten everything to configured package (e.g., pkg1.sub -> mypkg)
    # - "unify": Place all detected packages under package, combine if package matches
    # - "unify_preserve": Like unify but preserves structure when package matches
    # - "flat": Treat loose files as top-level modules (not under package)
    module_mode: ModuleMode
    # Shim setting: controls whether shims are generated and which modules get shims
    # - "all": Generate shims for all modules (default)
    # - "public": Only generate shims for public modules
    #   (future: based on _ prefix or __all__)
    # - "none": Don't generate shims at all
    shim: ShimSetting
    # Module actions: custom module transformations (move, copy, delete)
    # - dict[str, str | None]: Simple format mapping source -> dest
    # - list[ModuleActionFull]: Full format with detailed options
    module_actions: NotRequired[ModuleActions]
    # Comments mode: how to handle comments in stitched output
    # - "keep": Keep all comments (default)
    # - "ignores": Only keep comments that specify ignore rules
    #   (e.g., "noqa:", "type: ignore")
    # - "inline": Only keep inline comments (comments on the same line as code)
    # - "strip": Remove all comments
    comments_mode: CommentsMode
    # Docstring mode: how to handle docstrings in stitched output
    # - "keep": Keep all docstrings (default)
    # - "strip": Remove all docstrings
    # - "public": Keep only public docstrings (not prefixed with underscore)
    # - dict: Per-location control, e.g., {"module": "keep", "class": "strip"}
    #   Valid locations: "module", "class", "function", "method"
    #   Each location value can be "keep", "strip", or "public"
    #   Omitted locations default to "keep"
    docstring_mode: DocstringMode
    # Source bases: ordered list of directories where packages can be found
    # - str: Single directory (convenience, converted to list[str] on resolve)
    # - list[str]: Ordered list of directories (default: ["src", "lib", "packages"])
    source_bases: str | list[str]
    # Installed packages bases: ordered list of directories where installed packages
    # can be found (for "follow the imports" stitching)
    # - str: Single directory (convenience, converted to list[str] on resolve)
    # - list[str]: Ordered list of directories (default: auto-discovered if enabled)
    installed_bases: NotRequired[str | list[str]]
    # Auto-discover installed packages: whether to automatically discover
    # installed package roots (default: True)
    auto_discover_installed_packages: NotRequired[bool]
    # Include installed dependencies: whether to include installed dependencies
    # in "follow the imports" stitching (default: False)
    include_installed_dependencies: NotRequired[bool]
    # Main function configuration
    # - "none": Don't generate __main__ block
    # - "auto": Automatically detect and generate __main__ block (default)
    main_mode: NotRequired[MainMode]
    # Main function name specification
    # - None: Auto-detect main function (default)
    # - str: Explicit main function specification (see docs for syntax)
    main_name: NotRequired[str | None]
    # Build timestamp control
    # - False: Use real timestamps (default)
    # - True: Use placeholder for deterministic builds
    disable_build_timestamp: NotRequired[bool]
    # Max lines to check when detecting serger builds
    # - int: Override the default line limit for checking "# Build Tool: serger"
    #   (default: 200)
    build_tool_find_max_lines: NotRequired[int]


class RootConfigResolved(TypedDict):
    include: list[IncludeResolved]
    exclude: list[PathResolved]

    # Optional per-build overrides
    strict_config: bool
    out: PathResolved
    respect_gitignore: bool
    log_level: str

    # Runtime behavior
    watch_interval: float

    # Runtime flags (CLI only, not persisted in normal configs)
    dry_run: bool
    validate: bool

    # Global provenance (optional, for audit/debug)
    __meta__: MetaBuildConfigResolved

    # Internal metadata fields (not user-configurable)
    version: NotRequired[str]  # Version (user -> pyproject, resolved in config)

    # Stitching fields (optional - present if this is a stitch build)
    package: NotRequired[str]
    order: NotRequired[list[str]]
    # Metadata fields (optional, resolved to user -> pyproject -> None)
    license: str  # License text (mandatory, always present with fallback)
    display_name: NotRequired[str]
    description: NotRequired[str]
    authors: NotRequired[str]
    repo: NotRequired[str]
    custom_header: NotRequired[str]  # Custom header (overrides display_name)
    file_docstring: NotRequired[str]  # Custom docstring (overrides auto-generated)
    post_processing: PostProcessingConfigResolved  # Post-processing configuration
    internal_imports: InternalImportMode  # How to handle internal imports
    external_imports: ExternalImportMode  # How to handle external imports
    stitch_mode: StitchMode  # How to combine modules into a single file
    module_mode: ModuleMode  # How to generate import shims for stitched runtime
    shim: ShimSetting  # Controls shim generation and which modules get shims
    # Module transformations (normalized to list format, always present)
    module_actions: list[ModuleActionFull]
    comments_mode: CommentsMode  # How to handle comments in stitched output
    docstring_mode: DocstringMode  # How to handle docstrings in stitched output
    # Source bases: ordered list of directories where packages can be found
    # (always present, resolved to list[str])
    source_bases: list[str]
    # Installed packages bases: ordered list of directories where installed packages
    # can be found (always present, resolved to list[str])
    installed_bases: list[str]
    # Auto-discover installed packages (always present, resolved with defaults)
    auto_discover_installed_packages: bool
    # Include installed dependencies (always present, resolved with defaults)
    include_installed_dependencies: bool
    # Main function configuration (always present, resolved with defaults)
    main_mode: MainMode
    # Main function name specification (always present, resolved with defaults)
    main_name: str | None
    # Build timestamp control (always present, resolved with defaults)
    disable_build_timestamp: bool
    # Max lines to check when detecting serger builds
    # (always present, resolved with defaults)
    build_tool_find_max_lines: int
