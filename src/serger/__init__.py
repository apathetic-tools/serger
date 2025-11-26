# src/serger/__init__.py

"""Serger — Stitch your module into a single file.

Full developer API
==================
This package re-exports all non-private symbols from its submodules,
making it suitable for programmatic use, custom integrations, or plugins.
Anything prefixed with "_" is considered internal and may change.

Highlights:
    - main()              → CLI entrypoint
    - run_build()         → Execute a build configuration
    - resolve_config()    → Merge CLI args with config files
    - get_metadata()      → Retrieve version / commit info
"""

from .actions import get_metadata, watch_for_changes
from .build import run_build
from .cli import main
from .config import (
    IncludeResolved,
    MetaBuildConfigResolved,
    OriginType,
    PathResolved,
    RootConfig,
    RootConfigResolved,
    find_config,
    load_and_validate_config,
    load_config,
    parse_config,
    resolve_build_config,
    resolve_config,
    validate_config,
)
from .constants import (
    DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP,
    DEFAULT_ENV_LOG_LEVEL,
    DEFAULT_ENV_RESPECT_GITIGNORE,
    DEFAULT_ENV_WATCH_INTERVAL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_OUT_DIR,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_WATCH_INTERVAL,
)
from .logs import getAppLogger
from .meta import (
    PROGRAM_CONFIG,
    PROGRAM_DISPLAY,
    PROGRAM_ENV,
    PROGRAM_PACKAGE,
    PROGRAM_SCRIPT,
    Metadata,
)
from .selftest import run_selftest
from .utils import (
    is_excluded,
    make_includeresolved,
    make_pathresolved,
)


__all__ = [  # noqa: RUF022
    # actions
    "get_metadata",
    "watch_for_changes",
    # build
    "run_build",
    # cli
    "main",
    # config
    "find_config",
    "IncludeResolved",
    "load_and_validate_config",
    "load_config",
    "MetaBuildConfigResolved",
    "OriginType",
    "parse_config",
    "PathResolved",
    "resolve_build_config",
    "resolve_config",
    "RootConfig",
    "RootConfigResolved",
    "validate_config",
    # constants
    "DEFAULT_ENV_DISABLE_BUILD_TIMESTAMP",
    "DEFAULT_ENV_LOG_LEVEL",
    "DEFAULT_ENV_RESPECT_GITIGNORE",
    "DEFAULT_ENV_WATCH_INTERVAL",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_OUT_DIR",
    "DEFAULT_RESPECT_GITIGNORE",
    "DEFAULT_STRICT_CONFIG",
    "DEFAULT_WATCH_INTERVAL",
    # logs
    "getAppLogger",
    # meta
    "Metadata",
    "PROGRAM_CONFIG",
    "PROGRAM_DISPLAY",
    "PROGRAM_ENV",
    "PROGRAM_PACKAGE",
    "PROGRAM_SCRIPT",
    # selftest
    "run_selftest",
    # utils
    "is_excluded",
    "make_includeresolved",
    "make_pathresolved",
]
