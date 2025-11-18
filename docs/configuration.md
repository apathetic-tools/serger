---
layout: default
title: Configuration
permalink: /configuration
---

# Configuration

Serger uses configuration files to define how modules should be stitched together. Config files can be written in JSON, JSONC (JSON with comments), or Python.

For a complete reference of all configuration options, see the [Configuration Reference](/configuration-reference).

## Config File Location

Configuration files should typically live in your project root and be named `.serger.jsonc`. You can also use the `--config` CLI flag to specify a custom path, or place a `.serger.jsonc`, `.serger.json`, or `.serger.py` file at or above the current working directory.

## Config File Formats

### JSONC/JSON Format

JSONC (JSON with comments) is recommended for readability:

```jsonc
{
  "package": "mypkg",
  "description": "A simple package example",
  "include": ["src/mypkg/**/*.py"],
  "exclude": [],
  "out": "dist/mypkg.py"
}
```

For the Python format, see the [Config File Formats](/configuration-reference#config-file-formats) section in the Configuration Reference. 

## Pyproject.toml Integration

Serger can automatically extract metadata from `pyproject.toml`:

- `package` - fallback from `[project] name`
- `display_name` - indirectly through `package` fallback
- `description` - fallback from `[project] description`
- `license` - fallback from `[project] license` (supports PEP 621 and PEP 639 formats)
- `license_files` - fallback from `[project] license-files` (glob patterns)
- `authors` - fallback from `[project] authors`
- `version` - fallback from `[project] version` (stored as `_pyproject_version` for build metadata)

For configless builds, pyproject.toml metadata is used by default. For builds with config files, use `use_pyproject_metadata: true` or set `pyproject_path` to enable. Package name is always extracted from pyproject.toml (if available) for resolution purposes, regardless of the `use_pyproject_metadata` setting.

## Package Resolution

The `package` field can be automatically inferred if not explicitly set. Serger will attempt to determine the package name in the following order:

1. **Explicitly provided** - If `package` is set in your config, it is always used
2. **pyproject.toml** - Extracted from `[project] name` if available
3. **Include paths** - Inferred from the include patterns you provide
4. **module_bases** - Auto-detected from modules found in `module_bases` directories

See the [Configuration Reference](/configuration-reference) for details.



## Essential Configuration Options

All configuration options are specified at the root level of the config file:

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `package` | `str` | Yes* | - | Package name (used for import shims). Can be inferred automatically if not set (see [Package Resolution](#package-resolution) below). |
| `description` | `str` | No | - | Description for generated header |
| `include` | `list[str]` | Yes* | - | Glob patterns for files to include |
| `exclude` | `list[str]` | No | `[]` | Glob patterns for files to exclude |
| `out` | `str` | Yes* | - | Output file path (relative to project root) |
| `log_level` | `str` | No | `"info"` | Log verbosity level |
| `strict_config` | `bool` | No | `true` | Whether to error on missing include patterns |
| `respect_gitignore` | `bool` | No | `true` | Whether to respect `.gitignore` when selecting files |


\* Required unless provided via CLI arguments

## Include and Exclude Patterns

Patterns use glob syntax and are resolved relative to the project root:

```jsonc
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
```

### Pattern Examples

- `src/**/*.py` — All Python files in `src` and subdirectories
- `src/mypkg/*.py` — All Python files directly in `src/mypkg`
- `**/__init__.py` — All `__init__.py` files anywhere
- `tests/**` — Everything in the `tests` directory

## Example: Simple Configuration

Here's a simple example configuration file:

```jsonc
// .serger.jsonc
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
```

For advanced options like import handling, stitch modes, comment handling, and more, see the [Configuration Reference](/configuration-reference).
