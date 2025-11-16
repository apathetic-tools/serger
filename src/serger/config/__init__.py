# src/serger/config/__init__.py

"""Configuration handling for serger.

This module provides configuration loading, parsing, validation, and resolution.
"""

from .config_loader import (
    can_run_configless,
    find_config,
    load_and_validate_config,
    load_config,
    parse_config,
)
from .config_resolve import (
    PyprojectMetadata,
    extract_pyproject_metadata,
    resolve_build_config,
    resolve_config,
    resolve_post_processing,
)
from .config_types import (
    BuildConfig,
    BuildConfigResolved,
    CommentsMode,
    DocstringMode,
    DocstringModeLocation,
    DocstringModeSimple,
    ExternalImportMode,
    IncludeConfig,
    IncludeResolved,
    InternalImportMode,
    MetaBuildConfigResolved,
    ModuleActionFull,
    ModuleMode,
    OriginType,
    PathResolved,
    PostCategoryConfig,
    PostCategoryConfigResolved,
    PostProcessingConfig,
    PostProcessingConfigResolved,
    RootConfig,
    RootConfigResolved,
    ShimSetting,
    StitchMode,
    ToolConfig,
    ToolConfigResolved,
)
from .config_validate import validate_config


__all__ = [  # noqa: RUF022
    # config_loader
    "can_run_configless",
    "find_config",
    "load_and_validate_config",
    "load_config",
    "parse_config",
    # config_resolve
    "PyprojectMetadata",
    "extract_pyproject_metadata",
    "resolve_build_config",
    "resolve_config",
    "resolve_post_processing",
    # config_types
    "BuildConfig",
    "BuildConfigResolved",
    "CommentsMode",
    "DocstringMode",
    "DocstringModeLocation",
    "DocstringModeSimple",
    "ExternalImportMode",
    "IncludeConfig",
    "IncludeResolved",
    "InternalImportMode",
    "MetaBuildConfigResolved",
    "ModuleActionFull",
    "ModuleMode",
    "OriginType",
    "PathResolved",
    "PostCategoryConfig",
    "PostCategoryConfigResolved",
    "PostProcessingConfig",
    "PostProcessingConfigResolved",
    "RootConfig",
    "RootConfigResolved",
    "ShimSetting",
    "StitchMode",
    "ToolConfig",
    "ToolConfigResolved",
    # config_validate
    "validate_config",
]
