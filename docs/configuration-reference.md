---
layout: default
title: Configuration Reference
permalink: /configuration-reference
---

# Configuration Reference

Complete reference for all Serger configuration options. For a quick start guide, see [Configuration](/configuration).

## Config File Location

Serger searches for configuration files in the following order:

1. Explicit path from CLI (`--config` flag)
2. Default candidates in the current working directory (and parent directories):
   - `.serger.py`
   - `.serger.jsonc`
   - `.serger.json`

The search walks up the directory tree from the current working directory until it finds a config file or reaches the filesystem root.

## Config File Formats

Serger supports three configuration file formats: JSON, JSONC (JSON with comments), and Python.

### JSON/JSONC Format

JSONC (JSON with comments) is recommended for readability:

```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "exclude": ["**/__init__.py", "**/__pycache__/**"],
  "out": "dist/mypkg.py",
  "display_name": "My Package",
  "description": "A simple package example"
}
```

### Python Format

Python configs allow for dynamic configuration:

```python
# .serger.py
config = {
    "package": "mypkg",
    "include": ["src/mypkg/**/*.py"],
    "exclude": ["**/__init__.py", "**/__pycache__/**"],
    "out": "dist/mypkg.py",
}
```

Python configs can also use local imports:

```python
# .serger.py
from helpers import get_build_config

config = get_build_config()
```

## Configuration Options

