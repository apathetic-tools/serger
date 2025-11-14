---
layout: default
title: CLI Reference
permalink: /cli-reference
---

# CLI Reference

Complete reference for Serger's command-line interface.

## Basic Usage

```bash
python3 serger.py [OPTIONS] [INCLUDE...] [OUT]
```

## Positional Arguments

### `INCLUDE...` (optional)

Positional include paths or patterns (shorthand for `--include`).

```bash
python3 serger.py src/mypkg/**/*.py
```

### `OUT` (optional)

Positional output file or directory (shorthand for `--out`).  
Use trailing slash for directories (e.g., `dist/`), otherwise treated as file.

```bash
python3 serger.py src/**/*.py dist/app.py
python3 serger.py src/**/*.py dist/  # Directory output
```

## Options

### File Selection

#### `--include PATTERN [PATTERN ...]`

Override include patterns. Format: `path` or `path:dest`

```bash
python3 serger.py --include "src/**/*.py" "utils/**/*.py"
```

#### `--exclude PATTERN [PATTERN ...]`

Override exclude patterns.

```bash
python3 serger.py --exclude "**/test*.py" "**/__pycache__/**"
```

#### `--add-include PATTERN [PATTERN ...]`

Additional include paths (relative to cwd). Extends config includes.

```bash
python3 serger.py --add-include "extra/**/*.py"
```

#### `--add-exclude PATTERN [PATTERN ...]`

Additional exclude patterns. Extends config excludes.

```bash
python3 serger.py --add-exclude "**/*_backup.py"
```

### Output

#### `-o, --out PATH`

Override output file or directory.  
Use trailing slash for directories (e.g., `dist/`), otherwise treated as file.

```bash
python3 serger.py --out dist/app.py
python3 serger.py --out dist/  # Directory
```

### Configuration

#### `-c, --config PATH`

Path to build config file.

```bash
python3 serger.py --config custom.jsonc
```

### Behavior

#### `--dry-run`

Simulate build actions without writing files.

```bash
python3 serger.py --dry-run
```

#### `--watch [SECONDS]`

Rebuild automatically on changes. Optionally specify interval in seconds.

```bash
python3 serger.py --watch          # Use default interval
python3 serger.py --watch 2.5      # 2.5 second interval
```

### Gitignore

#### `--gitignore`

Respect `.gitignore` when selecting files (default).

```bash
python3 serger.py --gitignore
```

#### `--no-gitignore`

Ignore `.gitignore` and include all files.

```bash
python3 serger.py --no-gitignore
```

### Logging

#### `-q, --quiet`

Suppress non-critical output (same as `--log-level warning`).

```bash
python3 serger.py --quiet
```

#### `-v, --verbose`

Verbose output (same as `--log-level debug`).

```bash
python3 serger.py --verbose
```

#### `--log-level LEVEL`

Set log verbosity level. Choices: `trace`, `debug`, `info`, `warning`, `error`

```bash
python3 serger.py --log-level debug
```

### Output Formatting

#### `--no-color`

Disable ANSI color output.

```bash
python3 serger.py --no-color
```

#### `--color`

Force-enable ANSI color output (overrides auto-detect).

```bash
python3 serger.py --color
```

### Information

#### `--version`

Show version info.

```bash
python3 serger.py --version
```

#### `--selftest`

Run a built-in sanity test to verify tool correctness.

```bash
python3 serger.py --selftest
```

## Examples

### Basic Usage with Config

```bash
# Use default config (.serger.jsonc)
python3 serger.py

# Use custom config
python3 serger.py --config myconfig.jsonc
```

### Configless Usage

```bash
# Simple include and output
python3 serger.py src/**/*.py dist/app.py

# Multiple includes
python3 serger.py --include "src/**/*.py" "utils/**/*.py" --out dist/app.py

# With excludes
python3 serger.py --include "src/**/*.py" --exclude "**/test*.py" --out dist/app.py
```

### Extending Config

```bash
# Add additional includes to config
python3 serger.py --add-include "extra/**/*.py"

# Add additional excludes
python3 serger.py --add-exclude "**/*_backup.py"
```

### Watch Mode

```bash
# Watch for changes with default interval
python3 serger.py --watch

# Watch with custom interval
python3 serger.py --watch 2.5
```

### Debugging

```bash
# Verbose output
python3 serger.py --verbose

# Dry run to see what would happen
python3 serger.py --dry-run --verbose
```

## Argument Precedence

When the same option is specified in multiple places, precedence is:

1. **CLI arguments** (highest priority)
2. Environment variables
3. Config file
4. Defaults (lowest priority)

## Common Patterns

### Build from Config

```bash
python3 serger.py
```

### Override Output Path

```bash
python3 serger.py --out dist/custom.py
```

### Quick Test Build

```bash
python3 serger.py --include "src/**/*.py" --exclude "**/test*.py" --out test.py
```

### Production Build with Verbose Logging

```bash
python3 serger.py --verbose --out dist/production.py
```

