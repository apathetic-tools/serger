# tests/utils/buildconfig.py
"""Shared test helpers for constructing fake RootConfigResolved and related types."""

import json
from pathlib import Path
from typing import Any, cast

import serger.config.config_types as mod_types
import serger.constants as mod_constants


# ---------------------------------------------------------------------------
# Factories for resolved and unresolved configs
# ---------------------------------------------------------------------------


def make_meta(root: Path) -> mod_types.MetaBuildConfigResolved:
    """Minimal fake meta object for resolved configs."""
    return {"cli_root": root, "config_root": root}


def make_resolved(path: Path | str, root: Path | str) -> mod_types.PathResolved:
    """Return a fake PathResolved-style dict."""
    raw_path = path if isinstance(path, str) else str(path)
    return cast(
        "mod_types.PathResolved",
        {
            "path": raw_path,
            "root": Path(root),
            "origin": "test",
        },
    )


def make_include_resolved(
    path: Path | str,
    root: Path | str,
    dest: Path | str | None = None,
) -> mod_types.IncludeResolved:
    """Return a fake IncludeResolved-style dict."""
    # Preserve raw string form to retain trailing slashes
    raw_path = path if isinstance(path, str) else str(path)
    d: dict[str, Path | str] = {
        "path": raw_path,
        "root": Path(root),
        "origin": "test",
    }
    if dest:
        d["dest"] = Path(dest)
    return cast("mod_types.IncludeResolved", d)


def make_build_cfg(  # noqa: PLR0913
    tmp_path: Path | None = None,
    include: list[mod_types.IncludeResolved] | None = None,
    exclude: list[mod_types.PathResolved] | None = None,
    *,
    respect_gitignore: bool = True,
    log_level: str = "info",
    dry_run: bool = False,
    validate_config: bool = False,
    out: mod_types.PathResolved | None = None,
    stitch_mode: mod_types.StitchMode = "raw",
    module_mode: mod_types.ModuleMode = "multi",
    shim: mod_types.ShimSetting = "all",
    internal_imports: mod_types.InternalImportMode = "force_strip",
    external_imports: mod_types.ExternalImportMode = "top",
    comments_mode: mod_types.CommentsMode = "keep",
    docstring_mode: mod_types.DocstringMode = "keep",
    post_processing: mod_types.PostProcessingConfigResolved | None = None,
    package: str | None = None,
    order: list[str] | None = None,
    watch_interval: float = 1.0,
    module_actions: list[mod_types.ModuleActionFull] | None = None,
    source_bases: list[str] | None = None,
    installed_bases: list[str] | None = None,
    auto_discover_installed_packages: bool = True,
    include_installed_dependencies: bool = False,
    main_mode: mod_types.MainMode = "auto",
    main_name: str | None = None,
    version: str | None = None,
    license_text: str = mod_constants.DEFAULT_LICENSE_FALLBACK,
    disable_build_timestamp: bool = False,
    build_tool_find_max_lines: int | None = None,
    display_name: str | None = None,
    description: str | None = None,
    authors: str | None = None,
    repo: str | None = None,
    custom_header: str | None = None,
    file_docstring: str | None = None,
) -> mod_types.RootConfigResolved:
    """Return a fake, fully-populated RootConfigResolved."""
    if tmp_path is None:
        tmp_path = Path.cwd()
    if include is None:
        include = []
    cfg: dict[str, object] = {
        "include": include,
        "exclude": exclude or [],
        "out": out
        if out is not None
        else make_resolved(tmp_path / "dist" / "script.py", tmp_path),
        "__meta__": make_meta(tmp_path),
        "respect_gitignore": respect_gitignore,
        "log_level": log_level,
        "dry_run": dry_run,
        "validate_config": validate_config,
        "strict_config": False,
        "watch_interval": watch_interval,
        "stitch_mode": stitch_mode,
        "module_mode": module_mode,
        "shim": shim,
        "internal_imports": internal_imports,
        "external_imports": external_imports,
        "comments_mode": comments_mode,
        "docstring_mode": docstring_mode,
        "post_processing": post_processing
        if post_processing is not None
        else make_post_processing_config_resolved(),
        "module_actions": module_actions if module_actions is not None else [],
        "source_bases": (
            source_bases if source_bases is not None else ["src", "lib", "packages"]
        ),
        "installed_bases": installed_bases if installed_bases is not None else [],
        "auto_discover_installed_packages": auto_discover_installed_packages,
        "include_installed_dependencies": include_installed_dependencies,
        "main_mode": main_mode,
        "main_name": main_name,
        "license": license_text,
        "disable_build_timestamp": disable_build_timestamp,
        "build_tool_find_max_lines": (
            build_tool_find_max_lines
            if build_tool_find_max_lines is not None
            else mod_constants.BUILD_TOOL_FIND_MAX_LINES
        ),
    }
    if package is not None:
        cfg["package"] = package
    if order is not None:
        cfg["order"] = order
    if version is not None:
        cfg["version"] = version
    if display_name is not None:
        cfg["display_name"] = display_name
    if description is not None:
        cfg["description"] = description
    if authors is not None:
        cfg["authors"] = authors
    if repo is not None:
        cfg["repo"] = repo
    if custom_header is not None:
        cfg["custom_header"] = custom_header
    if file_docstring is not None:
        cfg["file_docstring"] = file_docstring
    return cast("mod_types.RootConfigResolved", cfg)


