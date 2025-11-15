---
layout: default
title: Configuration
permalink: /configuration
---

# Configuration

Serger uses configuration files to define how modules should be stitched together. Config files can be written in JSON, JSONC (JSON with comments), or Python.

For a complete reference of all configuration options, see the [Configuration Reference](/configuration-reference).

## Config File Location

Serger searches for configuration files in the following order:

1. Explicit path from CLI (`--config` flag)
2. Default candidates in the current working directory (and parent directories):
   - `.serger.py`
   - `.serger.jsonc`
   - `.serger.json`

The search walks up the directory tree from the current working directory until it finds a config file or reaches the filesystem root.

## Config File Formats

### JSON/JSONC Format

JSONC (JSON with comments) is recommended for readability:

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "exclude": ["**/__init__.py", "**/__pycache__/**"],
      "out": "dist/mypkg.py",
      "display_name": "My Package",
      "description": "A simple package example"
    }
  ],
  "log_level": "info"
}
```

### Python Format

Python configs allow for dynamic configuration:

```python
# .serger.py
config = {
    "builds": [
        {
            "package": "mypkg",
            "include": ["src/mypkg/**/*.py"],
            "exclude": ["**/__init__.py", "**/__pycache__/**"],
            "out": "dist/mypkg.py",
        }
    ],
    "log_level": "info",
}
```

Python configs can also use local imports:

```python
# .serger.py
from helpers import get_build_config

config = {
    "builds": [get_build_config()],
}
```

## Essential Configuration Options

### Root Options

These options apply globally and can cascade into individual builds:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `builds` | `list[BuildConfig]` | `[]` | List of build configurations |
| `log_level` | `str` | `"info"` | Log verbosity: `trace`, `debug`, `info`, `warning`, `error` |
| `out` | `str` | - | Default output path (can be overridden per build) |

### Build Options

Each build in the `builds` array can specify:

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `package` | `str` | Yes | Package name (used for import shims) |
| `include` | `list[str]` | Yes* | Glob patterns for files to include |
| `exclude` | `list[str]` | No | Glob patterns for files to exclude |
| `out` | `str` | Yes* | Output file path (relative to project root) |
| `display_name` | `str` | No | Display name for generated header |
| `description` | `str` | No | Description for generated header |

\* Required unless provided via CLI arguments

## Include and Exclude Patterns

Patterns use glob syntax and are resolved relative to the project root:

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": [
        "src/mypkg/**/*.py",      // All Python files in mypkg
        "src/utils/**/*.py"       // All Python files in utils
      ],
      "exclude": [
        "**/__init__.py",         // Exclude all __init__.py files
        "**/__pycache__/**",      // Exclude cache directories
        "**/test_*.py",           // Exclude test files
        "**/*_test.py"            // Exclude test files (alternative pattern)
      ],
      "out": "dist/mypkg.py"
    }
  ]
}
```

### Pattern Examples

- `src/**/*.py` — All Python files in `src` and subdirectories
- `src/mypkg/*.py` — All Python files directly in `src/mypkg`
- `**/__init__.py` — All `__init__.py` files anywhere
- `tests/**` — Everything in the `tests` directory

## Multiple Builds

You can define multiple builds in a single config file:

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py"
    },
    {
      "package": "utils",
      "include": ["src/utils/**/*.py"],
      "out": "dist/utils.py"
    }
  ]
}
```

## Example: Simple Configuration

Here's a simple example configuration file:

```jsonc
// .serger.jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "display_name": "My Package",
      "description": "A simple package example",
      "include": ["src/mypkg/**/*.py"],
      "exclude": [
        "**/__init__.py",
        "**/__pycache__/**"
      ],
      "out": "dist/mypkg.py"
    }
  ],
  "log_level": "info"
}
```

For advanced options like import handling, stitch modes, comment handling, and more, see the [Configuration Reference](/configuration-reference).