All configuration options are specified at the root level of the config file:

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `package` | `str` | Yes† | - | Package name (used for import shims). Can be inferred from `pyproject.toml` name, includes, or `module_bases`. |
| `include` | `list[str]` | Yes* | - | Glob patterns for files to include |
| `exclude` | `list[str]` | No | `[]` | Glob patterns for files to exclude |
| `out` | `str` | Yes* | - | Output file path (relative to project root) |
| `display_name` | `str` | No† | - | Display name for generated header. Falls back to `package` |
| `description` | `str` | No† | - | Description for generated header. |
| `repo` | `str` | No | - | Repository URL for generated header |
| `license_header` | `str` | No† | - | License text for generated header. Fallback from `pyproject.toml` `[project] license`. |
| `authors` | `str` | No† | - | Authors for generated header. |
| `log_level` | `str` | No | `"info"` | Log verbosity: `trace`, `debug`, `info`, `warning`, `error` |
| `respect_gitignore` | `bool` | No | `true` | Whether to respect `.gitignore` when selecting files |
| `strict_config` | `bool` | No | `true` | Whether to error on missing include patterns |
| `disable_build_timestamp` | `bool` | No | `false` | Replace build timestamps with placeholder for deterministic builds (see [Build Timestamps](#build-timestamps)) |
| `watch_interval` | `float` | No | `1.0` | File watch interval in seconds (for `--watch` mode) |
| `use_pyproject_metadata` | `bool` | No | - | Whether to pull metadata (description, authors, license, version) from `pyproject.toml`. Defaults to `true`, explicit `pyproject_path` also enables. `package` is always extracted as fallback. |
| `pyproject_path` | `str` | No | - | Path to `pyproject.toml` (relative to config directory). Setting this implicitly enables pyproject.toml usage. |
| `internal_imports` | `str` | No | `"force_strip"` | How to handle internal package imports (see [Import Handling](#import-handling)) |
| `external_imports` | `str` | No | `"top"` | How to handle external imports (see [Import Handling](#import-handling)) |
| `stitch_mode` | `str` | No | `"raw"` | How to combine modules into a single file (see [Stitch Modes](#stitch-modes)) |
| `module_mode` | `str` | No | `"multi"` | How to generate import shims for single-file runtime (see [Module Modes](#module-modes)) |
| `shim` | `str` | No | `"all"` | Controls shim generation (see [Shim Setting](#shim-setting)) |
| `module_actions` | `dict \| list` | No | - | Custom module transformations (see [Module Actions](#module-actions)) |
| `comments_mode` | `str` | No | `"keep"` | How to handle comments in stitched output (see [Comment Handling](#comment-handling)) |
| `docstring_mode` | `str \| dict` | No | `"keep"` | How to handle docstrings in stitched output (see [Docstring Handling](#docstring-handling)) |
| `module_bases` | `str \| list[str]` | No | `["src"]` | Ordered list of directories where packages can be found (see [Module Bases](#module-bases)) |
| `main_mode` | `"none" \| "auto"` | No | `"auto"` | How to handle main function detection and `__main__` block generation (see [Main Configuration](#main-configuration)) |
| `main_name` | `str \| None` | No | `None` | Specification for which main function to use (see [Main Configuration](#main-configuration)) |

\* Required unless provided via CLI arguments. 

\† Can fallback from `pyproject.toml` metadata when enabled.

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
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "stitch_mode": "raw"  // Use raw mode (default)
}
```

> **Note**: Currently, only `raw` mode is implemented. Attempting to use `class` or `exec` will raise a `NotImplementedError`. The default import handling modes are automatically selected based on the stitch mode, but you can override them if needed.

## Module Modes

Serger provides control over how import shims are generated for the single-file runtime. Import shims allow external code to import modules from the stitched file as if they were separate files. Different shim modes control how module names are organized and whether packages are preserved or flattened.

**Available modes:**

| Mode | Description |
|------|-------------|
| `none` | No shims generated. The stitched file cannot be imported as a module. Use this when you only need a standalone script. |
| `multi` | Generate shims for all detected packages (default). Each detected package gets its own shim, preserving the original package structure. For example, if you stitch `pkg1` and `pkg2`, both will be available as separate packages. |
| `force` | Replace root package but keep subpackages. All detected package roots are replaced with the configured `package` name, but subpackages are preserved. For example, `pkg1.sub` and `pkg2.sub` both become `mypkg.sub`. |
| `force_flat` | Flatten everything to configured package. All modules become direct children of the configured `package` name, removing all package hierarchy. For example, `pkg1.sub.module` becomes `mypkg.module`. |
| `unify` | Place all detected packages under the configured package, combining if package matches. If the configured `package` matches a detected package, they are combined (no double prefix). Other detected packages are placed under the configured package. For example, with `package="serger"` and detected packages `{"serger", "apathetic_logs"}`, `serger.utils` stays as `serger.utils`, but `apathetic_logs.logs` becomes `serger.apathetic_logs.logs`. Loose files attach directly to the configured package. |
| `unify_preserve` | Like `unify` but preserves structure when package matches. Similar to `unify`, but when the configured `package` matches a detected package, the full structure is preserved without any flattening. Loose files still attach to the configured package as module files. |
| `flat` | Treat loose files as top-level modules (not under package). Loose files (files not in a package directory) are kept as top-level modules without the package prefix. Packages still get shims as usual. For example, `main.py` stays as `main`, not `mypkg.main`. |

### Choosing a Module Mode

- **`multi`** (default): Use this for most cases. It preserves the original package structure and allows multiple packages to coexist in the stitched file.

- **`none`**: Use when you only need a standalone executable script and don't need import shims.

- **`force`**: Use when you want to unify multiple packages under a single package name while preserving subpackage structure.

- **`force_flat`**: Use when you want to completely flatten the package hierarchy into a single namespace.

- **`unify`**: Use when you want to collect all packages under a single root package, combining the configured package if it matches a detected package.

- **`unify_preserve`**: Use when you want `unify` behavior but need to preserve the full structure of the configured package when it matches.

- **`flat`**: Use when you want loose files to be accessible as top-level modules without package prefixes.

### Example

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_mode": "multi"  // Generate shims for all detected packages
}
```

## Shim Setting

The `shim` setting controls whether import shims are generated and which modules get shims. This setting works in conjunction with `module_mode` and `module_actions` to control the final shim structure.

**Available values:**

| Value | Description |
|-------|-------------|
| `all` | Generate shims for all modules (default). All modules that would normally get shims based on `module_mode` and `module_actions` will have shims generated. |
| `public` | Only generate shims for public modules. Currently treated the same as `all` (future: will filter based on `_` prefix or `__all__`). |
| `none` | Don't generate shims at all. The stitched file cannot be imported as a module. Use this when you only need a standalone script. |

### Relationship with Module Mode and Module Actions

The `shim` setting acts as a filter on top of `module_mode` and `module_actions`:

1. **`module_mode`** determines the overall strategy for organizing shims (e.g., `multi`, `force`, `unify`)
2. **`module_actions`** provides fine-grained control over specific module transformations
3. **`shim`** controls whether shims are generated at all and which modules get shims

### Example

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_mode": "multi",
  "shim": "all"  // Generate shims for all modules (default)
}
```

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "shim": "none"  // No shims - standalone script only
}
```

## Module Actions

Module actions provide fine-grained control over module organization, allowing you to rename, move, copy, or delete specific parts of the module hierarchy. Module actions can affect shim generation, stitching, or both.

**Key concepts:**
- **Actions operate on modules**: Actions transform module names in the final output
- **Can affect shims and/or stitching**: Use the `affects` key to control scope
- **Works with `module_mode`**: `module_mode` generates convenience actions that are combined with your custom actions
- **Two configuration formats**: Simple dict format for quick renames, or list format for full control

### Configuration Formats

#### Simple Dict Format

For quick renames, you can use a simple dictionary mapping source module names to destination module names:

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": {
    "old_pkg": "new_pkg",        // Move old_pkg to new_pkg
    "unwanted.module": null      // Delete unwanted.module
  }
}
```

**Behavior:**
- `{"source": "dest"}` → Move `source` to `dest` (preserves subpackages)
- `{"source": null}` → Delete `source` (removes from shims)
- Defaults: `action: "move"`, `mode: "preserve"`, `scope: "shim"`, `affects: "shims"`, `cleanup: "auto"`

#### List Format (Full Control)

For full control over all parameters, use the list format:

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "old_pkg",
          "dest": "new_pkg",
          "action": "move",
          "mode": "preserve",
          "scope": "shim",
          "affects": "shims",
          "cleanup": "auto"
        }
    }
  ]
}
```

### Action Types

| Action | Description | Requires `dest`? |
|--------|-------------|-----------------|
| `move` | Rename/relocate a module (source no longer exists in output) | Yes |
| `copy` | Duplicate a module to another location (source still exists) | Yes |
| `delete` | Remove a module from output entirely | No |
| `none` | Alias for `delete` | No |

### Action Parameters

#### Required Parameters

- **`source`** (string, required): The source module name to transform. Can be a top-level package (e.g., `"pkg1"`) or a subpackage/module (e.g., `"pkg1.sub.module"`).

#### Optional Parameters

- **`dest`** (string, optional): The destination module name. Required for `move` and `copy` actions, not used for `delete` actions.

- **`action`** (string, default: `"move"`): The action type. Valid values: `"move"`, `"copy"`, `"delete"`, `"none"`.

- **`mode`** (string, default: `"preserve"`): How to handle subpackages:
  - `"preserve"`: Keep subpackage structure (e.g., `pkg1.sub` → `newpkg.sub`)
  - `"flatten"`: Flatten all subpackages onto destination (e.g., `pkg1.sub` → `newpkg`)

- **`scope`** (string, default: `"shim"` for user actions, `"original"` for mode-generated): Which module name space to operate on:
  - `"original"`: Operate on original module names (before any transformations)
  - `"shim"`: Operate on shim module names (after `module_mode` transformations)

- **`affects`** (string, default: `"shims"`): What the action affects:
  - `"shims"`: Only affects shim generation (import shims)
  - `"stitching"`: Only affects file stitching (which files are included)
  - `"both"`: Affects both shims and stitching

- **`cleanup`** (string, default: `"auto"`): How to handle shim-stitching mismatches (when `affects: "shims"` creates a shim but the file wasn't stitched, or vice versa):
  - `"auto"`: Automatically handle mismatches (delete shims for unstitched files, skip stitching for deleted shims)
  - `"error"`: Raise an error if mismatches are detected
  - `"ignore"`: Ignore mismatches (may cause import errors at runtime)

- **`source_path`** (string, optional): Filesystem path to a Python file that should be re-included or referenced. Use this when:
  - A file was excluded but you want to include it via an action
  - You want to reference a module from a different location
  - The module name extracted from the file must match the `source` parameter (or be derivable from it)
  - Only works when `affects` includes `"stitching"` or `"both"` (files are only added to stitching when `affects` includes stitching)
  - If the file is already included, it won't be duplicated
  - If the file was excluded, `source_path` overrides the exclude for that specific file

### Examples

#### Simple Rename

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": {
    "apathetic_logs": "grinch"
  }
}
```

This moves `apathetic_logs` to `grinch`, preserving subpackages (e.g., `apathetic_logs.utils` → `grinch.utils`).

#### Flatten Subpackage

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
    {
  "source": "pkg1.sub",
          "dest": "mypkg",
          "action": "move",
      "mode": "flatten"
    }
  ]
}
```

This flattens all modules under `pkg1.sub` directly into `mypkg` (e.g., `pkg1.sub.module` → `mypkg.module`).

#### Multi-Level Operations

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
    {
  "source": "pkg1.sub.module",
          "dest": "mypkg.utils",
          "action": "move",
      "mode": "preserve"
    }
  ]
}
```

This moves a specific submodule to a new location while preserving its structure.

#### Copy Operations

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
    {
  "source": "utils",
          "dest": "mypkg.utils",
          "action": "copy"
    }
  ]
}
```

This creates a copy of `utils` at `mypkg.utils` while keeping the original `utils` module.

#### Delete Operations

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
    {
  "source": "internal._private",
          "action": "delete"
    }
  ]
}
```

This removes `internal._private` from the output entirely.

#### Mode + User Actions

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_mode": "force",  // Generates actions to replace root packages
  "module_actions": [
    {
  "source": "pkg1.sub",
          "dest": "mypkg.custom",
          "action": "move",
      "mode": "flatten"
    }
  ]
}
```

User-specified actions are applied after mode-generated actions, allowing you to override or extend the convenience presets.

#### Scope: "original" vs "shim"

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_mode": "force",  // pkg1 -> mypkg
  "module_actions": [
    {
  "source": "pkg1",  // scope: "shim" (default) - operates on shim names
          "dest": "custom",
          "action": "move"
    }
  ]
}
```

With `scope: "shim"` (default for user actions), the action operates on the shim name after `module_mode` transformations. So `pkg1` (which became `mypkg` via `module_mode: "force"`) is moved to `custom`.

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_mode": "force",
  "module_actions": [
        {
  "source": "pkg1",  // scope: "original" - operates on original names
          "dest": "custom",
          "action": "move",
          "scope": "original"
        }
    }
  ]
}
```

With `scope: "original"`, the action operates on the original module name before `module_mode` transformations. So `pkg1` is moved to `custom` before `module_mode: "force"` is applied.

#### Affects: "shims" vs "stitching" vs "both"

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "internal",
          "action": "delete",
          "affects": "shims"  // Only remove from shims, still stitch the files
        }
    }
  ]
}
```

This removes `internal` from shims but still stitches the files into the output.

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "test_utils",
          "action": "delete",
          "affects": "stitching"  // Don't stitch files, but keep shims
        }
    }
  ]
}
```

This excludes `test_utils` files from stitching but keeps the shims (useful for testing scenarios).

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "old_pkg",
          "dest": "new_pkg",
          "action": "move",
          "affects": "both"  // Affects both shims and stitching
        }
    }
  ]
}
```

This moves `old_pkg` to `new_pkg` in both shims and stitching.

#### Cleanup: "auto" vs "error" vs "ignore"

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "internal",
          "action": "delete",
          "affects": "shims",
          "cleanup": "auto"  // Automatically handle mismatches
        }
    }
  ]
}
```

With `cleanup: "auto"`, if `internal` files are stitched but the shim is deleted, the shim is automatically removed (no error).

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "internal",
          "action": "delete",
          "affects": "shims",
          "cleanup": "error"  // Raise error if mismatches detected
        }
    }
  ]
}
```

With `cleanup: "error"`, if there's a mismatch (e.g., files are stitched but shim is deleted), an error is raised.

#### Re-including Excluded Files with source_path

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "exclude": ["src/internal/**/*.py"],  // Excluded internal modules
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "utils",
          "source_path": "src/internal/utils.py",  // Re-include this file
          "dest": "public.utils",
          "affects": "both"  // Must include "stitching" to add file
        }
    }
  ]
}
```

This re-includes `src/internal/utils.py` (which was excluded) and makes it available as `public.utils`. The file is added to stitching because `affects: "both"` includes stitching.

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "exclude": ["src/internal/**/*.py"],
  "out": "dist/mypkg.py",
  "module_actions": [
        {
  "source": "utils",
          "source_path": "src/internal/utils.py",
          "dest": "public.utils",
          "affects": "shims"  // Only affects shims, file NOT added
        }
    }
  ]
}
```

With `affects: "shims"`, the file is **not** added to stitching. The action only affects shim generation, so `source_path` is ignored for file inclusion (but still validated for module name matching).

### Relationship with Module Mode

`module_mode` provides convenience presets that generate actions internally. These mode-generated actions are combined with your user-specified `module_actions`:

1. **Mode-generated actions** are created first (based on `module_mode` like `multi`, `force`, `unify`, etc.)
2. **User-specified actions** are applied after mode-generated actions
3. **User actions can override mode behavior** by operating on the same modules

For example, `module_mode: "force"` generates actions to replace all detected package roots with the configured `package` name. You can then add custom actions to further transform specific modules.

### Validation Rules

Module actions are validated to ensure correctness:

- **Source must exist**: The `source` module must exist in the available modules (based on `scope`)
- **Dest conflicts**: For `move` and `copy` actions, `dest` cannot conflict with existing modules (unless it's the target of a previous action in the same batch)
- **Dest required**: `dest` is required for `move` and `copy` actions
- **Dest not allowed**: `dest` must not be specified for `delete` actions
- **Scope consistency**: Actions with `scope: "original"` must reference original module names; actions with `scope: "shim"` must reference shim module names
- **source_path validation**: If `source_path` is specified, the file must exist and be a Python file (`.py` extension). The module name extracted from the file must match the `source` parameter (or be derivable from it). If `affects` includes `"stitching"` or `"both"`, the file must exist at the specified path.

Invalid configurations will raise errors with clear messages indicating what went wrong.

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

## Module Bases

The `module_bases` setting specifies an ordered list of directories where Serger can find packages. This setting is used to determine where to search for Python packages when resolving module paths.

### Configuration

- **Type**: `str | list[str]`
- **Default**: `["src"]`
- **Can be set at**: Root level (cascades to all builds) or per-build (overrides root)

### Examples

**Single directory (string convenience):**
```jsonc
{
  "module_bases": "lib"
}
```

**Multiple directories (list):**
```jsonc
{
  "module_bases": ["src", "lib", "vendor"]
}
```

**Per-build override:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
      "module_bases": ["src", "lib"]  // Overrides root-level setting
    }
  ],
  "module_bases": ["src"]  // Default for all builds
}
```

