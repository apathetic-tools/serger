# src/serger/config/config_resolve.py


import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from apathetic_logging import setRootLevel
from apathetic_utils import cast_hint, has_glob_chars, literal_to_set, load_toml

from serger.constants import (
    BUILD_TOOL_FIND_MAX_LINES,
    DEFAULT_CATEGORIES,
    DEFAULT_CATEGORY_ORDER,
    DEFAULT_COMMENTS_MODE,
    DEFAULT_DISABLE_BUILD_TIMESTAMP,
    DEFAULT_DOCSTRING_MODE,
    DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP,
    DEFAULT_ENV_RESPECT_GITIGNORE,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_EXTERNAL_IMPORTS,
    DEFAULT_INTERNAL_IMPORTS,
    DEFAULT_LICENSE_FALLBACK,
    DEFAULT_MAIN_MODE,
    DEFAULT_MAIN_NAME,
    DEFAULT_MODULE_MODE,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_SHIM,
    DEFAULT_SOURCE_BASES,
    DEFAULT_STITCH_MODE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_USE_PYPROJECT_METADATA,
    DEFAULT_WATCH_INTERVAL,
)
from serger.logs import getAppLogger
from serger.meta import PROGRAM_ENV
from serger.module_actions import extract_module_name_from_source_path
from serger.utils import (
    discover_installed_packages_roots,
    make_includeresolved,
    make_pathresolved,
    shorten_paths_for_display,
)
from serger.utils.utils_validation import validate_required_keys

