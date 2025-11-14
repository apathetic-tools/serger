---
layout: default
title: API Documentation
permalink: /api
---

# API Documentation

Serger provides a programmatic API for custom integrations, plugins, and automation.

## Quick Reference

```python
from serger import (
    main,              # CLI entrypoint
    run_build,         # Execute a build configuration
    resolve_config,    # Merge CLI args with config files
    get_metadata,      # Retrieve version / commit info
)
```

## Core Functions

### `main(argv: list[str] | None = None) -> int`

CLI entrypoint function. Can be called programmatically or used as a script entry point.

**Parameters:**
- `argv` (optional): Command-line arguments. If `None`, uses `sys.argv[1:]`.

**Returns:**
- Exit code (0 for success, non-zero for errors).

**Example:**
```python
from serger import main

# Run with custom arguments
exit_code = main(["--include", "src/**/*.py", "--out", "dist/app.py"])

# Run with sys.argv (default)
exit_code = main()
```

### `run_build(build_cfg: BuildConfigResolved, root_cfg: RootConfigResolved) -> None`

Execute a single build configuration.

**Parameters:**
- `build_cfg`: Resolved build configuration
- `root_cfg`: Resolved root configuration

**Example:**
```python
from serger import run_build, resolve_config
from pathlib import Path

# Resolve config
config_path = Path(".serger.jsonc")
root_cfg, resolved_builds = resolve_config(config_path)

# Run first build
if resolved_builds:
    run_build(resolved_builds[0], root_cfg)
```

### `resolve_config(...) -> tuple[RootConfigResolved, list[BuildConfigResolved]]`

Merge CLI arguments with config files and resolve all paths.

**Parameters:**
- Various parameters for config path, CLI args, etc.

**Returns:**
- Tuple of `(resolved_root_config, list_of_resolved_builds)`

**Example:**
```python
from serger import resolve_config
from pathlib import Path
import argparse

args = argparse.Namespace()
config_path = Path(".serger.jsonc")
root_cfg, builds = resolve_config(args, config_path)
```

### `get_metadata() -> Metadata`

Retrieve version and commit information.

**Returns:**
- `Metadata` object with `version` and `commit` attributes.

**Example:**
```python
from serger import get_metadata

meta = get_metadata()
print(f"Serger {meta.version} ({meta.commit})")
```

## Configuration Types

### `RootConfig`

Root configuration dictionary type.

```python
from serger import RootConfig

config: RootConfig = {
    "builds": [...],
    "log_level": "info",
    "strict_config": True,
    "respect_gitignore": True,
}
```

### `BuildConfig`

Individual build configuration dictionary type.

```python
from serger import BuildConfig

build: BuildConfig = {
    "package": "mypkg",
    "include": ["src/**/*.py"],
    "exclude": ["**/__init__.py"],
    "out": "dist/mypkg.py",
}
```

### `BuildConfigResolved`

Resolved build configuration with all paths expanded.

### `RootConfigResolved`

Resolved root configuration with all paths expanded.

## Configuration Loading

### `find_config(args: argparse.Namespace, cwd: Path) -> Path | None`

Locate a configuration file.

**Parameters:**
- `args`: Argument namespace (may contain `config` attribute)
- `cwd`: Current working directory

**Returns:**
- Path to config file, or `None` if not found.

### `load_config(config_path: Path) -> dict[str, Any] | list[Any] | None`

Load configuration data from a file.

**Parameters:**
- `config_path`: Path to config file

**Returns:**
- Raw config object (dict, list, or None)

**Example:**
```python
from serger import load_config
from pathlib import Path

config = load_config(Path(".serger.jsonc"))
```

### `load_and_validate_config(args: argparse.Namespace) -> tuple[Path, RootConfig, ValidationSummary] | None`

Find, load, parse, and validate configuration.

**Returns:**
- Tuple of `(config_path, root_config, validation_summary)` or `None`

### `parse_config(raw_config: dict | list) -> RootConfig | None`

Parse raw config structure into typed form.

### `validate_config(parsed_cfg: RootConfig) -> ValidationSummary`

Validate configuration schema.

## Utility Functions

### `is_excluded(path: Path, excludes: list[str], respect_gitignore: bool) -> bool`

Check if a path should be excluded.

### `make_pathresolved(path: str | Path, origin: OriginType) -> PathResolved`

Create a resolved path object.

### `make_includeresolved(include: str, origin: OriginType) -> IncludeResolved`

Create a resolved include pattern object.

## Constants

### Log Levels

```python
from serger import DEFAULT_LOG_LEVEL

# Available levels: "trace", "debug", "info", "warning", "error"
```

### Default Values

```python
from serger import (
    DEFAULT_OUT_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_RESPECT_GITIGNORE,
    DEFAULT_STRICT_CONFIG,
    DEFAULT_WATCH_INTERVAL,
)
```

### Environment Variables

```python
from serger import (
    DEFAULT_ENV_LOG_LEVEL,
    DEFAULT_ENV_RESPECT_GITIGNORE,
    DEFAULT_ENV_WATCH_INTERVAL,
)
```

## Logging

### `get_app_logger() -> AppLogger`

Get the application logger instance.

**Example:**
```python
from serger import get_app_logger

logger = get_app_logger()
logger.info("Building...")
logger.debug("Debug information")
```

## Metadata

### `Metadata`

Dataclass containing version and commit information.

```python
@dataclass(frozen=True)
class Metadata:
    version: str
    commit: str
```

## Example: Custom Build Script

```python
#!/usr/bin/env python3
"""Custom build script using Serger's API."""

from pathlib import Path
from serger import (
    run_build,
    resolve_config,
    get_metadata,
    get_app_logger,
)

def custom_build():
    """Run a custom build with additional logic."""
    logger = get_app_logger()
    logger.info("Starting custom build...")
    
    # Get metadata
    meta = get_metadata()
    logger.info(f"Using Serger {meta.version}")
    
    # Resolve config
    config_path = Path(".serger.jsonc")
    root_cfg, builds = resolve_config(config_path)
    
    # Run each build
    for build in builds:
        logger.info(f"Building {build['package']}...")
        run_build(build, root_cfg)
        logger.info(f"✓ Built {build['package']}")
    
    logger.info("Build complete!")

if __name__ == "__main__":
    custom_build()
```

## Type Hints

All public functions and classes are fully type-annotated. Use a type checker like `mypy` or `pyright` for IDE support and validation.

## Internal vs Public API

Anything prefixed with `_` is considered internal and may change without notice. The public API consists of:

- Functions and classes exported in `serger.__init__`
- Types defined in `serger.config`
- Constants defined in `serger.constants`