def make_build_input(
    include: list[str | dict[str, str]] | None = None,
    exclude: list[str] | None = None,
    out: str | None = None,
    **extra: object,
) -> mod_types.RootConfig:
    """Convenient shorthand for constructing raw (pre-resolve) build inputs."""
    cfg: dict[str, object] = {}
    if include is not None:
        cfg["include"] = include
    if exclude is not None:
        cfg["exclude"] = exclude
    if out is not None:
        cfg["out"] = out
    cfg.update(extra)
    return cast("mod_types.RootConfig", cfg)


# ---------------------------------------------------------------------------
# Factories for module actions
# ---------------------------------------------------------------------------


def make_module_action_full(
    source: str,
    *,
    source_path: str | None = None,
    dest: str | None = None,
    action: mod_types.ModuleActionType = "move",
    mode: mod_types.ModuleActionMode = "preserve",
    scope: mod_types.ModuleActionScope | None = None,
    affects: mod_types.ModuleActionAffects = "shims",
    cleanup: mod_types.ModuleActionCleanup = "auto",
) -> mod_types.ModuleActionFull:
    """Create a ModuleActionFull with required fields and defaults.

    Args:
        source: Source module name (required)
        source_path: Optional filesystem path
        dest: Destination module name (required for move/copy)
        action: Action type (defaults to "move")
        mode: Action mode (defaults to "preserve")
        scope: Action scope (defaults to None, will be set by resolver)
        affects: What the action affects (defaults to "shims")
        cleanup: Cleanup behavior (defaults to "auto")

    Returns:
        ModuleActionFull with all fields populated with defaults where applicable
    """
    result: dict[str, object] = {
        "source": source,
        "action": action,
        "mode": mode,
        "affects": affects,
        "cleanup": cleanup,
    }
    if source_path is not None:
        result["source_path"] = source_path
    if dest is not None:
        result["dest"] = dest
    if scope is not None:
        result["scope"] = scope
    return cast("mod_types.ModuleActionFull", result)


# ---------------------------------------------------------------------------
# Factories for include configs
# ---------------------------------------------------------------------------


def make_include_config(
    path: str,
    *,
    dest: str | None = None,
) -> mod_types.IncludeConfig:
    """Create an IncludeConfig with required fields.

    Args:
        path: Include path pattern (required)
        dest: Optional destination override

    Returns:
        IncludeConfig with all specified fields
    """
    result: dict[str, object] = {"path": path}
    if dest is not None:
        result["dest"] = dest
    return cast("mod_types.IncludeConfig", result)


# ---------------------------------------------------------------------------
# Factories for post-processing configs (unresolved)
# ---------------------------------------------------------------------------