### Notes

- The directories are searched in the order specified
- Used for package auto-detection when `package` is not explicitly set
- When a string is provided, it is automatically converted to a list containing that single string during resolution

## Package Resolution

The `package` field is required for stitch builds, but can be automatically inferred if not explicitly set. Serger attempts to determine the package name using the following priority order:

### Resolution Order

1. **Explicitly provided** - If `package` is set in your config, it is always used (highest priority)
2. **pyproject.toml** - Extracted from `[project] name` if available
3. **Include paths** - Inferred from the include patterns you provide
4. **Main function detection** - If multiple modules exist, prefers the one containing a `main()` function or `if __name__ == "__main__"` block
5. **Single module auto-detection** - When exactly one first-level module exists in any `module_base`
6. **First package in module_bases order** - Falls back to the first module found in `module_bases` order when multiple modules exist

### Details

**Include path inference:**
- Analyzes your include patterns to extract package names
- Uses `__init__.py` and `__main__.py` markers when available
- Validates against `module_bases` to ensure packages exist
- Uses the most common package when multiple candidates are found

**Main function detection:**
- Scans modules for `def main(` functions or `if __name__ == "__main__"` blocks
- Only runs when multiple modules exist and no package has been determined yet
- Helps identify the "main" package in multi-package projects

**Single module auto-detection:**
- Scans `module_bases` directories for first-level modules/packages
- Only triggers when exactly one module exists across all `module_bases`
- Supports both package directories and single-file modules

