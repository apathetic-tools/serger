# src/serger/config/config_resolve.py


import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from serger.constants import (
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ORDER,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_USE_PYPROJECT,
    DEFAULT_WATCH_INTERVAL,
)
from serger.logs import get_app_logger
from serger.utils import (
    cast_hint,
    has_glob_chars,
    load_toml,
    make_includeresolved,
    make_pathresolved,
)

from .config_types import (
    BuildConfig,
    BuildConfigResolved,
    IncludeResolved,
    MetaBuildConfigResolved,
    OriginType,
    PathResolved,
    PostCategoryConfigResolved,
    PostProcessingConfig,
    PostProcessingConfigResolved,
    RootConfig,
    RootConfigResolved,
    ToolConfig,
    ToolConfigResolved,
)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


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


def _should_use_pyproject(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    num_builds: int,
) -> bool:
    """Determine if pyproject.toml should be used for this build.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)
        num_builds: Number of builds in root config

    Returns:
        True if pyproject.toml should be used, False otherwise
    """
    build_use_pyproject = build_cfg.get("use_pyproject")
    root_use_pyproject = (root_cfg or {}).get("use_pyproject")
    build_pyproject_path = build_cfg.get("pyproject_path")

    # Determine if this build has opted in
    build_opted_in = False
    if isinstance(build_use_pyproject, bool):
        build_opted_in = build_use_pyproject
    elif build_pyproject_path:
        # Specifying a path is an implicit opt-in
        build_opted_in = True

    if num_builds > 1:
        # Multi-build: build must explicitly opt-in
        return build_opted_in

    # Single build: use root/default settings unless build explicitly opts out
    if isinstance(build_use_pyproject, bool):
        return build_use_pyproject
    if build_pyproject_path:
        return True
    # Use root setting or default
    if isinstance(root_use_pyproject, bool):
        return root_use_pyproject
    return DEFAULT_USE_PYPROJECT


def _resolve_pyproject_path(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
) -> Path:
    """Resolve the path to pyproject.toml file.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution

    Returns:
        Resolved path to pyproject.toml
    """
    build_pyproject_path = build_cfg.get("pyproject_path")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")

    if build_pyproject_path:
        # Build-level path takes precedence
        return (config_dir / build_pyproject_path).resolve()
    if root_pyproject_path:
        # Root-level path
        return (config_dir / root_pyproject_path).resolve()
    # Default: config_dir / "pyproject.toml" (project root)
    return config_dir / "pyproject.toml"


def _is_explicitly_requested(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
) -> bool:
    """Check if pyproject.toml was explicitly requested (not just default).

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        True if explicitly requested, False if just default behavior
    """
    build_use_pyproject = build_cfg.get("use_pyproject")
    root_use_pyproject = (root_cfg or {}).get("use_pyproject")
    build_pyproject_path = build_cfg.get("pyproject_path")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")

    return (
        isinstance(build_use_pyproject, bool)
        or build_pyproject_path is not None
        or isinstance(root_use_pyproject, bool)
        or root_pyproject_path is not None
    )


def _extract_pyproject_metadata_safe(
    pyproject_path: Path,
    *,
    explicitly_requested: bool,
) -> PyprojectMetadata:
    """Extract metadata from pyproject.toml with error handling.

    Args:
        pyproject_path: Path to pyproject.toml
        explicitly_requested: Whether pyproject was explicitly requested

    Returns:
        PyprojectMetadata object (may be empty if unavailable)

    Raises:
        RuntimeError: If explicitly requested and TOML parsing unavailable
    """
    logger = get_app_logger()

    try:
        metadata = extract_pyproject_metadata(
            pyproject_path, required=explicitly_requested
        )
    except RuntimeError as e:
        # If explicitly requested and TOML parsing unavailable, re-raise
        if explicitly_requested:
            xmsg = (
                "pyproject.toml support was explicitly requested but "
                f"TOML parsing is unavailable. {e!s}"
            )
            raise RuntimeError(xmsg) from e
        # If not explicitly requested, this shouldn't happen (should return None)
        raise

    if metadata is None:
        # TOML parsing unavailable but not explicitly requested - warn and skip
        logger.warning(
            "pyproject.toml found but TOML parsing unavailable "
            "(Python 3.10 requires 'tomli'). "
            "Skipping metadata extraction. Install 'tomli' to enable, "
            "or explicitly set 'use_pyproject: false' to disable this warning."
        )
        # Create empty metadata object
        metadata = PyprojectMetadata()

    return metadata


