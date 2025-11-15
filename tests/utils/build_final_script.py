# tests/utils/build_final_script.py
"""Factory functions for creating _build_final_script test arguments."""

from collections import OrderedDict
from typing import Any

import serger.stitch as mod_stitch


def make_build_final_script_args(  # noqa: PLR0913
    *,
    package_name: str = "testpkg",
    all_imports: OrderedDict[str, None] | None = None,
    parts: list[str] | None = None,
    order_names: list[str] | None = None,
    all_function_names: set[str] | None = None,
    detected_packages: set[str] | None = None,
    shim_mode: str = "multi",
    license_header: str = "",
    version: str = "1.0.0",
    commit: str = "abc123",
    build_date: str = "2025-01-01",
    display_name: str = "",
    description: str = "",
    repo: str = "",
) -> dict[str, Any]:
    """Create arguments for _build_final_script with sensible defaults.

    Args:
        package_name: Root package name
        all_imports: Collected external imports (defaults to sys/types imports)
        parts: Module code sections (defaults to single main module)
        order_names: List of module names (defaults to ["main"])
        all_function_names: Set of all function names (defaults to empty set)
        detected_packages: Pre-detected package names (defaults to {package_name})
        shim_mode: How to generate import shims (defaults to "multi")
        license_header: License header text
        version: Version string
        commit: Commit hash
        build_date: Build timestamp
        display_name: Optional display name for header
        description: Optional description for header
        repo: Optional repository URL for header

    Returns:
        Dictionary of keyword arguments for _build_final_script
    """
    if all_imports is None:
        all_imports = OrderedDict()
        all_imports["import sys\n"] = None
        all_imports["import types\n"] = None

    if parts is None:
        parts = ["# === main.py ===\nMAIN = 1\n"]

    if order_names is None:
        order_names = ["main"]

    if all_function_names is None:
        all_function_names = set()

    if detected_packages is None:
        detected_packages = {package_name}

    return {
        "package_name": package_name,
        "all_imports": all_imports,
        "parts": parts,
        "order_names": order_names,
        "all_function_names": all_function_names,
        "detected_packages": detected_packages,
        "shim_mode": shim_mode,
        "license_header": license_header,
        "version": version,
        "commit": commit,
        "build_date": build_date,
        "display_name": display_name,
        "description": description,
        "repo": repo,
    }


def call_build_final_script(**kwargs: Any) -> tuple[str, list[str]]:
    """Call _build_final_script with arguments from make_build_final_script_args.

    This is a convenience wrapper that combines make_build_final_script_args
    with the actual function call.

    Args:
        **kwargs: Arguments to pass to make_build_final_script_args

    Returns:
        Tuple of (script_text, detected_packages) from _build_final_script
    """
    args = make_build_final_script_args(**kwargs)
    return mod_stitch._build_final_script(**args)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