**First package fallback:**
- Uses the first module found in `module_bases` order when all other methods fail
- Preserves the order specified in `module_bases` configuration
- Provides a predictable fallback for ambiguous cases

### Logging

Serger logs where the package name was determined from, for example:
- `Package name 'mypkg' provided in config`
- `Package name 'mypkg' extracted from pyproject.toml for resolution`
- `Package name 'mypkg' inferred from include paths. Set 'package' in config to override.`
- `Package name 'mypkg' detected via main() function. Set 'package' in config to override.`
- `Package name 'mypkg' auto-detected from single module in module_base 'src'. Set 'package' in config to override.`
- `Package name 'mypkg' selected from module_bases (first found). Set 'package' in config to override.`

You can always override the auto-detected package by explicitly setting `package` in your config.

## Main Configuration

Serger provides automatic detection and generation of `__main__` blocks for executable scripts. The `main_mode` and `main_name` settings control how main functions are found and how `__main__` blocks are handled in the stitched output.

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `main_mode` | `"none" \| "auto"` | `"auto"` | Controls main function detection and `__main__` block generation |
| `main_name` | `str \| None` | `None` | Specification for which main function to use |

### `main_mode` Values

| Value | Description |
|-------|-------------|
| `"auto"` | Automatically detect a main function and generate a `__main__` block if needed. If no main function is found, the build continues without a `__main__` block (non-main build). |
| `"none"` | Disable main function detection. No `__main__` block is generated, even if main functions exist. Use this for library builds that don't need executable entry points. |

