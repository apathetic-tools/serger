---
layout: default
title: Configuration
permalink: /configuration
---

# Configuration

Serger uses configuration files to define how modules should be stitched together. Config files can be written in JSON, JSONC (JSON with comments), or Python.

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
  "log_level": "info",
  "strict_config": true,
  "respect_gitignore": true
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

## Root Configuration Options

These options apply globally and can cascade into individual builds:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `builds` | `list[BuildConfig]` | `[]` | List of build configurations |
| `log_level` | `str` | `"info"` | Log verbosity: `trace`, `debug`, `info`, `warning`, `error` |
| `out` | `str` | - | Default output path (can be overridden per build) |
| `respect_gitignore` | `bool` | `true` | Whether to respect `.gitignore` when selecting files |
| `strict_config` | `bool` | `true` | Whether to error on missing include patterns |
| `watch_interval` | `float` | `1.0` | File watch interval in seconds (for `--watch` mode) |
| `use_pyproject` | `bool` | `true` | Whether to pull metadata from `pyproject.toml` |
| `pyproject_path` | `str` | - | Path to `pyproject.toml` (fallback for single builds) |

## Build Configuration Options

Each build in the `builds` array can specify:

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `package` | `str` | Yes | Package name (used for import shims) |
| `include` | `list[str]` | Yes* | Glob patterns for files to include |
| `exclude` | `list[str]` | No | Glob patterns for files to exclude |
| `out` | `str` | Yes* | Output file path (relative to project root) |
| `display_name` | `str` | No | Display name for generated header |
| `description` | `str` | No | Description for generated header |
| `repo` | `str` | No | Repository URL for generated header |
| `license_header` | `str` | No | License text for generated header |
| `strict_config` | `bool` | No | Override root-level `strict_config` for this build |

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

## Environment Variables

Some configuration can be overridden via environment variables:

- `SERGER_LOG_LEVEL` — Log verbosity level
- `SERGER_RESPECT_GITIGNORE` — Whether to respect `.gitignore` (true/false)

## CLI Overrides

Most config options can be overridden via command-line arguments. See the [CLI Reference](/cli-reference) for details.

## Example: Complete Configuration

Here's a complete example configuration file:

```jsonc
// .serger.jsonc
{
  "builds": [
    {
      // Main package build
      "package": "serger",
      "display_name": "Serger",
      "description": "Stitch your module into a single file.",
      "repo": "https://github.com/apathetic-tools/serger",
      "license_header": "License: MIT-aNOAI\nFull text: https://github.com/apathetic-tools/serger/blob/main/LICENSE",
      "include": [
        "src/apathetic_*/**/*.py",
        "src/serger/**/*.py"
      ],
      "exclude": [
        "__pycache__/**",
        "*.pyc",
        "**/__init__.py",
        "**/__main__.py"
      ],
      "out": "dist/serger.py"
    }
  ],
  "log_level": "info",
  "strict_config": true,
  "respect_gitignore": true
}
```