def _apply_metadata_fields(
    resolved_cfg: dict[str, Any],
    metadata: PyprojectMetadata,
    pyproject_path: Path,
) -> None:
    """Apply extracted metadata fields to resolved config.

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        metadata: Extracted metadata
        pyproject_path: Path to pyproject.toml (for logging)
    """
    logger = get_app_logger()

    # Fill in missing fields (only if not already set in config)
    if metadata.version and not resolved_cfg.get("version"):
        # Note: version is not a build config field, but we'll store it
        # for use in build.py later
        resolved_cfg["_pyproject_version"] = metadata.version

    if metadata.name and not resolved_cfg.get("display_name"):
        resolved_cfg["display_name"] = metadata.name

    if metadata.description and not resolved_cfg.get("description"):
        resolved_cfg["description"] = metadata.description

    if metadata.license_text and not resolved_cfg.get("license_header"):
        resolved_cfg["license_header"] = metadata.license_text

    if metadata.has_any():
        logger.trace(f"[resolve_build_config] Extracted metadata from {pyproject_path}")


def _apply_pyproject_metadata(
    resolved_cfg: dict[str, Any],
    *,
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
    num_builds: int,
) -> None:
    """Extract and apply pyproject.toml metadata to resolved config.

    Handles all the logic for determining when to use pyproject.toml,
    path resolution, and filling in missing fields.

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        build_cfg: Original build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution
        num_builds: Number of builds in the root config
    """
    if not _should_use_pyproject(build_cfg, root_cfg, num_builds):
        return

    pyproject_path = _resolve_pyproject_path(build_cfg, root_cfg, config_dir)
    explicitly_requested = _is_explicitly_requested(build_cfg, root_cfg)

    metadata = _extract_pyproject_metadata_safe(
        pyproject_path, explicitly_requested=explicitly_requested
    )
    _apply_metadata_fields(resolved_cfg, metadata, pyproject_path)


def _load_gitignore_patterns(path: Path) -> list[str]:
    """Read .gitignore and return non-comment patterns."""
    patterns: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            clean_line = line.strip()
            if clean_line and not clean_line.startswith("#"):
                patterns.append(clean_line)
    return patterns