from .config_types import (
    IncludeResolved,
    MainMode,
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
    license_text: str = ""  # Combined license text
    license_files: list[str] | None = None  # Additional license files (glob patterns)
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


def _resolve_single_license_pattern(
    pattern_str: str,
    base_dir: Path,
) -> list[Path]:
    """Resolve a single license pattern to list of file paths.

    Args:
        pattern_str: Single file/glob pattern
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        List of resolved file paths (empty if no matches)
    """
    logger = getAppLogger()
    if Path(pattern_str).is_absolute():
        # Absolute path - use as-is but resolve
        pattern_path = Path(pattern_str).resolve()
        if pattern_path.is_file():
            return [pattern_path]
        if pattern_path.is_dir():
            # Directory - skip (only files)
            logger.warning(
                "License pattern %r resolved to directory, skipping",
                pattern_str,
            )
        return []
    if has_glob_chars(pattern_str):
        # Glob pattern - resolve relative to base_dir
        all_matches = list(base_dir.glob(pattern_str))
        return [p.resolve() for p in all_matches if p.is_file()]
    # Literal file path - resolve relative to base_dir
    file_path = (base_dir / pattern_str).resolve()
    if file_path.exists() and file_path.is_file():
        return [file_path]
    return []


def _check_duplicate_license_files(
    pattern_to_files: dict[str, list[Path]],
) -> None:
    """Check for and log duplicate license files matched by multiple patterns.

    Args:
        pattern_to_files: Mapping of patterns to their matched files
    """
    logger = getAppLogger()
    # Build reverse mapping: file -> patterns that matched it
    file_to_patterns: dict[Path, list[str]] = {}
    for pattern_str, files in pattern_to_files.items():
        for file_path in files:
            if file_path not in file_to_patterns:
                file_to_patterns[file_path] = []
            file_to_patterns[file_path].append(pattern_str)

    # Find duplicates
    duplicates = {
        file_path: pattern_list
        for file_path, pattern_list in file_to_patterns.items()
        if len(pattern_list) > 1
    }
    if duplicates:
        for file_path, pattern_list in sorted(duplicates.items()):
            logger.warning(
                "License file %s matched by multiple patterns: %s. Using file once.",
                file_path,
                ", ".join(sorted(pattern_list)),
            )


def _read_license_files(matched_files: set[Path]) -> list[str]:
    """Read contents of all matched license files.

    Args:
        matched_files: Set of file paths to read

    Returns:
        List of file contents (empty strings for failed reads)
    """
    logger = getAppLogger()
    text_parts: list[str] = []
    for file_path in sorted(matched_files):
        try:
            content = file_path.read_text(encoding="utf-8")
            text_parts.append(content)
        except (OSError, UnicodeDecodeError) as e:  # noqa: PERF203
            # PERF203: try/except in loop is intentional - we need to handle
            # errors per file and continue processing other files
            logger.warning(
                "Failed to read license file %s: %s. Skipping file.",
                file_path,
                e,
            )
    return text_parts


def _handle_missing_license_patterns(
    patterns: list[str],
    pattern_to_files: dict[str, list[Path]],
    base_dir: Path,
) -> list[str]:
    """Handle missing license patterns and return warning messages.

    Args:
        patterns: Original list of patterns
        pattern_to_files: Mapping of patterns to their matched files
        base_dir: Base directory for logging

    Returns:
        List of warning messages for missing patterns
    """
    logger = getAppLogger()
    missing_patterns = [
        pattern_str
        for pattern_str in patterns
        if pattern_str not in pattern_to_files or not pattern_to_files[pattern_str]
    ]

    if not missing_patterns:
        return []

    warning_messages: list[str] = []
    for pattern_str in sorted(missing_patterns):
        logger.warning(
            "License file/pattern not found: %s (resolved from %s)",
            pattern_str,
            base_dir,
        )
        warning_messages.append(
            f"See {pattern_str} if distributed alongside this file "
            "for additional terms."
        )
    return warning_messages


def _resolve_license_file_or_pattern(
    pattern: str | list[str],
    base_dir: Path,
) -> str:
    """Resolve license file(s) or glob pattern(s) to combined text.

    Resolves glob patterns to actual files (only files, not directories),
    deduplicates if same file matched multiple times, follows symlinks,
    and reads file contents (UTF-8 encoding).

    Args:
        pattern: Single file/glob pattern or list of file/glob patterns
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Combined text from all matched files, or warning message for missing
        files/patterns
    """
    patterns: list[str] = [pattern] if isinstance(pattern, str) else pattern

    if not patterns:
        return ""

    # Collect all matched files (deduplicated)
    matched_files: set[Path] = set()
    pattern_to_files: dict[str, list[Path]] = {}

    for pattern_str in patterns:
        files = _resolve_single_license_pattern(pattern_str, base_dir)
        matched_files.update(files)
        pattern_to_files[pattern_str] = files

    # Check for duplicates
    _check_duplicate_license_files(pattern_to_files)

    # Read all matched files
    text_parts = _read_license_files(matched_files)

    # Handle missing patterns/files
    warning_messages = _handle_missing_license_patterns(
        patterns, pattern_to_files, base_dir
    )
    text_parts.extend(warning_messages)

    return "\n\n".join(text_parts) if text_parts else ""


def _resolve_license_files_patterns(  # pyright: ignore[reportUnusedFunction]
    patterns: list[str],
    base_dir: Path,
) -> str:
    """Resolve list of license file glob patterns to combined text.

    Resolves glob patterns to actual files (only files, not directories),
    deduplicates if same file matched multiple times, follows symlinks,
    and reads file contents (UTF-8 encoding).

    Args:
        patterns: List of glob patterns for license files
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Combined text from all matched files (to be appended to license text)

    Note: This function will be used in Phase 3 and Phase 4 of license
    support implementation.
    """
    return _resolve_license_file_or_pattern(patterns, base_dir)


def _resolve_license_file_value(file_val: Any, base_dir: Path) -> str:
    """Resolve license file value (str or list[str]) to text.

    Args:
        file_val: File value from license dict (str or list[str])
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Combined text from resolved files (empty string if none found)
    """
    if file_val is None:
        return ""

    if isinstance(file_val, str):
        return _resolve_license_file_or_pattern(file_val, base_dir)

    if isinstance(file_val, list):
        # Convert to list of strings
        pattern_list: list[str] = []
        for item in file_val:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(item, str):
                pattern_list.append(item)
            elif item is not None:
                pattern_list.append(str(item))  # pyright: ignore[reportUnknownArgumentType]
        if pattern_list:
            return _resolve_license_file_or_pattern(pattern_list, base_dir)

    return ""


def _extract_license_from_project(license_val: Any, base_dir: Path) -> str:
    """Extract license text from project license field.

    Handles string format and dict format with file/text/expression keys.
    Priority: text > expression > file.

    Args:
        license_val: License value from project dict (str or dict)
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Combined license text (empty string if no license found)
    """
    if isinstance(license_val, str):
        # String format: Store as-is
        return license_val

    if not isinstance(license_val, dict):
        return ""

    # Dict format: Handle text, expression, and file keys
    # Priority: text > expression > file
    text_parts: list[str] = []

    # Check for text key (highest priority)
    if "text" in license_val:
        text_val = license_val.get("text")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if isinstance(text_val, str) and text_val:
            text_parts.append(text_val)
    # Check for expression key (alias for text, second priority)
    elif "expression" in license_val:
        expr_val = license_val.get("expression")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if isinstance(expr_val, str) and expr_val:
            text_parts.append(expr_val)

    # Check for file key (lowest priority, only if text/expression not present)
    if not text_parts and "file" in license_val:
        file_val = license_val.get("file")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        resolved_text = _resolve_license_file_value(file_val, base_dir)
        if resolved_text:
            text_parts.append(resolved_text)

    # Combine all text parts
    if text_parts:
        return "\n\n".join(text_parts)

    return ""


def _extract_license_files_from_project(
    license_files_val: Any,
) -> list[str] | None:
    """Extract license-files field from project dict.

    Args:
        license_files_val: License-files value from project dict

    Returns:
        List of license file patterns, or None if not present
    """
    if license_files_val is None:
        return None

    if isinstance(license_files_val, list):
        # Convert to list of strings
        license_files: list[str] = []
        for item in license_files_val:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(item, str):
                license_files.append(item)
            elif item is not None:
                license_files.append(str(item))  # pyright: ignore[reportUnknownArgumentType]
        return license_files if license_files else None

    if isinstance(license_files_val, str):
        # Single string pattern
        return [license_files_val]

    return None


def _resolve_license_dict_value(
    license_dict: dict[str, str | list[str]], base_dir: Path
) -> str:
    """Resolve license dict to text using priority: text > expression > file.

    Args:
        license_dict: License dict with text/expression/file keys
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Resolved license text (empty string if none found)
    """
    # Check for text key (highest priority)
    if "text" in license_dict:
        text_val = license_dict.get("text")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if isinstance(text_val, str) and text_val:
            return text_val
    # Check for expression key (alias for text, second priority)
    if "expression" in license_dict:
        expr_val = license_dict.get("expression")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        if isinstance(expr_val, str) and expr_val:
            return expr_val
    # Check for file key (lowest priority, only if text/expression not present)
    if "file" in license_dict:
        file_val = license_dict.get("file")  # pyright: ignore[reportUnknownVariableType,reportUnknownMemberType]
        return _resolve_license_file_value(file_val, base_dir)
    return ""


def _resolve_license_field(
    license_val: str | dict[str, str | list[str]] | None,
    license_files_val: list[str] | None,
    base_dir: Path,
) -> str:
    """Resolve license field (string or dict) and license_files to combined text.

    Processing order: license field first, then license_files.

    Args:
        license_val: License value from config (str or dict)
        license_files_val: License files patterns from config (list of glob patterns)
        base_dir: Base directory for resolving relative paths and globs

    Returns:
        Combined license text (always non-empty, uses fallback if needed)
    """
    text_parts: list[str] = []

    # Process license field first
    if license_val is not None:
        if isinstance(license_val, str):
            # String format: Store as-is
            if license_val:
                text_parts.append(license_val)
        else:
            # Dict format: Resolve using priority
            # pyright: ignore[reportUnnecessaryIsInstance] - needed for type narrowing
            resolved_text = _resolve_license_dict_value(license_val, base_dir)
            if resolved_text:
                text_parts.append(resolved_text)

    # Then process license_files field (append to license result)
    if license_files_val:
        resolved_files_text = _resolve_license_files_patterns(
            license_files_val, base_dir
        )
        if resolved_files_text:
            text_parts.append(resolved_files_text)

    # Combine all text parts
    combined_text = "\n\n".join(text_parts) if text_parts else ""

    # Final fallback: If empty, use DEFAULT_LICENSE_FALLBACK
    if not combined_text:
        combined_text = DEFAULT_LICENSE_FALLBACK

    return combined_text


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

    # Handle license (can be string or dict with file/text/expression keys)
    license_val = project.get("license")
    license_text = _extract_license_from_project(license_val, pyproject_path.parent)

    # Extract license-files field (list of glob patterns)
    license_files_val = project.get("license-files")
    license_files = _extract_license_files_from_project(license_files_val)

    # Extract authors
    authors_text = _extract_authors_from_project(project)

    return PyprojectMetadata(
        name=name if isinstance(name, str) else "",
        version=version if isinstance(version, str) else "",
        description=description if isinstance(description, str) else "",
        license_text=license_text,
        license_files=license_files,
        authors=authors_text,
    )


def _is_configless_build(root_cfg: RootConfig | None) -> bool:
    """Check if this is a configless build (no config file).

    Configless builds are detected by checking if root_cfg is minimal:
    has no include/exclude/out/package/order fields (set via CLI).

    Args:
        root_cfg: Root config (may be None)

    Returns:
        True if this is a configless build, False otherwise
    """
    if root_cfg is None:
        return True
    # Check if root_cfg is minimal (empty or only has minimal fields)
    # This indicates a configless build created in cli.py
    root_keys = set(root_cfg.keys())
    # Configless builds have no include/exclude/out fields (set via CLI)
    has_build_fields = any(
        key in root_keys for key in ("include", "exclude", "out", "package", "order")
    )
    return not has_build_fields


def _should_use_pyproject_metadata(
    build_cfg: RootConfig,
    root_cfg: RootConfig | None,
) -> bool:
    """Determine if pyproject.toml metadata should be extracted for this build.

    Pyproject.toml metadata is used by default (DEFAULT_USE_PYPROJECT_METADATA) unless
    explicitly disabled. Explicit enablement (use_pyproject_metadata=True or
    pyproject_path set) always takes precedence and enables it even if it would
    otherwise be disabled.

    Note: Package name is always extracted from pyproject.toml (if available) for
    resolution purposes, regardless of this setting. This setting only controls
    extraction of other metadata (display_name, description, authors, license, version).

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        True if pyproject.toml should be used, False otherwise
    """
    root_use_pyproject_metadata = (root_cfg or {}).get("use_pyproject_metadata")
    root_pyproject_path = (root_cfg or {}).get("pyproject_path")
    build_use_pyproject_metadata = build_cfg.get("use_pyproject_metadata")
    build_pyproject_path = build_cfg.get("pyproject_path")

    # Check if this is a configless build
    is_configless = _is_configless_build(root_cfg)

    # Build-level explicit disablement always takes precedence
    if build_use_pyproject_metadata is False:
        return False

    # Root-level explicit disablement takes precedence unless build overrides
    # (build-level pyproject_path is considered an override)
    if root_use_pyproject_metadata is False and build_pyproject_path is None:
        return False

    # For configless builds, use DEFAULT_USE_PYPROJECT_METADATA (unless disabled above)
    if is_configless:
        return DEFAULT_USE_PYPROJECT_METADATA

    # For non-configless builds, also use DEFAULT_USE_PYPROJECT_METADATA unless
    # explicitly disabled (but allow explicit enablement to override)
    if (
        root_use_pyproject_metadata is True
        or root_pyproject_path is not None
        or build_use_pyproject_metadata is True
        or build_pyproject_path is not None
    ):
        return True

    # Default to DEFAULT_USE_PYPROJECT_METADATA for non-configless builds too
    return DEFAULT_USE_PYPROJECT_METADATA


def _resolve_pyproject_path(
    build_cfg: RootConfig,
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


def validate_and_normalize_module_actions(  # noqa: C901, PLR0912, PLR0915
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
            if action_val in ("move", "copy", "rename"):
                # dest is required for move/copy/rename
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
                # For rename, validate that dest doesn't contain dots
                if action_val == "rename" and "." in dest_val:
                    msg = (
                        f"module_actions[{idx}]['dest'] for 'rename' action "
                        f"must not contain dots. Got dest='{dest_val}'. "
                        f"Use 'move' action to move modules down the tree"
                    )
                    raise ValueError(msg)
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


def _apply_metadata_fields(
    resolved_cfg: dict[str, Any],
    metadata: PyprojectMetadata,
    pyproject_path: Path,
    *,
    explicitly_requested: bool,
) -> None:
    """Apply extracted metadata fields to resolved config.

    Pyproject.toml metadata is always a fallback - it only fills missing fields.
    User-set values (empty strings or non-empty strings) always take precedence
    and are never overwritten.

    Note: Empty strings ("") in config are preserved as they represent an
    intentional choice. None or missing fields can be filled by pyproject.

    Note: Package name is NOT set here - it's handled in _apply_pyproject_metadata()
    and is always extracted if available, regardless of use_pyproject_metadata.

    Note: description, authors, and license are only applied when
    explicitly_requested is True (use_pyproject_metadata=True or pyproject_path set).

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        metadata: Extracted metadata
        pyproject_path: Path to pyproject.toml (for logging)
        explicitly_requested: True if pyproject metadata should be used
            (use_pyproject_metadata=True, pyproject_path set, or default for
            configless builds). Controls whether description, authors, and
            license are applied.
    """
    logger = getAppLogger()

    # Apply fields from pyproject.toml
    # Version is resolved immediately (user -> pyproject) rather than storing
    # _pyproject_version separately
    if (
        explicitly_requested
        and metadata.version
        and ("version" not in resolved_cfg or not resolved_cfg.get("version"))
    ):
        resolved_cfg["version"] = metadata.version

    # For description, authors, license:
    # - Only applied when explicitly_requested is True (use_pyproject_metadata=True
    #   or pyproject_path set)
    # - None or missing = not set, can be filled by pyproject (fallback)
    # - "" = explicitly set to empty, should NOT be overwritten
    # - non-empty string = explicitly set by user, should NEVER be overwritten
    # Note: display_name is NOT set here - it uses package as fallback
    # (handled after package resolution, since package may come from pyproject)

    if explicitly_requested:
        if metadata.description:
            current = resolved_cfg.get("description")
            if current is None:
                resolved_cfg["description"] = metadata.description

        if metadata.authors:
            current = resolved_cfg.get("authors")
            if current is None:
                resolved_cfg["authors"] = metadata.authors

        # Apply license from pyproject (only if not already set in config)
        # Note: This only runs when explicitly_requested=True
        # (use_pyproject_metadata=True or pyproject_path set),
        # same as description and authors fields.
        # Process license_text first, then license_files
        if metadata.license_text or metadata.license_files:
            current_license = resolved_cfg.get("license")
            if current_license is None:
                # Combine pyproject license_text (already resolved) with license_files
                text_parts: list[str] = []
                if metadata.license_text:
                    text_parts.append(metadata.license_text)
                if metadata.license_files:
                    resolved_files_text = _resolve_license_files_patterns(
                        metadata.license_files, pyproject_path.parent
                    )
                    if resolved_files_text:
                        text_parts.append(resolved_files_text)
                # Combine and use fallback if empty
                pyproject_license_text = (
                    "\n\n".join(text_parts) if text_parts else DEFAULT_LICENSE_FALLBACK
                )
                resolved_cfg["license"] = pyproject_license_text

    if metadata.has_any():
        logger.trace(f"[resolve_build_config] Extracted metadata from {pyproject_path}")


def _apply_pyproject_metadata(
    resolved_cfg: dict[str, Any],
    *,
    build_cfg: RootConfig,
    root_cfg: RootConfig | None,
    config_dir: Path,
) -> None:
    """Extract and apply pyproject.toml metadata to resolved config.

    Extracts all metadata from pyproject.toml once, then:
    - Always uses package name for resolution (if not already set)
    - Uses other metadata (display_name, description, authors, license, version)
      only if use_pyproject_metadata is enabled

    Args:
        resolved_cfg: Mutable resolved config dict (modified in place)
        build_cfg: Original build config
        root_cfg: Root config (may be None)
        config_dir: Config directory for path resolution
    """
    logger = getAppLogger()

    # Try to find pyproject.toml
    pyproject_path = _resolve_pyproject_path(build_cfg, root_cfg, config_dir)
    if not pyproject_path or not pyproject_path.exists():
        return

    # Extract all metadata once (if available)
    # Use required=False since we handle errors gracefully below
    try:
        metadata = extract_pyproject_metadata(pyproject_path, required=False)
        if metadata is None:
            return
    except (RuntimeError, ValueError, FileNotFoundError) as e:
        # If extraction fails, silently continue (package will be resolved via
        # other means)
        logger.trace(
            "[_apply_pyproject_metadata] Failed to extract metadata from %s: %s",
            pyproject_path,
            e,
        )
        return

    # Always extract package name for resolution purposes (if not already set)
    if metadata.name and not resolved_cfg.get("package"):
        resolved_cfg["package"] = metadata.name
        logger.info(
            "Package name '%s' extracted from pyproject.toml for resolution",
            metadata.name,
        )

    # Apply other metadata only if use_pyproject_metadata is enabled
    # (This includes configless builds which use pyproject by default)
    should_use = _should_use_pyproject_metadata(build_cfg, root_cfg)
    if not should_use:
        return

    _apply_metadata_fields(
        resolved_cfg,
        metadata,
        pyproject_path,
        explicitly_requested=should_use,
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
    build_cfg: RootConfig,
    root_cfg: RootConfig | None,
) -> PostProcessingConfigResolved:
    """Resolve post-processing configuration with cascade and validation.

    Args:
        build_cfg: Build config
        root_cfg: Root config (may be None)

    Returns:
        Resolved post-processing configuration
    """
    logger = getAppLogger()

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


def _try_resolve_path_in_bases(
    raw: Path | str,
    source_bases: list[str] | None = None,
    installed_bases: list[str] | None = None,
) -> tuple[Path, Path | str] | None:
    """Try to resolve a relative path in source_bases or installed_bases.

    Checks if a relative path exists in the provided bases (source_bases first,
    then installed_bases as fallback). Returns the resolved root and relative
    path if found, None otherwise.

    For glob patterns (e.g., "mypkg/**"), extracts the base path (e.g., "mypkg")
    and checks if that exists in the bases.

    Args:
        raw: Relative path to resolve
        source_bases: Optional list of source base directories (absolute paths)
        installed_bases: Optional list of installed base directories
            (absolute paths)

    Returns:
        Tuple of (root, rel) if path found in bases, None otherwise
    """
    logger = getAppLogger()
    raw_str = str(raw)

    # For glob patterns, extract the base path (part before glob)
    if has_glob_chars(raw_str):
        # Extract base path before first glob character
        glob_chars = ["*", "?", "[", "{"]
        glob_pos = min(
            (raw_str.find(c) for c in glob_chars if c in raw_str),
            default=len(raw_str),
        )
        # Find the last / before the glob (or use entire path if no /)
        path_before_glob = raw_str[:glob_pos]
        last_slash = path_before_glob.rfind("/")
        if last_slash >= 0:
            base_path_str = path_before_glob[:last_slash]
        else:
            # No slash found, entire path before glob is the base
            base_path_str = path_before_glob
    else:
        # No glob, use entire path as base
        base_path_str = raw_str

    # Try source_bases first (higher priority)
    if source_bases:
        for base_str in source_bases:
            base_path = Path(base_str).resolve()
            candidate_path = base_path / base_path_str
            if candidate_path.exists():
                logger.trace(
                    f"Found path in source_bases: {raw_str!r} "
                    f"(base: {base_path_str!r}) in {base_str}"
                )
                return base_path, raw_str

    # Try installed_bases as fallback
    if installed_bases:
        for base_str in installed_bases:
            base_path = Path(base_str).resolve()
            candidate_path = base_path / base_path_str
            if candidate_path.exists():
                logger.trace(
                    f"Found path in installed_bases: {raw_str!r} "
                    f"(base: {base_path_str!r}) in {base_str}"
                )
                return base_path, raw_str

    return None


def _normalize_path_with_root(
    raw: Path | str,
    context_root: Path | str,
    *,
    source_bases: list[str] | None = None,
    installed_bases: list[str] | None = None,
) -> tuple[Path, Path | str]:
    """Normalize a user-provided path (from CLI or config).

    - If absolute → treat that path as its own root.
      * `/abs/path/**` → root=/abs/path, rel="**"
      * `/abs/path/`   → root=/abs/path, rel="**"  (treat as contents)
      * `/abs/path`    → root=/abs/path, rel="."   (treat as literal)
    - If relative → try context_root first, then source_bases, then installed_bases
      * If found in bases, use that base as root
      * Otherwise, use context_root as root

    Args:
        raw: Path to normalize
        context_root: Default context root (config_dir or cwd)
        source_bases: Optional list of source base directories
            (for fallback lookup)
        installed_bases: Optional list of installed base directories
            (for fallback lookup)
    """
    logger = getAppLogger()
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
        # --- relative path case ---
        # Try to resolve in bases first (source_bases > installed_bases)
        resolved = _try_resolve_path_in_bases(
            raw,
            source_bases=source_bases,
            installed_bases=installed_bases,
        )
        if resolved is not None:
            root, rel = resolved
        else:
            # Not found in bases, use context_root
            root = Path(context_root).resolve()
            # preserve literal string if user provided one
            rel = raw if isinstance(raw, str) else Path(raw)

    logger.trace(f"Normalized: raw={raw!r} → root={root}, rel={rel}")
    return root, rel


def _extract_source_bases_from_includes(  # noqa: PLR0912
    includes: list[IncludeResolved],
    config_dir: Path,
) -> list[str]:
    """Extract parent directories from includes to use as source_bases.

    For each include, extracts the first directory component that contains
    packages (e.g., "src/" from "src/mypkg/main.py" or "src/mypkg/**/*.py").
    Returns absolute paths. Skips filesystem root and config_dir itself.
    Returns a deduplicated list preserving order.

    Args:
        includes: List of resolved includes
        config_dir: Config directory for resolving paths

    Returns:
        List of module base directories as absolute paths
    """
    logger = getAppLogger()
    config_dir_resolved = config_dir.resolve()
    bases: list[str] = []
    seen_bases: set[str] = set()

    for inc in includes:
        # Get the root directory for this include
        include_root = Path(inc["root"]).resolve()
        include_path = inc["path"]

        # Extract the first directory component from the path
        if isinstance(include_path, Path):
            # Resolved Path object: get first component
            path_parts = include_path.parts
            if path_parts:
                # Get first directory component
                first_dir = path_parts[0]
                parent_dir = (include_root / first_dir).resolve()
            else:
                parent_dir = include_root
        else:
            # String pattern: extract first directory component
            path_str = str(include_path)
            # Remove glob patterns and trailing slashes
            if path_str.endswith("/**"):
                # Recursive pattern: remove "/**"
                path_str = path_str.removesuffix("/**")
            elif path_str.endswith("/"):
                # Directory: remove trailing slash
                path_str = path_str.rstrip("/")

            # Extract first directory component
            # For "src/mypkg/main.py" → "src"
            # For "src/mypkg/**/*.py" → "src"
            # For "lib/otherpkg/" → "lib"
            if "/" in path_str:
                # Get first component (before first /)
                first_component = path_str.split("/", 1)[0]
                # Remove any glob chars from first component
                if has_glob_chars(first_component):
                    # If first component has glob, use include_root
                    parent_dir = include_root
                else:
                    parent_dir = (include_root / first_component).resolve()
            else:
                # Single filename or pattern: use root
                parent_dir = include_root

        # Skip if parent is filesystem root or config_dir itself
        if parent_dir in {parent_dir.anchor, config_dir_resolved}:
            continue

        # Store as absolute path
        base_str = str(parent_dir)

        # Deduplicate while preserving order
        if base_str not in seen_bases:
            seen_bases.add(base_str)
            bases.append(base_str)
            logger.trace(
                "[MODULE_BASES] Extracted base from include: %s → %s",
                inc["path"],
                base_str,
            )

    return bases


# --------------------------------------------------------------------------- #
# main per-build resolver
# --------------------------------------------------------------------------- #


def _get_first_level_modules_from_base(
    base_str: str,
    _config_dir: Path,
) -> list[str]:
    """Get first-level module/package names from a single module_base directory.

    Scans only the immediate children of the module_base directory (not
    recursive). Returns a sorted list of package/module names.

    Package detection logic:
    - Directories with __init__.py are definitely packages (standard Python)
    - Directories in source_bases are also considered packages (namespace
      packages, mimics modern Python behavior)
    - .py files at first level are modules

    Args:
        base_str: Module base directory path (absolute)
        _config_dir: Config directory (unused, kept for compatibility)

    Returns:
        Sorted list of first-level module/package names found in the base
    """
    logger = getAppLogger()
    modules: list[str] = []

    # base_str is already an absolute path
    base_path = Path(base_str).resolve()

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
                    # Directory in source_bases is considered a package
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
    source_bases: list[str],
    config_dir: Path,
) -> list[str]:
    """Get first-level module/package names from source_bases directories.

    Scans only the immediate children of each source_base directory (not
    recursive). Returns a list preserving the order of source_bases, with
    modules from each base sorted but not deduplicated across bases.

    Args:
        source_bases: List of source base directory paths (absolute)
        config_dir: Config directory (unused, kept for compatibility)

    Returns:
        List of first-level module/package names found in source_bases,
        preserving source_bases order
    """
    modules: list[str] = []

    for base_str in source_bases:
        base_modules = _get_first_level_modules_from_base(base_str, config_dir)
        modules.extend(base_modules)

    return modules


def _has_main_function(module_path: Path) -> bool:
    """Check if a module path contains a main function.

    Looks for:
    - `def main(` in any Python file
    - `if __name__ == "__main__":` in any Python file

    Args:
        module_path: Path to module (directory or file)

    Returns:
        True if main function or __main__ block found
    """
    import ast  # noqa: PLC0415

    if module_path.is_file() and module_path.suffix == ".py":
        files_to_check = [module_path]
    elif module_path.is_dir():
        # Check all Python files in directory (non-recursive)
        files_to_check = list(module_path.glob("*.py"))
    else:
        return False

    for file_path in files_to_check:
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                # Check for def main(
                if isinstance(node, ast.FunctionDef) and node.name == "main":
                    return True
                # Check for if __name__ == '__main__' block
                if isinstance(node, ast.If):
                    test = node.test
                    if (
                        isinstance(test, ast.Compare)
                        and isinstance(test.left, ast.Name)
                        and test.left.id == "__name__"
                        and len(test.ops) == 1
                        and isinstance(test.ops[0], ast.Eq)
                        and len(test.comparators) == 1
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"
                    ):
                        return True
        except (SyntaxError, UnicodeDecodeError, OSError):  # noqa: PERF203
            # Skip files that can't be parsed
            continue

    return False


def _infer_packages_from_includes(  # noqa: C901, PLR0912, PLR0915
    includes: list[IncludeResolved],
    source_bases: list[str],
    config_dir: Path,
) -> list[str]:
    """Infer package names from include paths using multiple strategies.

    Uses strategies in priority order:
    1. Filter by source_bases (if configured)
    2. Check __init__.py (definitive package markers)
    3. Check __main__.py (executable package markers)
    4. Extract from common prefix
    5. Validate against source_bases (ensure exists)
    6. Use most common first-level directory (when multiple candidates)

    Args:
        includes: List of resolved include patterns
        source_bases: List of source base directory paths
        config_dir: Config directory for resolving relative paths

    Returns:
        List of inferred package names (may be empty or contain multiple candidates)
    """
    if not includes:
        return []

    logger = getAppLogger()
    candidates: set[str] = set()
    path_strings: list[str] = []

    # Extract path strings from includes
    for inc in includes:
        path_val = inc.get("path")
        if isinstance(path_val, (Path, str)):  # pyright: ignore[reportUnnecessaryIsInstance]
            path_str = str(path_val)
            # Remove trailing slashes and normalize
            path_str = path_str.rstrip("/")
            if path_str:
                path_strings.append(path_str)

    if not path_strings:
        return []

    # Strategy 1: Filter by source_bases (if configured)
    filtered_paths: list[str] = []
    if source_bases:
        for path_str in path_strings:
            # Check if path is within any module_base
            for base_str in source_bases:
                # base_str is already an absolute path
                base_path = Path(base_str).resolve()
                # Try to resolve path relative to config_dir
                try:
                    path_obj = (config_dir / path_str).resolve()
                    # Check if path is within base_path
                    try:
                        path_obj.relative_to(base_path)
                        filtered_paths.append(path_str)
                        break
                    except ValueError:
                        # Not within this base, try next
                        continue
                except (OSError, ValueError):
                    # Path resolution failed, skip
                    continue
    else:
        # No source_bases, use all paths
        filtered_paths = path_strings

    if not filtered_paths:
        return []

    # Strategy 2 & 3: Check for __init__.py and __main__.py
    for path_str in filtered_paths:
        path_obj = (config_dir / path_str).resolve()
        if not path_obj.exists():
            continue

        # Check if it's a file or directory
        if path_obj.is_file():
            # Check if parent has __init__.py or __main__.py
            parent = path_obj.parent
            if (parent / "__init__.py").exists() or (parent / "__main__.py").exists():
                candidates.add(parent.name)
            # Also check if file itself is __init__.py or __main__.py
            if path_obj.name in {"__init__.py", "__main__.py"}:
                candidates.add(parent.name)
        elif path_obj.is_dir():
            # Check if directory has __init__.py or __main__.py
            if (path_obj / "__init__.py").exists() or (
                path_obj / "__main__.py"
            ).exists():
                candidates.add(path_obj.name)

    # Strategy 4: Extract from common prefix
    if not candidates:
        # Find common prefix of all paths
        common_prefix = _find_common_path_prefix(filtered_paths, config_dir)
        if common_prefix:
            # Get first directory after common prefix for each path
            common_path = (config_dir / common_prefix).resolve()
            for path_str in filtered_paths:
                try:
                    path_obj = (config_dir / path_str).resolve()
                    try:
                        rel_path = path_obj.relative_to(common_path)
                        # Get first component
                        parts = list(rel_path.parts)
                        if parts:
                            first_part = parts[0]
                            if first_part and first_part != ".":
                                candidates.add(first_part)
                    except ValueError:
                        # Not relative to common prefix, skip
                        continue
                except (OSError, ValueError):
                    continue

    # Strategy 5: Validate against source_bases (ensure exists)
    if source_bases and candidates:
        valid_modules = _get_first_level_modules_from_bases(source_bases, config_dir)
        candidates = {c for c in candidates if c in valid_modules}

    # Strategy 6: If multiple candidates, use most common first-level directory
    if len(candidates) > 1:
        # Count occurrences in original paths
        first_level_counts: dict[str, int] = {}
        for path_str in filtered_paths:
            try:
                path_obj = (config_dir / path_str).resolve()
                # Try to find first-level directory relative to source_bases
                for base_str in source_bases:
                    # base_str is already an absolute path
                    base_path = Path(base_str).resolve()
                    try:
                        rel_path = path_obj.relative_to(base_path)
                        parts = list(rel_path.parts)
                        if parts:
                            first_part = parts[0]
                            if first_part in candidates:
                                first_level_counts[first_part] = (
                                    first_level_counts.get(first_part, 0) + 1
                                )
                        break
                    except ValueError:
                        continue
            except (OSError, ValueError):
                continue

        # Return most common, or all if tied
        if first_level_counts:
            max_count = max(first_level_counts.values())
            most_common = [
                pkg for pkg, count in first_level_counts.items() if count == max_count
            ]
            if len(most_common) == 1:
                logger.trace(
                    "[_infer_packages_from_includes] Using most common package: %s",
                    most_common[0],
                )
                return most_common

    result = sorted(candidates)
    if result:
        logger.trace("[_infer_packages_from_includes] Inferred packages: %s", result)
    return result


def _find_common_path_prefix(paths: list[str], config_dir: Path) -> str | None:
    """Find the longest common path prefix of a list of paths.

    Args:
        paths: List of path strings (relative to config_dir)
        config_dir: Config directory for resolving paths

    Returns:
        Common prefix path string (relative to config_dir), or None if no common prefix
    """
    if not paths:
        return None

    # Resolve all paths and find common prefix
    resolved_paths: list[Path] = []
    for path_str in paths:
        try:
            resolved = (config_dir / path_str).resolve()
            if resolved.exists():
                resolved_paths.append(resolved)
        except (OSError, ValueError):  # noqa: PERF203
            continue

    if not resolved_paths:
        return None

    # Find common prefix by comparing path parts
    common_parts: list[str] = []
    first_path = resolved_paths[0]
    max_parts = len(first_path.parts)

    for i in range(max_parts):
        part = first_path.parts[i]
        # Check if all paths have this part at this position
        if all(i < len(p.parts) and p.parts[i] == part for p in resolved_paths[1:]):
            common_parts.append(part)
        else:
            break

    if not common_parts:
        return None

    # Reconstruct path and make relative to config_dir
    common_path = Path(*common_parts)
    try:
        rel_path = common_path.relative_to(config_dir.resolve())
        return str(rel_path)
    except ValueError:
        # Not relative to config_dir, return as-is
        return str(common_path)


def _resolve_includes(  # noqa: PLR0912
    resolved_cfg: dict[str, Any],
    *,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
    source_bases: list[str] | None = None,
    installed_bases: list[str] | None = None,
) -> list[IncludeResolved]:
    logger = getAppLogger()
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
                root, rel = _normalize_path_with_root(
                    path_str,
                    config_dir,
                    source_bases=source_bases,
                    installed_bases=installed_bases,
                )
                inc = make_includeresolved(rel, root, "config")
                if dest_str:
                    # dest is relative to output dir, no normalization
                    inc["dest"] = Path(dest_str)
                includes.append(inc)
            else:
                # String format: "path/to/files"
                root, rel = _normalize_path_with_root(
                    raw,
                    config_dir,
                    source_bases=source_bases,
                    installed_bases=installed_bases,
                )
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
    logger = getAppLogger()
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
    else:
        # Check ENV (SERGER_RESPECT_GITIGNORE or RESPECT_GITIGNORE)
        env_respect = os.getenv(
            f"{PROGRAM_ENV}_{DEFAULT_ENV_RESPECT_GITIGNORE}"
        ) or os.getenv(DEFAULT_ENV_RESPECT_GITIGNORE)
        if env_respect is not None:
            # Parse boolean from string (accept "true", "1", "yes", etc.)
            env_respect_lower = env_respect.lower()
            respect_gitignore = env_respect_lower in ("true", "1", "yes", "on")
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
    logger = getAppLogger()
    logger.trace("[resolve_output] Resolving output directory")

    if getattr(args, "output", None):
        # Full override → relative to cwd
        root, rel = _normalize_path_with_root(args.output, cwd)
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
    build_cfg: RootConfig,
    args: argparse.Namespace,
    config_dir: Path,
    cwd: Path,
) -> RootConfigResolved:
    """Resolve a flat RootConfig into a RootConfigResolved.

    Applies CLI overrides, normalizes paths, merges gitignore behavior,
    and attaches provenance metadata.
    """
    logger = getAppLogger()
    logger.trace("[resolve_build_config] Starting resolution for config")

    # Make a mutable copy
    resolved_cfg: dict[str, Any] = dict(build_cfg)

    # Log package source if provided in config
    if "package" in build_cfg and build_cfg.get("package"):
        logger.info(
            "Package name '%s' provided in config",
            build_cfg.get("package"),
        )

    # Set log_level if not present (for tests that call resolve_build_config directly)
    if "log_level" not in resolved_cfg:
        root_log = None
        log_level = logger.determineLogLevel(args=args, root_log_level=root_log)
        resolved_cfg["log_level"] = log_level

    # root provenance for all resolutions
    meta: MetaBuildConfigResolved = {
        "cli_root": cwd,
        "config_root": config_dir,
    }

    # ------------------------------
    # Auto-discover installed packages (resolved early for use in includes)
    # ------------------------------
    if "auto_discover_installed_packages" not in resolved_cfg:
        resolved_cfg["auto_discover_installed_packages"] = True

    # ------------------------------
    # Installed packages bases (resolved early for use in includes)
    # ------------------------------
    # Convert str to list[str] if needed, then resolve relative paths to absolute
    # Priority: user-specified > auto-discovery > empty list
    if "installed_bases" in resolved_cfg:
        installed_bases = resolved_cfg["installed_bases"]
        config_installed_bases = (
            [installed_bases] if isinstance(installed_bases, str) else installed_bases
        )
        # Resolve relative paths to absolute
        resolved_installed_bases: list[str] = []
        for base in config_installed_bases:
            base_path = (config_dir / base).resolve()
            resolved_installed_bases.append(str(base_path))
        resolved_cfg["installed_bases"] = resolved_installed_bases
    # Not specified - use auto-discovery if enabled
    elif resolved_cfg["auto_discover_installed_packages"]:
        discovered_bases = discover_installed_packages_roots()
        resolved_cfg["installed_bases"] = discovered_bases
        if discovered_bases:
            logger.debug(
                "[INSTALLED_BASES] Auto-discovered %d installed package root(s): %s",
                len(discovered_bases),
                shorten_paths_for_display(
                    discovered_bases, cwd=cwd, config_dir=config_dir
                ),
            )
    else:
        # Auto-discovery disabled and not specified - use empty list
        resolved_cfg["installed_bases"] = []

    # --- Includes ---------------------------
    # Resolve source_bases to absolute paths for include resolution
    # (they may be relative paths from config)
    resolved_source_bases: list[str] | None = None
    if "source_bases" in resolved_cfg:
        source_bases_raw = resolved_cfg["source_bases"]
        source_bases_list = (
            [source_bases_raw]
            if isinstance(source_bases_raw, str)
            else source_bases_raw
        )
        resolved_source_bases = [
            str((config_dir / base).resolve()) for base in source_bases_list
        ]
    resolved_cfg["include"] = _resolve_includes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
        source_bases=resolved_source_bases,
        installed_bases=resolved_cfg.get("installed_bases"),
    )
    logger.trace(
        f"[resolve_build_config] Resolved {len(resolved_cfg['include'])} include(s)"
    )

    # --- Extract source_bases from includes (before resolving source_bases) ---
    # Separate CLI and config includes for priority ordering
    cli_includes: list[IncludeResolved] = [
        inc for inc in resolved_cfg["include"] if inc["origin"] == "cli"
    ]
    config_includes: list[IncludeResolved] = [
        inc for inc in resolved_cfg["include"] if inc["origin"] == "config"
    ]

    # Extract bases from includes (CLI first, then config)
    cli_bases = _extract_source_bases_from_includes(cli_includes, config_dir)
    config_bases = _extract_source_bases_from_includes(config_includes, config_dir)

    # --- Excludes ---------------------------
    resolved_cfg["exclude"] = _resolve_excludes(
        resolved_cfg,
        args=args,
        config_dir=config_dir,
        cwd=cwd,
        root_cfg=None,
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
    # Log level is resolved in resolve_config() before calling this function
    # This is a no-op placeholder - the value should already be set
    # (resolve_config sets it and then calls this function)

    # ------------------------------
    # Strict config
    # ------------------------------
    if "strict_config" not in resolved_cfg:
        resolved_cfg["strict_config"] = DEFAULT_STRICT_CONFIG

    # ------------------------------
    # Stitch mode (resolved first, used for import defaults)
    # ------------------------------
    if "stitch_mode" not in resolved_cfg:
        resolved_cfg["stitch_mode"] = DEFAULT_STITCH_MODE

    # Get the resolved stitch_mode for use in import defaults
    stitch_mode = resolved_cfg["stitch_mode"]
    if not isinstance(stitch_mode, str):
        msg = "stitch_mode must be a string"
        raise TypeError(msg)

    # ------------------------------
    # Module mode
    # ------------------------------
    if "module_mode" not in resolved_cfg:
        resolved_cfg["module_mode"] = DEFAULT_MODULE_MODE

    # ------------------------------
    # Shim setting
    # ------------------------------
    valid_shim_values = literal_to_set(ShimSetting)
    if "shim" in resolved_cfg:
        shim_val = resolved_cfg["shim"]
        # Validate value
        if shim_val not in valid_shim_values:
            valid_str = ", ".join(repr(v) for v in sorted(valid_shim_values))
            msg = f"Invalid shim value: {shim_val!r}. Must be one of: {valid_str}"
            raise ValueError(msg)
    else:
        resolved_cfg["shim"] = DEFAULT_SHIM

    # ------------------------------
    # Module actions
    # ------------------------------
    if "module_actions" in resolved_cfg:
        # Validate and normalize to list format
        resolved_cfg["module_actions"] = validate_and_normalize_module_actions(
            resolved_cfg["module_actions"], config_dir=config_dir
        )
    else:
        # Always set to empty list in resolved config (fully resolved)
        resolved_cfg["module_actions"] = []

    # ------------------------------
    # Import handling
    # ------------------------------
    if "internal_imports" not in resolved_cfg:
        resolved_cfg["internal_imports"] = DEFAULT_INTERNAL_IMPORTS[stitch_mode]

    if "external_imports" not in resolved_cfg:
        resolved_cfg["external_imports"] = DEFAULT_EXTERNAL_IMPORTS[stitch_mode]

    # ------------------------------
    # Comments mode
    # ------------------------------
    if "comments_mode" not in resolved_cfg:
        resolved_cfg["comments_mode"] = DEFAULT_COMMENTS_MODE

    # ------------------------------
    # Docstring mode
    # ------------------------------
    if "docstring_mode" not in resolved_cfg:
        resolved_cfg["docstring_mode"] = DEFAULT_DOCSTRING_MODE

    # ------------------------------
    # Module bases
    # ------------------------------
    # Convert str to list[str] if needed, then merge with bases from includes
    if "source_bases" in resolved_cfg:
        source_bases = resolved_cfg["source_bases"]
        config_source_bases = (
            [source_bases] if isinstance(source_bases, str) else source_bases
        )
    else:
        config_source_bases = DEFAULT_SOURCE_BASES

    # Merge with priority: CLI includes > config includes > config source_bases >
    # defaults
    # Deduplicate while preserving priority order
    merged_bases: list[str] = []
    seen_bases: set[str] = set()

    # Add CLI bases first (highest priority)
    # (already absolute from _extract_source_bases_from_includes)
    for base in cli_bases:
        if base not in seen_bases:
            seen_bases.add(base)
            merged_bases.append(base)

    # Add config bases (second priority)
    # (already absolute from _extract_source_bases_from_includes)
    for base in config_bases:
        if base not in seen_bases:
            seen_bases.add(base)
            merged_bases.append(base)

    # Add config source_bases (third priority) - resolve relative paths to absolute
    for base in config_source_bases:
        # Resolve relative paths to absolute
        base_path = (config_dir / base).resolve()
        base_abs = str(base_path)
        if base_abs not in seen_bases:
            seen_bases.add(base_abs)
            merged_bases.append(base_abs)

    # Add defaults last (lowest priority, but should already be in config_source_bases)
    # Resolve relative paths to absolute
    for base in DEFAULT_SOURCE_BASES:
        base_path = (config_dir / base).resolve()
        base_abs = str(base_path)
        if base_abs not in seen_bases:
            seen_bases.add(base_abs)
            merged_bases.append(base_abs)

    resolved_cfg["source_bases"] = merged_bases
    if cli_bases or config_bases:
        # Use display helpers for logging
        display_bases = shorten_paths_for_display(
            merged_bases, cwd=cwd, config_dir=config_dir
        )
        display_cli = shorten_paths_for_display(
            cli_bases, cwd=cwd, config_dir=config_dir
        )
        display_config = shorten_paths_for_display(
            config_bases, cwd=cwd, config_dir=config_dir
        )
        logger.debug(
            "[MODULE_BASES] Extracted bases from includes: CLI=%s, config=%s, "
            "merged=%s",
            display_cli,
            display_config,
            display_bases,
        )

    # ------------------------------
    # Include installed dependencies
    # ------------------------------
    if "include_installed_dependencies" not in resolved_cfg:
        resolved_cfg["include_installed_dependencies"] = False

    # ------------------------------
    # Main mode
    # ------------------------------
    valid_main_mode_values = literal_to_set(MainMode)
    if "main_mode" in resolved_cfg:
        main_mode_val = resolved_cfg["main_mode"]
        # Validate value
        if main_mode_val not in valid_main_mode_values:
            valid_str = ", ".join(repr(v) for v in sorted(valid_main_mode_values))
            msg = (
                f"Invalid main_mode value: {main_mode_val!r}. "
                f"Must be one of: {valid_str}"
            )
            raise ValueError(msg)
    else:
        resolved_cfg["main_mode"] = DEFAULT_MAIN_MODE

    # ------------------------------
    # Main name
    # ------------------------------
    if "main_name" not in resolved_cfg:
        resolved_cfg["main_name"] = DEFAULT_MAIN_NAME
    # Note: main_name can be None or a string, no validation needed here
    # (validation happens during parsing in later phases)

    # ------------------------------
    # Disable build timestamp
    # ------------------------------
    if getattr(args, "disable_build_timestamp", None):
        # CLI argument takes precedence
        resolved_cfg["disable_build_timestamp"] = True
    else:
        # Check ENV (SERGER_DISABLE_BUILD_TIMESTAMP or DISABLE_BUILD_TIMESTAMP)
        env_disable = os.getenv(
            f"{PROGRAM_ENV}_{DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP}"
        ) or os.getenv(DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP)
        if env_disable is not None:
            # Parse boolean from string (accept "true", "1", "yes", etc.)
            env_disable_lower = env_disable.lower()
            resolved_cfg["disable_build_timestamp"] = env_disable_lower in (
                "true",
                "1",
                "yes",
                "on",
            )
        elif "disable_build_timestamp" not in resolved_cfg:
            resolved_cfg["disable_build_timestamp"] = DEFAULT_DISABLE_BUILD_TIMESTAMP

    # ------------------------------
    # Max lines to check for serger build
    # ------------------------------
    resolved_cfg["build_tool_find_max_lines"] = build_cfg.get(
        "build_tool_find_max_lines", BUILD_TOOL_FIND_MAX_LINES
    )

    # ------------------------------
    # Post-processing
    # ------------------------------
    resolved_cfg["post_processing"] = resolve_post_processing(build_cfg, None)

    # ------------------------------
    # Pyproject.toml metadata extraction
    # ------------------------------
    # Extracts all metadata once, then:
    # - Always uses package name for resolution (if not already set)
    # - Uses other metadata only if use_pyproject_metadata is enabled
    # - Version is resolved here: user version -> pyproject version
    _apply_pyproject_metadata(
        resolved_cfg,
        build_cfg=build_cfg,
        root_cfg=None,
        config_dir=config_dir,
    )

    # ------------------------------
    # Version resolution
    # ------------------------------
    # Version is optional - resolved during pyproject metadata extraction above.
    # If not set, will fall back to timestamp in _extract_build_metadata()
    # No action needed here - value is already resolved if available

    # ------------------------------
    # License resolution
    # ------------------------------
    # License is mandatory in resolved config (always present with fallback).
    # Processing order: license field first, then license_files.
    # Resolution order: config license -> pyproject license (if enabled) -> fallback
    # Note: pyproject license is already applied in _apply_pyproject_metadata()
    # above (only when use_pyproject_metadata=True or pyproject_path set),
    # so we only need to handle config-provided license here.
    license_val = build_cfg.get("license")
    license_files_val = build_cfg.get("license_files")
    if license_val is not None or license_files_val is not None:
        # Resolve config-provided license (overrides pyproject if set)
        resolved_license = _resolve_license_field(
            license_val, license_files_val, config_dir
        )
        resolved_cfg["license"] = resolved_license
    elif "license" not in resolved_cfg:
        # No license in config or pyproject - use fallback
        resolved_cfg["license"] = DEFAULT_LICENSE_FALLBACK

    # ------------------------------
    # Stitching metadata fields (ensure all are present)
    # ------------------------------
    # Metadata fields are optional in resolved config.
    # Resolution order for most fields: user value -> pyproject value -> None (default)
    # Note: display_name has different priority (handled after package resolution)
    # Note: license is handled above (always present with fallback)
    # Fields are only set if they have a value; otherwise they remain None/absent
    for field in ("description", "authors", "repo"):
        if field not in resolved_cfg or resolved_cfg.get(field) is None:
            # Don't set to empty string - leave as None/absent
            pass

    # ------------------------------
    # Custom header and file docstring (pass through if present)
    # ------------------------------
    # These fields are truly optional and pass through as-is if provided
    if "custom_header" in build_cfg:
        resolved_cfg["custom_header"] = build_cfg["custom_header"]
    if "file_docstring" in build_cfg:
        resolved_cfg["file_docstring"] = build_cfg["file_docstring"]

    # ------------------------------
    # Package resolution (steps 3-7)
    # ------------------------------
    # Order of operations:
    # 1. ✅ User-provided in config (already set, logged above)
    # 2. ✅ pyproject.toml (just completed above)
    # 3. ✅ Infer from include paths
    # 4. ✅ Main function detection
    # 5. ✅ Most common package in includes (handled in step 3)
    # 6. ✅ Single module auto-detection
    # 7. ✅ First package in source_bases order
    package = resolved_cfg.get("package")
    source_bases_list = resolved_cfg.get("source_bases", [])
    config_includes = resolved_cfg.get("include", [])

    # Step 3: Infer from include paths (if package not set and includes exist)
    if not package and config_includes:
        inferred_packages = _infer_packages_from_includes(
            config_includes, source_bases_list, config_dir
        )
        if inferred_packages:
            # Use first package if single, or most common if multiple (already handled)
            resolved_cfg["package"] = inferred_packages[0]
            logger.info(
                "Package name '%s' inferred from include paths. "
                "Set 'package' in config to override.",
                inferred_packages[0],
            )

    # Step 4: Main function detection (if package not set and multiple modules exist)
    package = resolved_cfg.get("package")
    if not package and source_bases_list:
        # Check if multiple modules exist
        all_modules = _get_first_level_modules_from_bases(source_bases_list, config_dir)
        if len(all_modules) > 1:
            # Try to find main function in modules
            for module_name in all_modules:
                # Find module path
                module_path: Path | None = None
                for base_str in source_bases_list:
                    base_path = (config_dir / base_str).resolve()
                    module_dir = base_path / module_name
                    module_file = base_path / f"{module_name}.py"
                    if module_dir.exists() and module_dir.is_dir():
                        module_path = module_dir
                        break
                    if module_file.exists() and module_file.is_file():
                        module_path = module_file.parent
                        break
                if module_path and _has_main_function(module_path):
                    # Simple check for main function (def main( or if __name__ == "__main__")  # noqa: E501
                    resolved_cfg["package"] = module_name
                    logger.info(
                        "Package name '%s' detected via main() function. "
                        "Set 'package' in config to override.",
                        module_name,
                    )
                    break

    # Step 6: Single module auto-detection (if package not set)
    package = resolved_cfg.get("package")
    if not package and source_bases_list:
        # Find the first module_base with exactly 1 module
        detected_module: str | None = None
        detected_base: str | None = None
        for base_str in source_bases_list:
            base_modules = _get_first_level_modules_from_base(base_str, config_dir)
            if len(base_modules) == 1:
                # Found a base with exactly 1 module
                detected_module = base_modules[0]
                detected_base = base_str
                break

        if detected_module and detected_base:
            # Set package to the detected module
            resolved_cfg["package"] = detected_module
            logger.info(
                "Package name '%s' auto-detected from single module in "
                "module_base '%s'. Set 'package' in config to override.",
                detected_module,
                detected_base,
            )

    # Step 7: First package in source_bases order (if package not set)
    package = resolved_cfg.get("package")
    if not package and source_bases_list:
        all_modules = _get_first_level_modules_from_bases(source_bases_list, config_dir)
        if len(all_modules) > 0:
            # Use first module found (preserves source_bases order)
            resolved_cfg["package"] = all_modules[0]
            logger.info(
                "Package name '%s' selected from source_bases (first found). "
                "Set 'package' in config to override.",
                all_modules[0],
            )

    # ------------------------------
    # Auto-set includes from package and source_bases
    # ------------------------------
    # If no includes were provided (configless or config has no includes),
    # automatically set includes based on package and source_bases.
    # This must run AFTER pyproject metadata extraction so package from
    # pyproject.toml is available.
    has_cli_includes = bool(
        getattr(args, "include", None) or getattr(args, "add_include", None)
    )
    # Check if config has includes (empty list means no includes)
    config_includes = resolved_cfg.get("include", [])
    has_config_includes = len(config_includes) > 0
    # Check if includes were explicitly set in original config
    # (even if empty, explicit setting means don't auto-set)
    has_explicit_config_includes = "include" in build_cfg
    package = resolved_cfg.get("package")
    source_bases_list = resolved_cfg.get("source_bases", [])

    # Auto-set includes based on package (if package exists and no includes provided)
    if (
        package
        and not has_cli_includes
        and not has_config_includes
        and not has_explicit_config_includes
        and source_bases_list
    ):
        # Package exists and is found in source_bases
        # Get first-level modules from source_bases for this check
        first_level_modules = _get_first_level_modules_from_bases(
            source_bases_list, config_dir
        )
        if package in first_level_modules:
            logger.debug(
                "Auto-setting includes to package '%s' found in source_bases: %s",
                package,
                source_bases_list,
            )

            # Find which module_base contains the package
            # Can be either a directory (package) or a .py file (module)
            package_path: str | None = None
            for base_str in source_bases_list:
                # base_str is already an absolute path
                base_path = Path(base_str).resolve()
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
                # Set includes to the package found in source_bases
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
    # Display name resolution (after package is fully resolved)
    # ------------------------------
    # display_name priority: user -> package -> None (default)
    # Package is now fully resolved, so we can use it as fallback
    if "display_name" not in resolved_cfg or resolved_cfg.get("display_name") is None:
        package = resolved_cfg.get("package")
        if package:
            resolved_cfg["display_name"] = package
        # If no package, leave display_name as None/absent

    # ------------------------------
    # Attach provenance
    # ------------------------------
    resolved_cfg["__meta__"] = meta
    return cast_hint(RootConfigResolved, resolved_cfg)


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
    logger = getAppLogger()
    root_cfg = cast_hint(RootConfig, dict(root_input))

    logger.trace("[resolve_config] Resolving flat config")

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
    root_log = root_cfg.get("log_level")
    log_level = logger.determineLogLevel(args=args, root_log_level=root_log)

    # --- sync runtime ---
    setRootLevel(log_level)

    # Set log_level in config before resolving (resolve_build_config expects it)
    root_cfg["log_level"] = log_level

    # ------------------------------
    # Resolve single flat config
    # ------------------------------
    resolved = resolve_build_config(root_cfg, args, config_dir, cwd)

    # Add watch_interval to resolved config
    resolved["watch_interval"] = watch_interval

    # Set runtime flags with defaults (will be overridden in _execute_build if set)
    resolved["dry_run"] = False
    resolved["validate"] = False

    return resolved