def make_tool_config(
    *,
    command: str | None = None,
    args: list[str] | None = None,
    path: str | None = None,
    options: list[str] | None = None,
) -> mod_types.ToolConfig:
    """Create a ToolConfig with optional fields.

    Args:
        command: Executable name (optional, defaults to key if missing)
        args: Command arguments (optional, replaces defaults)
        path: Custom executable path (optional)
        options: Additional CLI arguments (optional, appends to args)

    Returns:
        ToolConfig with all specified fields
    """
    result: dict[str, object] = {}
    if command is not None:
        result["command"] = command
    if args is not None:
        result["args"] = args
    if path is not None:
        result["path"] = path
    if options is not None:
        result["options"] = options
    return cast("mod_types.ToolConfig", result)


def make_post_category_config(
    *,
    enabled: bool | None = None,
    priority: list[str] | None = None,
    tools: dict[str, mod_types.ToolConfig] | None = None,
) -> mod_types.PostCategoryConfig:
    """Create a PostCategoryConfig with optional fields.

    Args:
        enabled: Whether category is enabled (defaults to True if not specified)
        priority: Tool names in priority order (optional)
        tools: Dict of tool configs (optional)

    Returns:
        PostCategoryConfig with all specified fields
    """
    result: dict[str, object] = {}
    if enabled is not None:
        result["enabled"] = enabled
    if priority is not None:
        result["priority"] = priority
    if tools is not None:
        result["tools"] = tools
    return cast("mod_types.PostCategoryConfig", result)


def make_post_processing_config(
    *,
    enabled: bool | None = None,
    category_order: list[str] | None = None,
    categories: dict[str, mod_types.PostCategoryConfig] | None = None,
) -> mod_types.PostProcessingConfig:
    """Create a PostProcessingConfig with optional fields.

    Args:
        enabled: Master switch (defaults to True if not specified)
        category_order: Order to run categories (optional)
        categories: Category definitions (optional)

    Returns:
        PostProcessingConfig with all specified fields
    """
    result: dict[str, object] = {}
    if enabled is not None:
        result["enabled"] = enabled
    if category_order is not None:
        result["category_order"] = category_order
    if categories is not None:
        result["categories"] = categories
    return cast("mod_types.PostProcessingConfig", result)


# ---------------------------------------------------------------------------
# Factories for post-processing configs (resolved)
# ---------------------------------------------------------------------------


def make_tool_config_resolved(
    args: list[str],
    *,
    command: str | None = None,
    path: str | None = None,
    options: list[str] | None = None,
) -> mod_types.ToolConfigResolved:
    """Create a ToolConfigResolved with required fields.

    Args:
        args: Command arguments (required)
        command: Executable name (defaults to tool_label if not provided)
        path: Custom executable path (defaults to None)
        options: Additional CLI arguments (defaults to empty list)

    Returns:
        ToolConfigResolved with all fields populated
    """
    return {
        "command": command or "tool",  # Default placeholder
        "args": args,
        "path": path,
        "options": options or [],
    }


def make_post_category_config_resolved(
    *,
    enabled: bool = True,
    priority: list[str] | None = None,
    tools: dict[str, mod_types.ToolConfigResolved] | None = None,
) -> mod_types.PostCategoryConfigResolved:
    """Create a PostCategoryConfigResolved with required fields.

    Args:
        enabled: Whether category is enabled (defaults to True)
        priority: Tool names in priority order (defaults to empty list)
        tools: Dict of tool configs (defaults to empty dict)

    Returns:
        PostCategoryConfigResolved with all fields populated
    """
    return {
        "enabled": enabled,
        "priority": priority or [],
        "tools": tools or {},
    }


def make_post_processing_config_resolved(
    *,
    enabled: bool = True,
    category_order: list[str] | None = None,
    categories: dict[str, mod_types.PostCategoryConfigResolved] | None = None,
) -> mod_types.PostProcessingConfigResolved:
    """Create a PostProcessingConfigResolved with required fields.

    Args:
        enabled: Master switch (defaults to True)
        category_order: Order to run categories (defaults to empty list)
        categories: Category definitions (defaults to empty dict)

    Returns:
        PostProcessingConfigResolved with all fields populated
    """
    return {
        "enabled": enabled,
        "category_order": category_order or [],
        "categories": categories or {},
    }


