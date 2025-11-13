# tests/utils/buildconfig.py
"""Shared test helpers for constructing fake BuildConfigResolved and related types."""

import json
from pathlib import Path
from typing import Any, cast

import serger.config.config_types as mod_types


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


def make_build_cfg(
    tmp_path: Path,
    include: list[mod_types.IncludeResolved],
    exclude: list[mod_types.PathResolved] | None = None,
    *,
    respect_gitignore: bool = True,
    log_level: str = "info",
    dry_run: bool = False,
    out: mod_types.PathResolved | None = None,
) -> mod_types.BuildConfigResolved:
    """Return a fake, fully-populated BuildConfigResolved."""
    return {
        "include": include,
        "exclude": exclude or [],
        "out": out
        if out is not None
        else make_resolved(tmp_path / "dist" / "script.py", tmp_path),
        "__meta__": make_meta(tmp_path),
        "respect_gitignore": respect_gitignore,
        "log_level": log_level,
        "dry_run": dry_run,
        "strict_config": False,
    }


def make_build_input(
    include: list[str | dict[str, str]] | None = None,
    exclude: list[str] | None = None,
    out: str | None = None,
    **extra: object,
) -> mod_types.BuildConfig:
    """Convenient shorthand for constructing raw (pre-resolve) build inputs."""
    cfg: dict[str, object] = {}
    if include is not None:
        cfg["include"] = include
    if exclude is not None:
        cfg["exclude"] = exclude
    if out is not None:
        cfg["out"] = out
    cfg.update(extra)
    return cast("mod_types.BuildConfig", cfg)


# ---------------------------------------------------------------------------
# Factories for post-processing configs
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


def make_config_content(  # noqa: PLR0912
    *,
    package: str | None = None,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    out: str | None = None,
    builds: list[mod_types.BuildConfig] | mod_types.BuildConfig | None = None,
    fmt: str = "json",
    **root_options: Any,
) -> str:
    """Generate config file content (JSON, JSONC, or Python) with the given builds.

    Args:
        package: Package name for stitching (required if builds not provided)
        include: Include patterns (defaults to [f"{package}/**/*.py"]
            if package provided)
        exclude: Exclude patterns (defaults to empty list)
        out: Output path (defaults to "dist/{package}.py"
            if package provided)
        builds: Single build config dict or list of build config dicts (alternative to
            individual params - if provided, other params are ignored)
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
        >>> # Multiple builds
        >>> content = make_config_content(
        ...     builds=[
        ...         {"package": "pkg1", "out": "dist1"},
        ...         {"package": "pkg2", "out": "dist2"},
        ...     ],
        ...     fmt="py",
        ...     log_level="debug",
        ... )
    """
    # If builds provided, use them directly
    if builds is not None:
        builds_list = builds if isinstance(builds, list) else [builds]
    else:
        # Build from individual parameters
        if package is None:
            xmsg = "Either 'package' or 'builds' must be provided"
            raise ValueError(xmsg)

        build_cfg: dict[str, Any] = {"package": package}

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

        builds_list = [cast("mod_types.BuildConfig", build_cfg)]

    # Construct root config
    root_cfg: dict[str, Any] = {"builds": builds_list}
    root_cfg.update(root_options)

    # Generate content based on format
    if fmt == "py":
        # Python config file - write as Python code
        builds_repr = repr(builds_list)
        content = f"builds = {builds_repr}\n"
        # Add root options if any
        if root_options:
            for key, value in root_options.items():
                if key != "builds":
                    value_repr = repr(value)
                    content += f"{key} = {value_repr}\n"
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
