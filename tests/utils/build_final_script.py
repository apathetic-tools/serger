# tests/utils/build_final_script.py
"""Factory functions for creating _build_final_script test arguments."""

from collections import OrderedDict
from pathlib import Path
from typing import Any

import serger.config as mod_config
import serger.main_config as mod_main_config
import serger.stitch as mod_stitch
from tests.utils.buildconfig import make_build_cfg, make_include_resolved


def make_build_final_script_args(  # noqa: PLR0913
    *,
    package_name: str = "testpkg",
    all_imports: OrderedDict[str, None] | None = None,
    parts: list[str] | None = None,
    order_names: list[str] | None = None,
    all_function_names: set[str] | None = None,
    detected_packages: set[str] | None = None,
    module_mode: str = "multi",
    module_actions: list[mod_config.ModuleActionFull] | None = None,
    shim: mod_config.ShimSetting = "all",
    license_header: str = "",
    version: str = "1.0.0",
    commit: str = "abc123",
    build_date: str = "2025-01-01",
    display_name: str = "",
    description: str = "",
    authors: str = "",
    repo: str = "",
    config: mod_config.RootConfigResolved | None = None,
    main_function_result: tuple[str, Path, str] | None = None,
    selected_main_block: mod_main_config.MainBlock | None = None,
    module_sources: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create arguments for _build_final_script with sensible defaults.

    Args:
        package_name: Root package name
        all_imports: Collected external imports (defaults to sys/types imports)
        parts: Module code sections (defaults to single main module)
        order_names: List of module names (defaults to ["main"])
        all_function_names: Set of all function names (defaults to empty set)
        detected_packages: Pre-detected package names (defaults to {package_name})
        module_mode: How to generate import shims (defaults to "multi")
        module_actions: List of module actions (defaults to empty list)
        shim: Shim setting (defaults to "all")
        license_header: License header text
        version: Version string
        commit: Commit hash
        build_date: Build timestamp
        display_name: Optional display name for header
        description: Optional description for header
        authors: Optional authors for header
        repo: Optional repository URL for header
        config: Resolved configuration with main_mode and main_name
        main_function_result: Result from find_main_function() if found
        selected_main_block: Selected __main__ block to use (if any)
        module_sources: Mapping of module name to source code

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

    if module_actions is None:
        module_actions = []

    # Create default config if not provided
    if config is None:
        tmp_path = Path("/tmp")  # noqa: S108
        config = make_build_cfg(
            tmp_path,
            include=[make_include_resolved("src", tmp_path)],
            package=package_name,
            main_mode="auto",
            main_name=None,
        )

    result: dict[str, Any] = {
        "package_name": package_name,
        "all_imports": all_imports,
        "parts": parts,
        "order_names": order_names,
        "_all_function_names": all_function_names,
        "detected_packages": detected_packages,
        "module_mode": module_mode,
        "module_actions": module_actions,
        "shim": shim,
        "license_header": license_header,
        "version": version,
        "commit": commit,
        "build_date": build_date,
        "display_name": display_name,
        "description": description,
        "authors": authors,
        "repo": repo,
        "config": config,
        "selected_main_block": selected_main_block,
        "main_function_result": main_function_result,
        "module_sources": module_sources,
    }

    return result


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
