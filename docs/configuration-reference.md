---
layout: default
title: Configuration Reference
permalink: /configuration-reference
---

# Configuration Reference

Complete reference for all Serger configuration options. For a quick start guide, see [Configuration](/configuration).

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
| `internal_imports` | `str` | `"force_strip"` | How to handle internal package imports (see [Import Handling](#import-handling)) |
| `external_imports` | `str` | `"top"` | How to handle external imports (see [Import Handling](#import-handling)) |
| `stitch_mode` | `str` | `"raw"` | How to combine modules into a single file (see [Stitch Modes](#stitch-modes)) |
| `comments_mode` | `str` | `"keep"` | How to handle comments in stitched output (see [Comment Handling](#comment-handling)) |
| `docstring_mode` | `str \| dict` | `"keep"` | How to handle docstrings in stitched output (see [Docstring Handling](#docstring-handling)) |

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
| `internal_imports` | `str` | No | Override root-level `internal_imports` for this build |
| `external_imports` | `str` | No | Override root-level `external_imports` for this build |
| `stitch_mode` | `str` | No | Override root-level `stitch_mode` for this build (see [Stitch Modes](#stitch-modes)) |
| `comments_mode` | `str` | No | Override root-level `comments_mode` for this build (see [Comment Handling](#comment-handling)) |
| `docstring_mode` | `str \| dict` | No | Override root-level `docstring_mode` for this build (see [Docstring Handling](#docstring-handling)) |

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

## Stitch Modes

Serger supports different modes for combining multiple Python modules into a single file. Each mode has different characteristics and use cases:

| Mode | Status | Description | Default Internal Imports | Default External Imports |
|------|--------|-------------|--------------------------|--------------------------|
| `raw` | ✅ **Implemented** | Concatenates all files together into a single namespace. All code from different modules is merged into one global scope. This is the simplest and fastest mode. | `force_strip` | `top` |
| `class` | ⚠️ **Not Yet Implemented** | Wraps each module in a class namespace. Each module becomes a class (e.g., `_Module_utils`), preserving module boundaries while still producing a single file. Internal imports are transformed to class attribute access. | `assign` | `top` |
| `exec` | ⚠️ **Not Yet Implemented** | Uses `exec()` with separate module objects in `sys.modules`. Each module maintains its own namespace and proper `__package__` attributes, allowing relative imports to work correctly. This mode most closely mimics normal Python module behavior. | `keep` | `top` |

### Choosing a Stitch Mode

- **`raw`** (default): Use this for most cases. It's the simplest and produces the most compact output. All modules share a single namespace, so internal imports are stripped since symbols are directly accessible.

- **`class`**: Planned for cases where you need module isolation but still want a single file. Each module's code runs within its own class namespace, which can help avoid naming conflicts.

- **`exec`**: Planned for maximum compatibility with existing code that relies on proper module semantics. This mode preserves `__package__` attributes and allows relative imports to work as they would in a normal Python installation.

### Example

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py",
      "stitch_mode": "raw"  // Use raw mode (default)
    }
  ],
  "stitch_mode": "raw"  // Default for all builds
}
```

> **Note**: Currently, only `raw` mode is implemented. Attempting to use `class` or `exec` will raise a `NotImplementedError`. The default import handling modes are automatically selected based on the stitch mode, but you can override them if needed.

## Comment Handling

Serger provides control over how comments are handled in the stitched output. You can choose to keep all comments, remove them, or selectively preserve only certain types of comments.

> **Note**: Comment handling does not affect docstrings (triple-quoted strings). Docstrings are controlled separately via the `docstring_mode` setting.

**Available modes:**

| Mode | Description |
|------|-------------|
| `keep` | Keep all comments (default). Preserves all comments in their original locations, including standalone comments and inline comments. |
| `ignores` | Only keep comments that specify ignore rules. Preserves comments that are used by linters and type checkers, such as `# noqa`, `# type: ignore`, `# pyright: ignore`, `# mypy: ignore`, `# ruff: noqa`, and `# serger: no-move`. All other comments are removed. |
| `inline` | Only keep inline comments. Preserves comments that appear on the same line as code (e.g., `x = 1  # comment`), but removes standalone comment lines (e.g., `# This is a comment` on its own line). |
| `strip` | Remove all comments. Removes all comments from the stitched output while preserving docstrings. This produces cleaner, more compact output. |

### Example

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py",
      "comments_mode": "ignores"  // Only keep linter/type checker ignore comments
    }
  ],
  "comments_mode": "keep"  // Default for all builds
}
```

## Docstring Handling

Serger provides control over how docstrings are handled in the stitched output. You can choose to keep all docstrings, remove them, or selectively preserve only certain types of docstrings based on their location or visibility.

> **Note**: Docstring handling uses AST parsing to accurately identify docstrings at different locations (module, class, function, method). Both triple-quoted strings (`"""..."""` and `'''...'''`) are supported. Single-line docstrings are also supported.

**Available modes:**

### Simple Modes

You can use a simple string mode to apply the same behavior to all docstrings:

| Mode | Description |
|------|-------------|
| `keep` | Keep all docstrings (default). Preserves all docstrings in their original locations, including module, class, function, and method docstrings. |
| `strip` | Remove all docstrings. Removes all docstrings from the stitched output, producing more compact code. |
| `public` | Keep only public docstrings. Preserves docstrings for public symbols (those not prefixed with an underscore), removing docstrings for private symbols (e.g., `_private_func`, `__special__`). Note: Module-level docstrings are always kept in `public` mode, as they are considered public. |

### Per-Location Control

For fine-grained control, you can use a dictionary to specify different modes for different docstring locations:

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py",
      "docstring_mode": {
        "module": "strip",    // Remove module-level docstrings
        "class": "keep",       // Keep class docstrings
        "function": "public",   // Keep only public function docstrings
        "method": "strip"     // Remove method docstrings
      }
    }
  ]
}
```

**Valid locations:**
- `module` - Module-level docstrings (at the top of the file)
- `class` - Class docstrings
- `function` - Top-level function docstrings (functions defined at module level)
- `method` - Method docstrings (functions inside classes, including regular methods, properties, static methods, class methods, and async methods)

**Location modes:**
- Each location can use `"keep"`, `"strip"`, or `"public"`
- Omitted locations default to `"keep"` (least destructive default)

### Example

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py",
      "docstring_mode": "public"  // Keep only public docstrings
    }
  ],
  "docstring_mode": "keep"  // Default for all builds
}
```

## Import Handling

Serger provides fine-grained control over how imports are handled during stitching. You can configure separate behaviors for internal imports (from the package being stitched) and external imports (from other packages).

> **Note**: The default import handling modes depend on the selected `stitch_mode`. See [Stitch Modes](#stitch-modes) for details.

### Internal Imports

Internal imports are imports from the package being stitched (e.g., `from mypkg.utils import foo` when stitching `mypkg`).

| Mode | Description |
|------|-------------|
| `force_strip` | Remove internal imports (default). Always removes imports, even inside conditional structures (if, try, etc.). Internal imports are resolved by stitching, so they can be safely removed. |
| `strip` | Remove internal imports (not yet implemented). Skips imports inside conditional structures (if, try, etc.), except `if TYPE_CHECKING` blocks which are always processed. |
| `keep` | Keep internal imports in their original locations within each module section. |
| `assign` | **[EXPERIMENTAL/WIP]** Transform imports into assignments. For example, `from mypkg.utils import foo` becomes `foo = foo` (direct reference), and `from mypkg.utils import foo as bar` becomes `bar = foo`. In stitched mode, all modules share the same global namespace, so symbols can be referenced directly. These assignments are included in collision detection. Note: `import module` statements for internal packages may not work correctly. |

### External Imports

External imports are imports from packages not being stitched (e.g., `import os`, `from pathlib import Path`).

| Mode | Description |
|------|-------------|
| `top` | Move external imports to the top (default). Moves imports to the top, but skips imports inside conditional structures (if, try, etc.), except `if TYPE_CHECKING` blocks which are always processed. |
| `force_top` | Move external imports to the top. Always moves imports, even inside conditional structures (if, try, etc.). Module-level imports are collected and deduplicated at the top. Empty structures (if, try, etc.) get a `pass` statement. Empty `if TYPE_CHECKING:` blocks (including those with only pass statements) are removed entirely. |
| `keep` | Keep external imports in their original locations within each module section. |
| `force_strip` | Remove external imports. Always removes imports, even inside conditional structures (if, try, etc.). Empty structures (if, try, etc.) get a `pass` statement. Empty `if TYPE_CHECKING:` blocks (including those with only pass statements) are removed entirely. |
| `strip` | Remove external imports (not yet implemented). Skips imports inside conditional structures (if, try, etc.), except `if TYPE_CHECKING` blocks which are always processed. Empty `if TYPE_CHECKING:` blocks (including those with only pass statements) are removed entirely. |

### Example

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "out": "dist/mypkg.py",
      "internal_imports": "force_strip",
      "external_imports": "top"
    }
  ],
  "internal_imports": "force_strip",  // Default for all builds
  "external_imports": "top"            // Default for all builds
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