### `main_name` Syntax

The `main_name` setting allows you to specify which function should be used as the main entry point. It supports flexible syntax for specifying module paths and function names.

#### Syntax Rules

**With dots (module/package path):** `::` separator is optional
- `mypkg.subpkg` → module `mypkg.subpkg`, function `main` (default)
- `mypkg.subpkg::` → module `mypkg.subpkg`, function `main` (explicit)
- `mypkg.subpkg::entry` → module `mypkg.subpkg`, function `entry`

**Without dots (single name):** `::` separator is required to indicate package
- `mypkg::` → package `mypkg`, function `main` (default)
- `mypkg::entry` → package `mypkg`, function `entry`
- `mypkg` → function name `mypkg` (search across all packages)
- `main` → function name `main` (search across all packages)

#### Examples

**Auto-detect (default):**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py"
  // main_name defaults to None, searches for "main" function
}
```

**Simple function name:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "cli"  // Search for "cli" function across all packages
}
```

**Package specification:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg::"  // Package "mypkg", function "main"
}
```

**Package with custom function:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg::entry"  // Package "mypkg", function "entry"
}
```

**Module path:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg.cli"  // Module "mypkg.cli", function "main"
}
```

**Module path with custom function:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg.cli::run"  // Module "mypkg.cli", function "run"
}
```