def _merge_post_processing(  # noqa: C901, PLR0912, PLR0915
    build_cfg: PostProcessingConfig | None,
    root_cfg: PostProcessingConfig | None,
) -> PostProcessingConfig:
    """Deep merge post-processing configs: build-level → root-level → default.

    Args:
        build_cfg: Build-level post-processing config (may be None)
        root_cfg: Root-level post-processing config (may be None)

    Returns:
        Merged post-processing config
    """
    # Start with defaults
    merged: PostProcessingConfig = {
        "enabled": True,
        "category_order": list(DEFAULT_CATEGORY_ORDER),
        "categories": {
            cat: {
                "enabled": bool(cfg.get("enabled", True)),
                "priority": (
                    list(cast("list[str]", cfg["priority"]))
                    if isinstance(cfg.get("priority"), list)
                    else []
                ),
            }
            for cat, cfg in DEFAULT_CATEGORIES.items()
        },
    }

    # Merge root-level config
    if root_cfg:
        if "enabled" in root_cfg:
            merged["enabled"] = root_cfg["enabled"]
        if "category_order" in root_cfg:
            merged["category_order"] = list(root_cfg["category_order"])

        if "categories" in root_cfg:
            if "categories" not in merged:
                merged["categories"] = {}
            for cat_name, cat_cfg in root_cfg["categories"].items():
                if cat_name not in merged["categories"]:
                    merged["categories"][cat_name] = {}
                # Merge category config
                merged_cat = merged["categories"][cat_name]
                if "enabled" in cat_cfg:
                    merged_cat["enabled"] = cat_cfg["enabled"]
                if "priority" in cat_cfg:
                    merged_cat["priority"] = list(cat_cfg["priority"])
                if "tools" in cat_cfg:
                    if "tools" not in merged_cat:
                        merged_cat["tools"] = {}
                    # Tool options replace (don't merge)
                    for tool_name, tool_override in cat_cfg["tools"].items():
                        root_override_dict: dict[str, object] = {}
                        if "command" in tool_override:
                            root_override_dict["command"] = tool_override["command"]
                        if "args" in tool_override:
                            root_override_dict["args"] = list(tool_override["args"])
                        if "path" in tool_override:
                            root_override_dict["path"] = tool_override["path"]
                        if "options" in tool_override:
                            root_override_dict["options"] = list(
                                tool_override["options"]
                            )
                        merged_cat["tools"][tool_name] = cast_hint(
                            ToolConfig, root_override_dict
                        )

    # Merge build-level config (overrides root)
    if build_cfg:
        if "enabled" in build_cfg:
            merged["enabled"] = build_cfg["enabled"]
        if "category_order" in build_cfg:
            merged["category_order"] = list(build_cfg["category_order"])

        if "categories" in build_cfg:
            if "categories" not in merged:
                merged["categories"] = {}
            for cat_name, cat_cfg in build_cfg["categories"].items():
                if cat_name not in merged["categories"]:
                    merged["categories"][cat_name] = {}
                # Merge category config
                merged_cat = merged["categories"][cat_name]
                if "enabled" in cat_cfg:
                    merged_cat["enabled"] = cat_cfg["enabled"]
                if "priority" in cat_cfg:
                    merged_cat["priority"] = list(cat_cfg["priority"])
                if "tools" in cat_cfg:
                    if "tools" not in merged_cat:
                        merged_cat["tools"] = {}
                    # Tool options replace (don't merge)
                    for tool_name, tool_override in cat_cfg["tools"].items():
                        build_override_dict: dict[str, object] = {}
                        if "command" in tool_override:
                            build_override_dict["command"] = tool_override["command"]
                        if "args" in tool_override:
                            build_override_dict["args"] = list(tool_override["args"])
                        if "path" in tool_override:
                            build_override_dict["path"] = tool_override["path"]
                        if "options" in tool_override:
                            build_override_dict["options"] = list(
                                tool_override["options"]
                            )
                        merged_cat["tools"][tool_name] = cast_hint(
                            ToolConfig, build_override_dict
                        )

    return merged