# ---------------------------------------------------------------------------
# Factory for writing config files
# ---------------------------------------------------------------------------


def make_config_content(
    *,
    package: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    out: str | None = None,
    builds: mod_types.RootConfig | None = None,
    fmt: str = "json",
    **root_options: Any,
) -> str:
    """Generate config file content (JSON, JSONC, or Python) with flat config format.

    Args:
        package: Package name for stitching (required if builds not provided)
        include: Include patterns (defaults to [f"{package}/**/*.py"]
            if package provided)
        exclude: Exclude patterns (defaults to empty list)
        out: Output path (defaults to "dist/{package}.py"
            if package provided)
        builds: Single build config dict (alternative to individual params -
            if provided, other params are ignored)
        fmt: Output format - "json", "jsonc", or "py" (default: "json")
        **root_options: Additional root-level config options (e.g., log_level)

    Returns:
        String content of the config file

    Examples:
        >>> # Simple usage with package name
        >>> content = make_config_content(package="mypkg")
        >>> config_path.write_text(content, encoding="utf-8")
        >>> # Override defaults
        >>> content = make_config_content(
        ...     package="mypkg",
        ...     out="custom/dist.py",
        ...     include=["mypkg/**/*.py", "other/**/*.py"],
        ... )
        >>> # Using build dict
        >>> content = make_config_content(
        ...     builds={"package": "pkg1", "out": "dist1"},
        ...     fmt="py",
        ...     log_level="debug",
        ... )
    """
    # If builds provided, use it directly (single build only)
    if builds is not None:
        build_cfg: dict[str, Any] = dict(builds)
    else:
        # Build from individual parameters
        if package is None:
            xmsg = "Either 'package' or 'builds' must be provided"
            raise ValueError(xmsg)

        build_cfg = {"package": package}

        # Set defaults based on package name
        if include is None:
            include = [f"{package}/**/*.py"]
        if include:
            build_cfg["include"] = include

        if exclude is not None:
            build_cfg["exclude"] = exclude

        if out is None:
            out = f"dist/{package}.py"
        if out:
            build_cfg["out"] = out

    # Construct flat config (merge build_cfg with root_options)
    root_cfg: dict[str, Any] = dict(build_cfg)
    root_cfg.update(root_options)

    # Generate content based on format
    if fmt == "py":
        # Python config file - write as Python code
        config_repr = repr(root_cfg)
        content = f"config = {config_repr}\n"
        return content
    if fmt == "jsonc":
        # JSONC (JSON with comments) - just write as JSON for simplicity
        # Tests can add comments manually if needed
        return json.dumps(root_cfg, indent=2)
    # Default to JSON
    return json.dumps(root_cfg, indent=2)


def write_config_file(
    config_path: Path,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Write a config file (JSON, JSONC, or Python) with the given builds.

    Convenience wrapper around make_config_content that writes to a file.
    All arguments except config_path are passed through to make_config_content.

    Args:
        config_path: Path where the config file should be written
        *args: Positional arguments passed to make_config_content
        **kwargs: Keyword arguments passed to make_config_content
            (package, include, exclude, out, builds, fmt, etc.)

    Examples:
        >>> # Simple usage with package name
        >>> write_config_file(tmp_path / ".serger.json", package="mypkg")
        >>> # Override defaults
        >>> write_config_file(
        ...     tmp_path / ".serger.json",
        ...     package="mypkg",
        ...     out="custom/dist.py",
        ... )
    """
    # Determine format from file extension and override fmt in kwargs
    ext = config_path.suffix.lower()
    if ext == ".py":
        fmt_str = "py"
    elif ext == ".jsonc":
        fmt_str = "jsonc"
    else:
        fmt_str = "json"

    # Pass all args/kwargs to make_config_content, overriding fmt with detected format
    content = make_config_content(*args, fmt=fmt_str, **kwargs)
    config_path.write_text(content, encoding="utf-8")