### Main Function Detection

Serger searches for main functions in the following order:

1. **If `main_name` is set:** Use the specified function (with fallback logic)
   - If a module path is specified, search in that module/package
   - If only a function name is specified, search across all packages
2. **If `package` is set:** Search for `main` function in that package
3. **Otherwise:** Search in the first package from include order

**File priority within a module:**
- `__main__.py` files are searched first
- `__init__.py` files are searched second
- Other files are searched last

**Search scope:**
- Only files that are actually being stitched are searched
- Excluded files are not considered

### `__main__` Block Handling

Serger automatically detects existing `if __name__ == '__main__':` blocks in your source files and selects which one to keep based on priority:

1. **Priority 1:** Block in the same module/file as the main function
2. **Priority 2:** Block in the same package as the main function
3. **Priority 3:** Block in the earliest include (by include order)

**Behavior:**
- If a `__main__` block is found, it is used (no new block is generated)
- All other `__main__` blocks are discarded
- If no `__main__` block is found and `main_mode="auto"`, Serger generates a new one
- If `main_mode="none"`, no `__main__` block is generated

**Generated block format:**
- Functions with parameters: `main(sys.argv[1:])`
- Functions without parameters: `main()`
- Parameter detection uses AST parsing to check for `*args`, `**kwargs`, defaults, etc.

