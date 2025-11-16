# src/serger/config/config_resolve.py


import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from apathetic_utils import cast_hint, has_glob_chars, literal_to_set, load_toml
from serger.constants import (
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ORDER,
    DEFAULT_COMMENTS_MODE,
    DEFAULT_DOCSTRING_MODE,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_EXTERNAL_IMPORTS,
    DEFAULT_INTERNAL_IMPORTS,
    DEFAULT_MODULE_BASES,
    DEFAULT_MODULE_MODE,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_SHIM,
    DEFAULT_STITCH_MODE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_USE_PYPROJECT,
    DEFAULT_WATCH_INTERVAL,
)
from serger.logs import get_app_logger
from serger.module_actions import extract_module_name_from_source_path
from serger.utils import make_includeresolved, make_pathresolved
from serger.utils.utils_validation import validate_required_keys

from .config_types import (
    BuildConfig,
    BuildConfigResolved,
    IncludeResolved,
    MetaBuildConfigResolved,
    ModuleActionAffects,
    ModuleActionCleanup,
    ModuleActionFull,
    ModuleActionMode,
    ModuleActions,
    ModuleActionScope,
    ModuleActionType,
    OriginType,
    PathResolved,
    PostCategoryConfigResolved,
    PostProcessingConfig,
    PostProcessingConfigResolved,
    RootConfig,
    RootConfigResolved,
    ShimSetting,
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
    authors: str = ""

    def has_any(self) -> bool:
        """Check if any metadata was found."""
        return bool(
            self.name
            or self.version
            or self.description
            or self.license_text
            or self.authors
        )


def _extract_authors_from_project(project: dict[str, Any]) -> str:
    """Extract authors from project dict and format as string.

    Args:
        project: Project section from pyproject.toml

    Returns:
        Formatted authors string (empty if no authors found)
    """
    authors_text = ""
    authors_val = project.get("authors", [])
    if isinstance(authors_val, list) and authors_val:
        author_parts: list[str] = []
        for author in authors_val:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(author, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                author_name = author.get("name", "")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                author_email = author.get("email", "")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
                if isinstance(author_name, str) and author_name:
                    if isinstance(author_email, str) and author_email:
                        author_parts.append(f"{author_name} <{author_email}>")
                    else:
                        author_parts.append(author_name)
        if author_parts:
            authors_text = ", ".join(author_parts)
    return authors_text


def extract_pyproject_metadata(
    pyproject_path: Path, *, required: bool = False
) -> PyprojectMetadata | None:
    """Extract metadata from pyproject.toml file.

    Extracts name, version, description, license, and authors from the
    [project] section. Uses load_toml() utility which supports Python 3.10
    and 3.11+.

    Args:
        pyproject_path: Path to pyproject.toml file
        required: If True, raise RuntimeError when tomli is missing on
                  Python 3.10. If False, return None when unavailable.

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

    # Extract authors
    authors_text = _extract_authors_from_project(project)

    return PyprojectMetadata(
        name=name if isinstance(name, str) else "",
        version=version if isinstance(version, str) else "",
        description=description if isinstance(description, str) else "",
        license_text=license_text,
        authors=authors_text,
    )


def _is_configless_build(root_cfg: RootConfig | None, num_builds: int) -> bool:
    """Check if this is a configless build (no config file).

    Configless builds are detected by checking if root_cfg is minimal:
    only has 'builds' with one empty build and no other meaningful fields.

    Args:
        root_cfg: Root config (may be None)
        num_builds: Number of builds in root config

    Returns:
        True if this is a configless build, False otherwise
    """
    if root_cfg is None:
        return True
    if num_builds != 1:
        return False
    # Check if root_cfg is minimal (only has 'builds' with one empty build)
    # This indicates a configless build created in cli.py
    root_keys = set(root_cfg.keys())
    if root_keys == {"builds"}:
        builds = root_cfg.get("builds", [])
        if len(builds) == 1 and not builds[0]:
            return True
    return False


def _should_use_pyproject(
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
) -> bool:
    """Determine if pyproject.toml should be used for this build.

    Pyproject.toml is used by default (DEFAULT_USE_PYPROJECT) unless explicitly
    disabled. Explicit enablement (use_pyproject=True or pyproject_path set)
    always takes precedence and enables it even if it would otherwise be disabled.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        True if pyproject.toml should be used, False otherwise
    """
    root_use_pyproject = (root_cfg or {}).get("use_pyproject")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")
    build_use_pyproject = build_cfg.get("use_pyproject")
    build_pyproject_path = build_cfg.get("pyproject_path")

    # Check if this is a configless build
    num_builds = len((root_cfg or {}).get("builds", []))
    is_configless = _is_configless_build(root_cfg, num_builds)

    # Build-level explicit disablement always takes precedence
    if build_use_pyproject is False:
        return False

    # Root-level explicit disablement takes precedence unless build overrides
    # (build-level pyproject_path is considered an override)
    if root_use_pyproject is False and build_pyproject_path is None:
        return False

    # For configless builds, use DEFAULT_USE_PYPROJECT (unless disabled above)
    if is_configless:
        return DEFAULT_USE_PYPROJECT

    # For non-configless builds, also use DEFAULT_USE_PYPROJECT unless explicitly
    # disabled (but allow explicit enablement to override)
    if (
        root_use_pyproject is True
        or root_pyproject_path is not None
        or build_use_pyproject is True
        or build_pyproject_path is not None
    ):
        return True

    # Default to DEFAULT_USE_PYPROJECT for non-configless builds too
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


def _validate_and_normalize_module_actions(  # noqa: C901, PLR0912, PLR0915
    module_actions: ModuleActions,
    config_dir: Path | None = None,
) -> list[ModuleActionFull]:
    """Validate and normalize module_actions to list format.

    Applies all default values and validates all fields. Returns fully resolved
    actions with all fields present (defaults applied).

    Args:
        module_actions: Either dict format (simple) or list format (full)
        config_dir: Optional config directory for resolving relative source_path
            paths. If None, paths are resolved relative to current working directory.

    Returns:
        Normalized list of ModuleActionFull with all fields present

    Raises:
        ValueError: If validation fails
        TypeError: If types are invalid
    """
    valid_action_types = literal_to_set(ModuleActionType)
    valid_action_modes = literal_to_set(ModuleActionMode)
    valid_action_scopes = literal_to_set(ModuleActionScope)
    valid_action_affects = literal_to_set(ModuleActionAffects)
    valid_action_cleanups = literal_to_set(ModuleActionCleanup)

    if isinstance(module_actions, dict):
        # Simple format: dict[str, str | None]
        # Convert to list format with defaults applied
        # {"old": "new"} -> move action
        # {"old": None} -> delete action
        result: list[ModuleActionFull] = []
        for key, value in sorted(module_actions.items()):
            if not isinstance(key, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                msg = (
                    f"module_actions dict keys must be strings, "
                    f"got {type(key).__name__}"
                )
                raise TypeError(msg)
            if value is not None and not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                msg = (
                    f"module_actions dict values must be strings or None, "
                    f"got {type(value).__name__}"
                )
                raise ValueError(msg)

            # Validate source is non-empty
            if not key:
                msg = "module_actions dict keys (source) must be non-empty strings"
                raise ValueError(msg)

            # Build normalized action with defaults
            # Dict format: {"old": "new"} -> move, {"old": None} -> delete
            if value is not None:
                # Move action: {"old": "new"}
                normalized: ModuleActionFull = {
                    "source": key,
                    "dest": value,
                    "action": "move",
                    "mode": "preserve",
                    "scope": "shim",  # Explicitly set for dict format (per Q4)
                    "affects": "shims",
                    "cleanup": "auto",
                }
            else:
                # Delete action: {"old": None}
                normalized = {
                    "source": key,
                    "action": "delete",
                    "mode": "preserve",
                    "scope": "shim",  # Explicitly set for dict format (per Q4)
                    "affects": "shims",
                    "cleanup": "auto",
                }
            result.append(normalized)
        return result

    if isinstance(module_actions, list):  # pyright: ignore[reportUnnecessaryIsInstance]
        # Full format: list[ModuleActionFull]
        # Validate each item, then apply defaults
        result_list: list[ModuleActionFull] = []
        for idx, action in enumerate(module_actions):
            if not isinstance(action, dict):  # pyright: ignore[reportUnnecessaryIsInstance]
                msg = (
                    f"module_actions list items must be dicts, "
                    f"got {type(action).__name__} at index {idx}"
                )
                raise TypeError(msg)

            # Validate required 'source' key
            if "source" not in action:
                msg = f"module_actions[{idx}] missing required 'source' key"
                raise ValueError(msg)
            source_val = action["source"]
            if not isinstance(source_val, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                msg = (
                    f"module_actions[{idx}]['source'] must be a string, "
                    f"got {type(source_val).__name__}"
                )
                raise TypeError(msg)
            # Validate source is non-empty
            if not source_val:
                msg = f"module_actions[{idx}]['source'] must be a non-empty string"
                raise ValueError(msg)

            # Validate and normalize action type
            action_val = action.get("action", "move")
            # Normalize "none" to "delete" (alias)
            if action_val == "none":
                action_val = "delete"
            if action_val not in valid_action_types:
                valid_str = ", ".join(repr(v) for v in sorted(valid_action_types))
                msg = (
                    f"module_actions[{idx}]['action'] invalid: {action_val!r}. "
                    f"Must be one of: {valid_str}"
                )
                raise ValueError(msg)

            # Validate mode if present
            if "mode" in action:
                mode_val = action["mode"]
                if mode_val not in valid_action_modes:
                    valid_str = ", ".join(repr(v) for v in sorted(valid_action_modes))
                    msg = (
                        f"module_actions[{idx}]['mode'] invalid: {mode_val!r}. "
                        f"Must be one of: {valid_str}"
                    )
                    raise ValueError(msg)

            # Validate scope if present
            if "scope" in action:
                scope_val = action["scope"]
                if scope_val not in valid_action_scopes:
                    valid_str = ", ".join(repr(v) for v in sorted(valid_action_scopes))
                    msg = (
                        f"module_actions[{idx}]['scope'] invalid: {scope_val!r}. "
                        f"Must be one of: {valid_str}"
                    )
                    raise ValueError(msg)

            # Validate affects if present
            if "affects" in action:
                affects_val = action["affects"]
                if affects_val not in valid_action_affects:
                    valid_str = ", ".join(repr(v) for v in sorted(valid_action_affects))
                    msg = (
                        f"module_actions[{idx}]['affects'] invalid: {affects_val!r}. "
                        f"Must be one of: {valid_str}"
                    )
                    raise ValueError(msg)

            # Validate cleanup if present
            if "cleanup" in action:
                cleanup_val = action["cleanup"]
                if cleanup_val not in valid_action_cleanups:
                    valid_str = ", ".join(
                        repr(v) for v in sorted(valid_action_cleanups)
                    )
                    msg = (
                        f"module_actions[{idx}]['cleanup'] invalid: {cleanup_val!r}. "
                        f"Must be one of: {valid_str}"
                    )
                    raise ValueError(msg)

            # Validate source_path if present
            source_path_resolved_str: str | None = None
            if "source_path" in action:
                source_path_val = action["source_path"]
                if not isinstance(source_path_val, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                    msg = (
                        f"module_actions[{idx}]['source_path'] must be a string, "
                        f"got {type(source_path_val).__name__}"
                    )
                    raise TypeError(msg)
                if not source_path_val:
                    msg = (
                        f"module_actions[{idx}]['source_path'] must be a "
                        f"non-empty string if present"
                    )
                    raise ValueError(msg)

                # Resolve to absolute path (relative to config_dir if provided)
                if config_dir is not None:
                    if Path(source_path_val).is_absolute():
                        source_path_resolved = Path(source_path_val).resolve()
                    else:
                        source_path_resolved = (config_dir / source_path_val).resolve()
                else:
                    source_path_resolved = Path(source_path_val).resolve()

                # Get affects value to determine if we need to validate file existence
                affects_val = action.get("affects", "shims")
                # Always validate module name matching (even for shims-only actions)
                # but only validate file existence if affects includes "stitching"
                if "stitching" in affects_val or affects_val == "both":
                    # Validate file exists (if affects includes "stitching")
                    if not source_path_resolved.exists():
                        msg = (
                            f"module_actions[{idx}]['source_path'] file "
                            f"does not exist: {source_path_resolved}"
                        )
                        raise ValueError(msg)

                    # Validate is Python file
                    if source_path_resolved.suffix != ".py":
                        msg = (
                            f"module_actions[{idx}]['source_path'] must be a "
                            f"Python file (.py extension), got: {source_path_resolved}"
                        )
                        raise ValueError(msg)

                # Extract module name from file and verify it matches source
                # Use file's parent directory as package root for validation
                # (since source_path files may not be in normal include set)
                # This validation happens for all affects values to ensure
                # source matches
                if (
                    source_path_resolved.exists()
                    and source_path_resolved.suffix == ".py"
                ):
                    package_root_for_validation = source_path_resolved.parent
                    try:
                        extract_module_name_from_source_path(
                            source_path_resolved,
                            package_root_for_validation,
                            source_val,
                        )
                    except ValueError as e:
                        msg = (
                            f"module_actions[{idx}]['source_path'] "
                            f"validation failed: {e!s}"
                        )
                        raise ValueError(msg) from e

                # Store resolved absolute path for later use
                source_path_resolved_str = str(source_path_resolved)

            # Validate dest based on action type (per Q5)
            dest_val = action.get("dest")
            if action_val in ("move", "copy"):
                # dest is required for move/copy
                if dest_val is None:
                    msg = (
                        f"module_actions[{idx}]: 'dest' is required for "
                        f"'{action_val}' action"
                    )
                    raise ValueError(msg)
                if not isinstance(dest_val, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                    msg = (
                        f"module_actions[{idx}]['dest'] must be a string, "
                        f"got {type(dest_val).__name__}"
                    )
                    raise TypeError(msg)
            elif action_val == "delete":
                # dest must NOT be present for delete
                if dest_val is not None:
                    msg = (
                        f"module_actions[{idx}]: 'dest' must not be present "
                        f"for 'delete' action"
                    )
                    raise ValueError(msg)

            # Build normalized action with all defaults applied (per Q1/Q2)
            normalized_action: ModuleActionFull = {
                "source": source_val,
                "action": action_val,  # Already normalized ("none" -> "delete")
                "mode": action.get("mode", "preserve"),
                # Default for user actions (per Q3)
                "scope": action.get("scope", "shim"),
                "affects": action.get("affects", "shims"),
                "cleanup": action.get("cleanup", "auto"),
            }
            # Add dest only if present (required for move/copy, not for delete)
            if dest_val is not None:
                normalized_action["dest"] = dest_val
            # Add source_path only if present (store resolved absolute path)
            if "source_path" in action:
                if source_path_resolved_str is not None:
                    normalized_action["source_path"] = source_path_resolved_str
                else:
                    # This shouldn't happen, but handle it just in case
                    source_path_val = action["source_path"]
                    if config_dir is not None:
                        if Path(source_path_val).is_absolute():
                            source_path_resolved = Path(source_path_val).resolve()
                        else:
                            source_path_resolved = (
                                config_dir / source_path_val
                            ).resolve()
                    else:
                        source_path_resolved = Path(source_path_val).resolve()
                    normalized_action["source_path"] = str(source_path_resolved)

            result_list.append(normalized_action)

        return result_list

    msg = f"module_actions must be dict or list, got {type(module_actions).__name__}"
    raise ValueError(msg)


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
    *,
    explicitly_requested: bool,
) -> None:
    """Apply extracted metadata fields to resolved config.

    When explicitly requested (use_pyproject=True), pyproject.toml values
    overwrite config values. When used by default, only fills in missing
    fields (config values take precedence).

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        metadata: Extracted metadata
        pyproject_path: Path to pyproject.toml (for logging)
        explicitly_requested: True if pyproject was explicitly enabled
    """
    logger = get_app_logger()

    # Apply fields from pyproject.toml
    if metadata.version:
        # Note: version is not a build config field, but we'll store it
        # for use in build.py later
        resolved_cfg["_pyproject_version"] = metadata.version

    if metadata.name:
        if explicitly_requested or "display_name" not in resolved_cfg:
            resolved_cfg["display_name"] = metadata.name
        # Package from pyproject.toml name
        if explicitly_requested or "package" not in resolved_cfg:
            resolved_cfg["package"] = metadata.name

    if metadata.description and (
        explicitly_requested or "description" not in resolved_cfg
    ):
        resolved_cfg["description"] = metadata.description

    if metadata.authors and (explicitly_requested or "authors" not in resolved_cfg):
        resolved_cfg["authors"] = metadata.authors

    if metadata.license_text and (
        explicitly_requested or "license_header" not in resolved_cfg
    ):
        resolved_cfg["license_header"] = metadata.license_text

    if metadata.has_any():
        logger.trace(f"[resolve_build_config] Extracted metadata from {pyproject_path}")


def _apply_pyproject_metadata(
    resolved_cfg: dict[str, Any],
    *,
    build_cfg: BuildConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
) -> None:
    """Extract and apply pyproject.toml metadata to resolved config.

    Handles all the logic for determining when to use pyproject.toml,
    path resolution, and filling in missing fields.

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        build_cfg: Original build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution
    """
    if not _should_use_pyproject(build_cfg, root_cfg):
        return

    pyproject_path = _resolve_pyproject_path(build_cfg, root_cfg, config_dir)
    explicitly_requested = _is_explicitly_requested(build_cfg, root_cfg)

    metadata = _extract_pyproject_metadata_safe(
        pyproject_path, explicitly_requested=explicitly_requested
    )
    _apply_metadata_fields(
        resolved_cfg,
        metadata,
        pyproject_path,
        explicitly_requested=explicitly_requested,
    )


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


def resolve_post_processing(  # noqa: PLR0912
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
        validate_required_keys(tool_dict, {"args"}, f"tool_config for {tool_label}")

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


def _get_first_level_modules_from_base(
    base_str: str,
    config_dir: Path,
) -> list[str]:
    """Get first-level module/package names from a single module_base directory.

    Scans only the immediate children of the module_base directory (not
    recursive). Returns a sorted list of package/module names.

    Package detection logic:
    - Directories with __init__.py are definitely packages (standard Python)
    - Directories in module_bases are also considered packages (namespace
      packages, mimics modern Python behavior)
    - .py files at first level are modules

    Args:
        base_str: Module base directory path (relative or absolute)
        config_dir: Config directory for resolving relative paths

    Returns:
        Sorted list of first-level module/package names found in the base
    """
    logger = get_app_logger()
    modules: list[str] = []

    # Resolve base path relative to config_dir
    base_path = (config_dir / base_str).resolve()

    if not base_path.exists() or not base_path.is_dir():
        logger.trace(
            "[get_first_level_modules] Skipping non-existent base: %s", base_path
        )
        return modules

    # Get immediate children (first level only, not recursive)
    try:
        for item in sorted(base_path.iterdir()):
            if item.is_dir():
                # Check if directory has __init__.py (definitive package marker)
                has_init = (item / "__init__.py").exists()
                if has_init:
                    # Standard Python package (has __init__.py)
                    modules.append(item.name)
                    logger.trace(
                        "[get_first_level_modules] Found package (with __init__.py): "
                        "%s in %s",
                        item.name,
                        base_path,
                    )
                else:
                    # Directory in module_bases is considered a package
                    # (namespace package, mimics modern Python)
                    modules.append(item.name)
                    logger.trace(
                        "[get_first_level_modules] Found package (namespace): %s in %s",
                        item.name,
                        base_path,
                    )
            elif item.is_file() and item.suffix == ".py":
                # Python file at first level is a module
                module_name = item.stem
                if module_name not in modules:
                    modules.append(module_name)
                    logger.trace(
                        "[get_first_level_modules] Found module file: %s in %s",
                        module_name,
                        base_path,
                    )
    except PermissionError:
        logger.trace("[get_first_level_modules] Permission denied for: %s", base_path)

    return sorted(modules)


def _get_first_level_modules_from_bases(
    module_bases: list[str],
    config_dir: Path,
) -> list[str]:
    """Get first-level module/package names from module_bases directories.

    Scans only the immediate children of each module_base directory (not
    recursive). Returns a list preserving the order of module_bases, with
    modules from each base sorted but not deduplicated across bases.

    Args:
        module_bases: List of module base directory paths (relative or absolute)
        config_dir: Config directory for resolving relative paths

    Returns:
        List of first-level module/package names found in module_bases,
        preserving module_bases order
    """
    modules: list[str] = []

    for base_str in module_bases:
        base_modules = _get_first_level_modules_from_base(base_str, config_dir)
        modules.extend(base_modules)

    return modules


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


def resolve_build_config(  # noqa: C901, PLR0912, PLR0915
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
    # Stitch mode (resolved first, used for import defaults)
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_stitch_mode = resolved_cfg.get("stitch_mode")
    root_stitch_mode = (root_cfg or {}).get("stitch_mode")
    if build_stitch_mode is not None:
        resolved_cfg["stitch_mode"] = build_stitch_mode
    elif root_stitch_mode is not None:
        resolved_cfg["stitch_mode"] = root_stitch_mode
    else:
        resolved_cfg["stitch_mode"] = DEFAULT_STITCH_MODE

    # Get the resolved stitch_mode for use in import defaults
    stitch_mode = resolved_cfg["stitch_mode"]
    if not isinstance(stitch_mode, str):
        msg = "stitch_mode must be a string"
        raise TypeError(msg)

    # ------------------------------
    # Module mode
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_module_mode = resolved_cfg.get("module_mode")
    root_module_mode = (root_cfg or {}).get("module_mode")
    if build_module_mode is not None:
        resolved_cfg["module_mode"] = build_module_mode
    elif root_module_mode is not None:
        resolved_cfg["module_mode"] = root_module_mode
    else:
        resolved_cfg["module_mode"] = DEFAULT_MODULE_MODE

    # ------------------------------
    # Shim setting
    # ------------------------------
    # Cascade: build-level → root-level → default
    valid_shim_values = literal_to_set(ShimSetting)
    build_shim = resolved_cfg.get("shim")
    root_shim = (root_cfg or {}).get("shim")
    if build_shim is not None:
        # Validate value
        if build_shim not in valid_shim_values:
            valid_str = ", ".join(repr(v) for v in sorted(valid_shim_values))
            msg = f"Invalid shim value: {build_shim!r}. Must be one of: {valid_str}"
            raise ValueError(msg)
        resolved_cfg["shim"] = build_shim
    elif root_shim is not None:
        # Validate value
        if root_shim not in valid_shim_values:
            valid_str = ", ".join(repr(v) for v in sorted(valid_shim_values))
            msg = f"Invalid shim value: {root_shim!r}. Must be one of: {valid_str}"
            raise ValueError(msg)
        resolved_cfg["shim"] = root_shim
    else:
        resolved_cfg["shim"] = DEFAULT_SHIM

    # ------------------------------
    # Module actions
    # ------------------------------
    # Cascade: build-level → root-level → default (empty list if not provided)
    build_module_actions = resolved_cfg.get("module_actions")
    root_module_actions = (root_cfg or {}).get("module_actions")
    if build_module_actions is not None:
        # Validate and normalize to list format
        resolved_cfg["module_actions"] = _validate_and_normalize_module_actions(
            build_module_actions, config_dir=config_dir
        )
    elif root_module_actions is not None:
        # Validate and normalize to list format
        resolved_cfg["module_actions"] = _validate_and_normalize_module_actions(
            root_module_actions, config_dir=config_dir
        )
    else:
        # Always set to empty list in resolved config (fully resolved)
        resolved_cfg["module_actions"] = []

    # ------------------------------
    # Import handling
    # ------------------------------
    # Cascade: build-level → root-level → default (mode-dependent)
    build_internal = resolved_cfg.get("internal_imports")
    root_internal = (root_cfg or {}).get("internal_imports")
    if build_internal is not None:
        resolved_cfg["internal_imports"] = build_internal
    elif root_internal is not None:
        resolved_cfg["internal_imports"] = root_internal
    else:
        resolved_cfg["internal_imports"] = DEFAULT_INTERNAL_IMPORTS[stitch_mode]

    build_external = resolved_cfg.get("external_imports")
    root_external = (root_cfg or {}).get("external_imports")
    if build_external is not None:
        resolved_cfg["external_imports"] = build_external
    elif root_external is not None:
        resolved_cfg["external_imports"] = root_external
    else:
        resolved_cfg["external_imports"] = DEFAULT_EXTERNAL_IMPORTS[stitch_mode]

    # ------------------------------
    # Comments mode
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_comments_mode = resolved_cfg.get("comments_mode")
    root_comments_mode = (root_cfg or {}).get("comments_mode")
    if build_comments_mode is not None:
        resolved_cfg["comments_mode"] = build_comments_mode
    elif root_comments_mode is not None:
        resolved_cfg["comments_mode"] = root_comments_mode
    else:
        resolved_cfg["comments_mode"] = DEFAULT_COMMENTS_MODE

    # ------------------------------
    # Docstring mode
    # ------------------------------
    # Cascade: build-level → root-level → default
    build_docstring_mode = resolved_cfg.get("docstring_mode")
    root_docstring_mode = (root_cfg or {}).get("docstring_mode")
    if build_docstring_mode is not None:
        resolved_cfg["docstring_mode"] = build_docstring_mode
    elif root_docstring_mode is not None:
        resolved_cfg["docstring_mode"] = root_docstring_mode
    else:
        resolved_cfg["docstring_mode"] = DEFAULT_DOCSTRING_MODE

    # ------------------------------
    # Module bases
    # ------------------------------
    # Cascade: build-level → root-level → default
    # Convert str to list[str] if needed
    build_module_bases = resolved_cfg.get("module_bases")
    root_module_bases = (root_cfg or {}).get("module_bases")
    if build_module_bases is not None:
        resolved_cfg["module_bases"] = (
            [build_module_bases]
            if isinstance(build_module_bases, str)
            else build_module_bases
        )
    elif root_module_bases is not None:
        resolved_cfg["module_bases"] = (
            [root_module_bases]
            if isinstance(root_module_bases, str)
            else root_module_bases
        )
    else:
        resolved_cfg["module_bases"] = DEFAULT_MODULE_BASES

    # ------------------------------
    # Post-processing
    # ------------------------------
    # Cascade: build-level → root-level → default
    resolved_cfg["post_processing"] = resolve_post_processing(build_cfg, root_cfg)

    # ------------------------------
    # Authors
    # ------------------------------
    # Cascade: build-level → root-level (no default, optional field)
    build_authors = resolved_cfg.get("authors")
    root_authors = (root_cfg or {}).get("authors")
    if build_authors is not None:
        resolved_cfg["authors"] = build_authors
    elif root_authors is not None:
        resolved_cfg["authors"] = root_authors
    # If neither is set, leave it unset (will be filled by pyproject.toml if available)

    # ------------------------------
    # Version
    # ------------------------------
    # Cascade: build-level → root-level (no default, optional field)
    # Falls back to _pyproject_version in _extract_build_metadata()
    # if use_pyproject was enabled
    build_version = resolved_cfg.get("version")
    root_version = (root_cfg or {}).get("version")
    if build_version is not None:
        resolved_cfg["version"] = build_version
    elif root_version is not None:
        resolved_cfg["version"] = root_version
    # If neither is set, leave it unset (will fall back to pyproject.toml if available)

    # ------------------------------
    # Pyproject.toml metadata
    # ------------------------------
    _apply_pyproject_metadata(
        resolved_cfg,
        build_cfg=build_cfg,
        root_cfg=root_cfg,
        config_dir=config_dir,
    )

    # ------------------------------
    # Auto-set includes from package and module_bases
    # ------------------------------
    # If no includes were provided (configless or config has no includes),
    # and we have a package that can be found in module_bases,
    # automatically set includes to that package.
    # This must run AFTER pyproject metadata is applied so package from
    # pyproject.toml is available.
    has_cli_includes = bool(
        getattr(args, "include", None) or getattr(args, "add_include", None)
    )
    # Check if config has includes (empty list means no includes)
    config_includes = resolved_cfg.get("include", [])
    has_config_includes = len(config_includes) > 0
    # Check if includes were explicitly set in original config
    # (even if empty, explicit setting means don't auto-set)
    # Note: RootConfig doesn't have include field, only BuildConfig does
    has_explicit_config_includes = "include" in build_cfg
    package = resolved_cfg.get("package")
    module_bases_list = resolved_cfg.get("module_bases", [])

    if (
        not has_cli_includes
        and not has_config_includes
        and not has_explicit_config_includes
        and package
        and module_bases_list
    ):
        # Get first-level modules from module_bases
        first_level_modules = _get_first_level_modules_from_bases(
            module_bases_list, config_dir
        )

        # Check if package is found in first-level modules
        if package in first_level_modules:
            logger.debug(
                "Auto-setting includes to package '%s' found in module_bases: %s",
                package,
                module_bases_list,
            )

            # Find which module_base contains the package
            # Can be either a directory (package) or a .py file (module)
            package_path: str | None = None
            for base_str in module_bases_list:
                base_path = (config_dir / base_str).resolve()
                package_dir = base_path / package
                package_file = base_path / f"{package}.py"

                if package_dir.exists() and package_dir.is_dir():
                    # Found the package directory
                    # Create include path relative to config_dir
                    rel_path = package_dir.relative_to(config_dir)
                    package_path = str(rel_path)
                    break
                if package_file.exists() and package_file.is_file():
                    # Found the package as a single-file module
                    # Create include path relative to config_dir
                    rel_path = package_file.relative_to(config_dir)
                    package_path = str(rel_path)
                    break

            if package_path:
                # Set includes to the package found in module_bases
                # For directories, add trailing slash to ensure recursive matching
                # (build.py handles directories with trailing slash as recursive)
                package_path_str = str(package_path)
                # Check if it's a directory (not a .py file) and add trailing slash
                if (
                    (config_dir / package_path_str).exists()
                    and (config_dir / package_path_str).is_dir()
                    and not package_path_str.endswith(".py")
                    and not package_path_str.endswith("/")
                ):
                    # Add trailing slash for recursive directory matching
                    package_path_str = f"{package_path_str}/"

                root, rel = _normalize_path_with_root(package_path_str, config_dir)
                auto_include = make_includeresolved(rel, root, "config")
                resolved_cfg["include"] = [auto_include]
                logger.trace(
                    "[resolve_build_config] Auto-set include: %s (root: %s)",
                    rel,
                    root,
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
    # Validate duplicate output paths
    # ------------------------------
    out_to_build_indices: dict[str, list[int]] = {}
    for idx, build in enumerate(resolved_builds, start=1):
        out_path = str(build["out"]["path"])
        if out_path not in out_to_build_indices:
            out_to_build_indices[out_path] = []
        out_to_build_indices[out_path].append(idx)

    # Check for duplicates
    duplicates = {
        out_path: indices
        for out_path, indices in out_to_build_indices.items()
        if len(indices) > 1
    }
    if duplicates:
        # Format error message with all duplicates
        error_parts: list[str] = []
        for out_path, indices in sorted(duplicates.items()):
            indices_str = ", ".join(f"build #{i}" for i in indices)
            error_parts.append(f'  "{out_path}": {indices_str}')
        error_msg = "Several builds have the same output path:\n" + "\n".join(
            error_parts
        )
        raise ValueError(error_msg)

    resolved_root: RootConfigResolved = {
        "builds": resolved_builds,
        "strict_config": root_cfg.get("strict_config", False),
        "watch_interval": watch_interval,
        "log_level": log_level,
    }

    return resolved_root