def resolve_post_processing(  # noqa: PLR0912, C901
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
) -> PostProcessingConfigResolved:
    """Resolve post-processing configuration with cascade and validation.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        Resolved post-processing configuration
    """
    logger = get_app_logger()

    # Extract configs
    build_post = build_cfg.get("post_processing")
    root_post = (root_cfg or {}).get("post_processing")

    # Merge configs
    merged = _merge_post_processing(
        build_post if isinstance(build_post, dict) else None,
        root_post if isinstance(root_post, dict) else None,
    )

    # Validate category_order - warn on invalid category names
    valid_categories = set(DEFAULT_CATEGORIES.keys())
    category_order = merged.get("category_order", DEFAULT_CATEGORY_ORDER)
    invalid_categories = [cat for cat in category_order if cat not in valid_categories]
    if invalid_categories:
        logger.warning(
            "Invalid category names in post_processing.category_order: %s. "
            "Valid categories are: %s",
            invalid_categories,
            sorted(valid_categories),
        )

    # Helper function to resolve a ToolConfig to ToolConfigResolved with all fields
    def _resolve_tool_config(
        tool_label: str, tool_config: ToolConfig | dict[str, Any]
    ) -> ToolConfigResolved:
        """Resolve a ToolConfig to ToolConfigResolved with all fields populated."""
        # Ensure we have a dict (ToolConfig is a TypedDict, which is a dict)
        tool_dict = cast("dict[str, Any]", tool_config)

        # Args is required - if not present, this is an error
        if "args" not in tool_dict:
            xmsg = f"Tool config for {tool_label} is missing required 'args' field"
            raise ValueError(xmsg)

        resolved: ToolConfigResolved = {
            "command": tool_dict.get("command", tool_label),
            "args": list(tool_dict["args"]),
            "path": tool_dict.get("path"),
            "options": list(tool_dict.get("options", [])),
        }
        return resolved

    # Build resolved config with all categories (even if not in category_order)
    resolved_categories: dict[str, PostCategoryConfigResolved] = {}
    for cat_name, default_cat in DEFAULT_CATEGORIES.items():
        # Start with defaults
        enabled_val = default_cat.get("enabled", True)
        priority_val = default_cat.get("priority", [])
        priority_list = (
            list(cast("list[str]", priority_val))
            if isinstance(priority_val, list)
            else []
        )

        # Build tools dict from defaults
        tools_dict: dict[str, ToolConfigResolved] = {}
        if "tools" in default_cat:
            for tool_name, tool_override in default_cat["tools"].items():
                tools_dict[tool_name] = _resolve_tool_config(tool_name, tool_override)

        # Apply merged config if present
        if "categories" in merged and cat_name in merged["categories"]:
            merged_cat = merged["categories"][cat_name]
            if "enabled" in merged_cat:
                enabled_val = merged_cat["enabled"]
            if "priority" in merged_cat:
                priority_list = list(merged_cat["priority"])
            if "tools" in merged_cat:
                # Merge tools: user config overrides defaults
                for tool_name, tool_override in merged_cat["tools"].items():
                    # Merge with existing tool config if present, otherwise use override
                    existing_tool_raw: ToolConfigResolved | dict[str, Any] = (
                        tools_dict.get(tool_name, {})
                    )
                    existing_tool: dict[str, Any] = cast(
                        "dict[str, Any]", existing_tool_raw
                    )
                    merged_tool: dict[str, Any] = dict(existing_tool)
                    # Update with user override (may be partial)
                    if isinstance(tool_override, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                        merged_tool.update(tool_override)
                    tools_dict[tool_name] = _resolve_tool_config(tool_name, merged_tool)

        # Fallback: ensure all tools in priority are in tools dict
        # If a tool is in priority but not in tools, look it up from DEFAULT_CATEGORIES
        default_tools = default_cat.get("tools", {})
        for tool_label in priority_list:
            if tool_label not in tools_dict and tool_label in default_tools:
                # Copy from defaults as fallback
                default_override = default_tools[tool_label]
                tools_dict[tool_label] = _resolve_tool_config(
                    tool_label, default_override
                )

        # Empty priority = disabled
        if not priority_list:
            enabled_val = False

        resolved_cat: PostCategoryConfigResolved = {
            "enabled": bool(enabled_val) if isinstance(enabled_val, bool) else True,
            "priority": priority_list,
            "tools": tools_dict,
        }

        resolved_categories[cat_name] = resolved_cat

    resolved: PostProcessingConfigResolved = {
        "enabled": merged.get("enabled", True),
        "category_order": list(category_order),
        "categories": resolved_categories,
    }

    return resolved


def _parse_include_with_dest(
    raw: str, context_root: Path
) -> tuple[IncludeResolved, bool]:
    """Parse include string with optional :dest suffix.

    Returns:
        (IncludeResolved, has_dest) tuple
    """
    has_dest = False
    path_str = raw
    dest_str = None

    # Handle "path:dest" format - split on last colon
    if ":" in raw:
        parts = raw.rsplit(":", 1)
        path_part, dest_part = parts[0], parts[1]

        # Check if this is a Windows drive letter (C:, D:, etc.)
        # Drive letters are 1-2 chars, possibly with backslash
        is_drive_letter = len(path_part) <= 2 and (  # noqa: PLR2004
            len(path_part) == 1 or path_part.endswith("\\")
        )

        if not is_drive_letter:
            # Valid dest separator found
            path_str = path_part
            dest_str = dest_part
            has_dest = True

    # Normalize the path
    root, rel = _normalize_path_with_root(path_str, context_root)
    inc = make_includeresolved(rel, root, "cli")

    if has_dest and dest_str:
        inc["dest"] = Path(dest_str)

    return inc, has_dest


def _normalize_path_with_root(
    raw: Path | str,
    context_root: Path | str,
) -> tuple[Path, Path | str]:
    """Normalize a user-provided path (from CLI or config).

    - If absolute → treat that path as its own root.
      * `/abs/path/**` → root=/abs/path, rel="**"
      * `/abs/path/`   → root=/abs/path, rel="**"  (treat as contents)
      * `/abs/path`    → root=/abs/path, rel="."   (treat as literal)
    - If relative → root = context_root, path = raw (preserve string form)
    """
    logger = get_app_logger()
    raw_path = Path(raw)
    rel: Path | str

    # --- absolute path case ---
    if raw_path.is_absolute():
        # Split out glob or trailing slash intent
        raw_str = str(raw)
        if raw_str.endswith("/**"):
            root = Path(raw_str[:-3]).resolve()
            rel = "**"
        elif raw_str.endswith("/"):
            root = Path(raw_str[:-1]).resolve()
            rel = "**"  # treat directory as contents
        elif has_glob_chars(raw_str):
            # Extract root directory (part before first glob char)
            # Find the last path separator before any glob character
            glob_chars = ["*", "?", "[", "{"]
            glob_pos = min(
                (raw_str.find(c) for c in glob_chars if c in raw_str),
                default=len(raw_str),
            )
            # Find the last / before the glob
            path_before_glob = raw_str[:glob_pos]
            last_slash = path_before_glob.rfind("/")
            if last_slash >= 0:
                root = Path(path_before_glob[:last_slash] or "/").resolve()
                rel = raw_str[last_slash + 1 :]  # Pattern part after root
            else:
                # No slash found, treat entire path as root
                root = Path("/").resolve()
                rel = raw_str.removeprefix("/")
        else:
            root = raw_path.resolve()
            rel = "."
    else:
        root = Path(context_root).resolve()
        # preserve literal string if user provided one
        rel = raw if isinstance(raw, str) else Path(raw)

    logger.trace(f"Normalized: raw={raw!r} → root={root}, rel={rel}")
    return root, rel


# --------------------------------------------------------------------------- #
# main per-build resolver
# --------------------------------------------------------------------------- #


def _resolve_includes(  # noqa: PLR0912
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> list[IncludeResolved]:
    logger = get_app_logger()
    logger.trace(
        f"[resolve_includes] Starting with"
        f" {len(resolved_cfg.get('include', []))} config includes"
    )

    includes: list[IncludeResolved] = []

    if getattr(args, "include", None):
        # Full override → relative to cwd
        for raw in args.include:
            inc, _ = _parse_include_with_dest(raw, cwd)
            includes.append(inc)

    elif "include" in resolved_cfg:
        # From config → relative to config_dir
        # Type narrowing: resolved_cfg is dict[str, Any], narrow the include list
        include_list: list[str | dict[str, str]] = cast(
            "list[str | dict[str, str]]", resolved_cfg["include"]
        )
        for raw in include_list:
            # Handle both string and object formats
            if isinstance(raw, dict):
                # Object format: {"path": "...", "dest": "..."}
                path_str = raw.get("path", "")
                dest_str = raw.get("dest")
                root, rel = _normalize_path_with_root(path_str, config_dir)
                inc = make_includeresolved(rel, root, "config")
                if dest_str:
                    # dest is relative to output dir, no normalization
                    inc["dest"] = Path(dest_str)
                includes.append(inc)
            else:
                # String format: "path/to/files"
                root, rel = _normalize_path_with_root(raw, config_dir)
                includes.append(make_includeresolved(rel, root, "config"))

    # Add-on includes (extend, not override)
    if getattr(args, "add_include", None):
        for raw in args.add_include:
            inc, _ = _parse_include_with_dest(raw, cwd)
            includes.append(inc)

    # unique path+root
    seen_inc: set[tuple[Path | str, Path]] = set()
    unique_inc: list[IncludeResolved] = []
    for i in includes:
        key = (i["path"], i["root"])
        if key not in seen_inc:
            seen_inc.add(key)
            unique_inc.append(i)

            # Check root existence
            if not i["root"].exists():
                logger.warning(
                    "Include root does not exist: %s (origin: %s)",
                    i["root"],
                    i["origin"],
                )

            # Check path existence
            if not has_glob_chars(str(i["path"])):
                full_path = i["root"] / i["path"]  # absolute paths override root
                if not full_path.exists():
                    logger.warning(
                        "Include path does not exist: %s (origin: %s)",
                        full_path,
                        i["origin"],
                    )

    return unique_inc


def _resolve_excludes(
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None,
) -> list[PathResolved]:
    logger = get_app_logger()
    logger.trace(
        f"[resolve_excludes] Starting with"
        f" {len(resolved_cfg.get('exclude', []))} config excludes"
    )

    excludes: list[PathResolved] = []

    def _add_excludes(paths: list[str], context: Path, origin: OriginType) -> None:
        # Exclude patterns (from CLI, config, or gitignore) should stay literal
        excludes.extend(make_pathresolved(raw, context, origin) for raw in paths)

    if getattr(args, "exclude", None):
        # Full override → relative to cwd
        # Keep CLI-provided exclude patterns as-is (do not resolve),
        # since glob patterns like "*.tmp" should match relative paths
        # beneath the include root, not absolute paths.
        _add_excludes(args.exclude, cwd, "cli")
    elif "exclude" in resolved_cfg:
        # From config → relative to config_dir
        _add_excludes(resolved_cfg["exclude"], config_dir, "config")

    # Add-on excludes (extend, not override)
    if getattr(args, "add_exclude", None):
        _add_excludes(args.add_exclude, cwd, "cli")

    # --- Merge .gitignore patterns into excludes if enabled ---
    # Determine whether to respect .gitignore
    if getattr(args, "respect_gitignore", None) is not None:
        respect_gitignore = args.respect_gitignore
    elif "respect_gitignore" in resolved_cfg:
        respect_gitignore = resolved_cfg["respect_gitignore"]
    else:
        # fallback — true by default, overridden by root config if needed
        respect_gitignore = (root_cfg or {}).get(
            "respect_gitignore",
            DEFAULT_RESPECT_GITIGNORE,
        )

    if respect_gitignore:
        gitignore_path = config_dir / ".gitignore"
        patterns = _load_gitignore_patterns(gitignore_path)
        if patterns:
            logger.trace(
                f"Adding {len(patterns)} .gitignore patterns from {gitignore_path}",
            )
        _add_excludes(patterns, config_dir, "gitignore")

    resolved_cfg["respect_gitignore"] = respect_gitignore

    # unique path+root
    seen_exc: set[tuple[Path | str, Path]] = set()
    unique_exc: list[PathResolved] = []
    for ex in excludes:
        key = (ex["path"], ex["root"])
        if key not in seen_exc:
            seen_exc.add(key)
            unique_exc.append(ex)

    return unique_exc


def _resolve_output(
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> PathResolved:
    logger = get_app_logger()
    logger.trace("[resolve_output] Resolving output directory")

    if getattr(args, "out", None):
        # Full override → relative to cwd
        root, rel = _normalize_path_with_root(args.out, cwd)
        out_wrapped = make_pathresolved(rel, root, "cli")
    elif "out" in resolved_cfg:
        # From config → relative to config_dir
        root, rel = _normalize_path_with_root(resolved_cfg["out"], config_dir)
        out_wrapped = make_pathresolved(rel, root, "config")
    else:
        root, rel = _normalize_path_with_root(DEFAULT_OUT_DIR, cwd)
        out_wrapped = make_pathresolved(rel, root, "default")

    return out_wrapped


def resolve_build_config(
    build_cfg: BuildConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    root_cfg: RootConfig | None = None,
) -> BuildConfigResolved:
    """Resolve a single BuildConfig into a BuildConfigResolved.

    Applies CLI overrides, normalizes paths, merges gitignore behavior,
    and attaches provenance metadata.
    """
    logger = get_app_logger()
    logger.trace("[resolve_build_config] Starting resolution for build config")

    # Make a mutable copy
    resolved_cfg: dict[str, Any] = dict(build_cfg)

    # root provenance for all resolutions
    meta: MetaBuildConfigResolved = {
        "cli_root": cwd,
        "config_root": config_dir,
    }

    # --- Includes ---------------------------
    resolved_cfg["include"] = _resolve_includes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
    )
    logger.trace(
        f"[resolve_build_config] Resolved {len(resolved_cfg['include'])} include(s)"
    )

    # --- Excludes ---------------------------
    resolved_cfg["exclude"] = _resolve_excludes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
        root_cfg=root_cfg,
    )
    logger.trace(
        f"[resolve_build_config] Resolved {len(resolved_cfg['exclude'])} exclude(s)"
    )

    # --- Output ---------------------------
    resolved_cfg["out"] = _resolve_output(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
    )

    # ------------------------------
    # Log level
    # ------------------------------
    build_log = resolved_cfg.get("log_level")
    root_log = (root_cfg or {}).get("log_level")
    resolved_cfg["log_level"] = logger.determine_log_level(
        args=args, root_log_level=root_log, build_log_level=build_log
    )

    # ------------------------------
    # Strict config
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_strict = resolved_cfg.get("strict_config")
    root_strict = (root_cfg or {}).get("strict_config")
    if isinstance(build_strict, bool):
        resolved_cfg["strict_config"] = build_strict
    elif isinstance(root_strict, bool):
        resolved_cfg["strict_config"] = root_strict
    else:
        resolved_cfg["strict_config"] = DEFAULT_STRICT_CONFIG

    # ------------------------------
    # Post-processing
    # ------------------------------
    # Cascade: build-level → root-level → default
    resolved_cfg["post_processing"] = resolve_post_processing(build_cfg, root_cfg)

    # ------------------------------
    # Pyproject.toml metadata
    # ------------------------------
    num_builds = len((root_cfg or {}).get("builds", []))
    _apply_pyproject_metadata(
        resolved_cfg,
        build_cfg=build_cfg,
        root_cfg=root_cfg,
        config_dir=config_dir,
        num_builds=num_builds,
    )

    # ------------------------------
    # Attach provenance
    # ------------------------------
    resolved_cfg["__meta__"] = meta
    return cast_hint(BuildConfigResolved, resolved_cfg)


# --------------------------------------------------------------------------- #
# root-level resolver
# --------------------------------------------------------------------------- #


def resolve_config(
    root_input: RootConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> RootConfigResolved:
    """Fully resolve a loaded RootConfig into a ready-to-run RootConfigResolved.

    If invoked standalone, ensures the global logger reflects the resolved log level.
    If called after load_and_validate_config(), this is a harmless no-op re-sync."""
    logger = get_app_logger()
    root_cfg = cast_hint(RootConfig, dict(root_input))

    builds_input = root_cfg.get("builds", [])
    logger.trace(
        f"[resolve_config] Resolving root config with {len(builds_input)} build(s)"
    )

    # ------------------------------
    # Watch interval
    # ------------------------------
    env_watch = os.getenv(DEFAULT_ENV_WATCH_INTERVAL)
    if getattr(args, "watch", None) is not None:
        watch_interval = args.watch
    elif env_watch is not None:
        try:
            watch_interval = float(env_watch)
        except ValueError:
            logger.warning(
                "Invalid %s=%r, using default.", DEFAULT_ENV_WATCH_INTERVAL, env_watch
            )
            watch_interval = DEFAULT_WATCH_INTERVAL
    else:
        watch_interval = root_cfg.get("watch_interval", DEFAULT_WATCH_INTERVAL)

    logger.trace(f"[resolve_config] Watch interval resolved to {watch_interval}s")

    # ------------------------------
    # Log level
    # ------------------------------
    #  log_level: arg -> env -> build -> root -> default
    root_log = root_cfg.get("log_level")
    log_level = logger.determine_log_level(args=args, root_log_level=root_log)

    # --- sync runtime ---
    logger.setLevel(log_level)

    # ------------------------------
    # Resolve builds
    # ------------------------------
    resolved_builds = [
        resolve_build_config(b, args, config_dir, cwd, root_cfg) for b in builds_input
    ]

    # ------------------------------
    # Post-processing
    # ------------------------------
    # For root-level, create a dummy build config to use the same resolution function
    dummy_build: BuildConfig = {}
    post_processing = resolve_post_processing(dummy_build, root_cfg)

    resolved_root: RootConfigResolved = {
        "builds": resolved_builds,
        "strict_config": root_cfg.get("strict_config", False),
        "watch_interval": watch_interval,
        "log_level": log_level,
        "post_processing": post_processing,
    }

    return resolved_root