### Auto-Rename Collision Handling

In `raw` stitch mode, if multiple functions exist with the same name as the main function, Serger automatically renames the conflicting functions to avoid collisions.

**Behavior:**
- Only applies in `raw` mode (module mode handles namespacing automatically)
- The main function itself is never renamed
- Other functions with the same name are renamed to `main_1`, `main_2`, etc.
- Only function definitions are renamed (not function calls)
- Auto-rename actions are applied after user-specified `module_actions`

**Example:**
If you have `main()` functions in both `utils.py` and `cli.py`, and the main function is in `cli.py`:
- `cli.main()` stays as `main()`
- `utils.main()` is renamed to `main_1()`

### Error Handling

**`main_name` specified but not found:**
- If `main_name` is explicitly set but the function cannot be found, Serger raises an error
- This ensures that explicit configurations are validated

**No main function found:**
- If `main_mode="auto"` and no main function is found, the build continues without a `__main__` block
- This is considered a "non-main build" and is logged as an INFO message
- No error is raised (this is expected for library builds)

### Examples

**Basic usage (auto-detect):**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_mode": "auto"  // Default: auto-detect main function
}
```

**Custom function name:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "cli"  // Use "cli" function instead of "main"
}
```

**Library build (no main block):**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_mode": "none"  // Don't generate __main__ block
}
```

**Package specification:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg::entry"  // Package "mypkg", function "entry"
}
```

**Module and function:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "main_name": "mypkg.cli::run"  // Module "mypkg.cli", function "run"
}
```

## Build Timestamps

Serger embeds build timestamps in the generated output file for tracking when builds were created. The `disable_build_timestamp` setting allows you to replace these timestamps with a placeholder string, making builds deterministic and reproducible.

### Configuration

- **Type**: `bool`
- **Default**: `false` (use real timestamps)
- **CLI flag**: `--disable-build-timestamp`

### Use Cases

**Deterministic builds** (primary use case):
- When `disable_build_timestamp: true`, all timestamps are replaced with the placeholder `<build-timestamp>`
- Multiple builds with the same source code produce identical output files
- Useful for verification, testing, and reproducible builds
- Enables byte-for-byte comparison of build outputs

**Production builds** (default):
- When `disable_build_timestamp: false` (default), real timestamps are embedded
- Timestamps show when the build was created
- Useful for debugging and tracking build history

### Timestamp Locations

When enabled, timestamps appear in the following locations in the stitched output:

1. **Header comment**: `# Build Date: <build-timestamp>`
2. **Module docstring**: `Built: <build-timestamp>`
3. **Build date constant**: `__build_date__ = "<build-timestamp>"`
4. **Version fallback**: When no version is found, the placeholder is used instead of a timestamp

### Examples

**Deterministic build (config file):**

```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py",
  "disable_build_timestamp": true
}
```

**Deterministic build (CLI):**

```bash
python3 serger.py --disable-build-timestamp
```

**Production build (default):**

```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "out": "dist/mypkg.py"
  // disable_build_timestamp defaults to false
}
```

### Output Comparison

**With timestamps (default):**
```python
# Build Date: 2024-01-15 14:30:45 UTC
"""
Built: 2024-01-15 14:30:45 UTC
...
"""
__build_date__ = "2024-01-15 14:30:45 UTC"
```

**With placeholder (deterministic):**
```python
# Build Date: <build-timestamp>
"""
Built: <build-timestamp>
...
"""
__build_date__ = "<build-timestamp>"
```

### Notes

- This is an **advanced setting** primarily intended for verification and testing purposes
- The placeholder string `<build-timestamp>` is a constant defined in Serger's code
- CLI flag `--disable-build-timestamp` overrides the config file setting
- When disabled, timestamps are generated at build time using UTC timezone

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

