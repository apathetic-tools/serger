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
  "builds": [
    {
      "package": "mypkg",
      "description": "A simple package example",
      "include": ["src/mypkg/**/*.py"],
      "exclude": [
        "**/__pycache__/**",
      ],
      "out": "dist/mypkg.py"      
    }
  ]
}
```

For the Python format, see the [Config File Formats](/configuration-reference#config-file-formats) section in the Configuration Reference. 

The `package` and `description` fields can be inferred from `pyproject.toml`.



## Essential Configuration Options

### Root Options

These options apply globally and can cascade into individual builds:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `builds` | `list[BuildConfig]` | `[]` | List of build configurations |
| `out` | `str` | - | Default output path (can be overridden per build) |

### Build Options

Each build in the `builds` array can specify:

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `package` | `str` | Yes | Package name (used for import shims) |
| `description` | `str` | No | Description for generated header |
| `include` | `list[str]` | Yes* | Glob patterns for files to include |
| `exclude` | `list[str]` | No | Glob patterns for files to exclude |
| `out` | `str` | Yes* | Output file path (relative to project root) |


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
  ]
}
```

For advanced options like import handling, stitch modes, comment handling, and more, see the [Configuration Reference](/configuration-reference).
