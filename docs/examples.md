---
layout: default
title: Examples
permalink: /examples
---

# Examples

Real-world examples of using Serger to stitch Python modules into single-file executables.

## Basic Example

### Project Structure

```
myproject/
├── src/
│   └── mypkg/
│       ├── __init__.py
│       ├── utils.py
│       └── main.py
└── .serger.jsonc
```

### Source Files

**`src/mypkg/utils.py`:**
```python
def helper():
    return "Hello from utils"
```

**`src/mypkg/main.py`:**
```python
from .utils import helper

def main():
    result = helper()
    print(result)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### Configuration

**`.serger.jsonc`:**
```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "exclude": ["**/__init__.py", "**/__pycache__/**"],
  "out": "dist/mypkg.py"
}
```

### Build

```bash
python3 serger.py
```

This creates `dist/mypkg.py` — a single-file executable.

## Excluding Test Files

### Configuration

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "exclude": [
    "**/__init__.py",
    "**/__pycache__/**",
    "**/test_*.py",
    "**/*_test.py",
    "tests/**"
  ],
  "out": "dist/mypkg.py"
}
```

## Using Python Config for Dynamic Configuration

### `.serger.py`

```python
import os
from pathlib import Path

# Determine build type from environment
build_type = os.getenv("BUILD_TYPE", "dev")

# Base configuration
base_config = {
    "package": "mypkg",
    "include": ["src/mypkg/**/*.py"],
    "exclude": ["**/__init__.py", "**/__pycache__/**"],
}

# Adjust based on build type
if build_type == "production":
    base_config["exclude"].extend([
        "**/test_*.py",
        "**/*_test.py",
        "**/debug*.py",
    ])
    base_config["out"] = "dist/mypkg-prod.py"
else:
    base_config["out"] = "dist/mypkg-dev.py"

config = {
    **base_config,
    "log_level": "info" if build_type == "production" else "debug",
}
```

### Usage

```bash
# Development build
python3 serger.py

# Production build
BUILD_TYPE=production python3 serger.py
```

## Self-Hosting Example (Serger's Own Config)

Serger uses itself to build itself! Here's its configuration:

**`.serger.jsonc`:**
```jsonc
{
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
  "out": "dist/serger.py",
  "log_level": "info",
  "strict_config": true,
  "respect_gitignore": true
}
```

## Watch Mode for Development

### Configuration

```jsonc
{
  "package": "mypkg",
  "include": ["src/**/*.py"],
  "exclude": ["**/__init__.py", "**/__pycache__/**"],
  "out": "dist/mypkg.py",
  "watch_interval": 1.0
}
```

### Usage

```bash
# Watch for changes and rebuild automatically
python3 serger.py --watch

# Custom watch interval
python3 serger.py --watch 2.5
```

## CLI-Only Usage (No Config File)

### Simple Build

```bash
python3 serger.py src/**/*.py dist/app.py
```

### With Excludes

```bash
python3 serger.py \
  --include "src/**/*.py" \
  --exclude "**/test*.py" "**/__pycache__/**" \
  --out dist/app.py
```

### Extending Config

```bash
# Add extra files to existing config
python3 serger.py --add-include "extra/**/*.py"

# Add extra excludes
python3 serger.py --add-exclude "**/*_backup.py"
```

## Programmatic Usage

### Custom Build Script

```python
#!/usr/bin/env python3
"""Custom build script."""

from pathlib import Path
from serger import run_build, resolve_config, get_app_logger

def main():
    logger = get_app_logger()
    logger.info("Starting build...")
    
    # Resolve config
    config_path = Path(".serger.jsonc")
    resolved_cfg = resolve_config(config_path)
    
    # Run build
    logger.info(f"Building {resolved_cfg['package']}...")
    run_build(resolved_cfg)
    
    logger.info("Build complete!")

if __name__ == "__main__":
    main()
```

## Advanced: Metadata and Headers

### Configuration

```jsonc
{
  "package": "mypkg",
  "include": ["src/mypkg/**/*.py"],
  "exclude": ["**/__init__.py", "**/__pycache__/**"],
  "out": "dist/mypkg.py",
  "display_name": "My Package",
  "description": "A simple package",
  "repo": "https://github.com/user/mypkg",
  "license_header": "License: MIT"
}
```

This generates a single-file script with a header containing metadata.

## Tips and Best Practices

1. **Use JSONC for readability**: Comments make configs easier to understand
2. **Exclude `__init__.py`**: These are handled automatically by import shims
3. **Respect `.gitignore`**: Enable `respect_gitignore` to avoid including unwanted files
4. **Use watch mode for development**: Automatically rebuild on file changes
5. **Test the output**: Run `--selftest` or test the generated script
6. **Use dry-run**: Test your config with `--dry-run` before building

## Common Patterns

### Excluding Development Files

```jsonc
{
  "exclude": [
    "**/__init__.py",
    "**/__pycache__/**",
    "**/test*.py",
    "**/*_test.py",
    "**/conftest.py",
    "**/pytest.ini",
    ".pytest_cache/**"
  ]
}
```

### Including Only Source Files

```jsonc
{
  "include": [
    "src/**/*.py"
  ],
  "exclude": [
    "**/__init__.py",
    "**/__pycache__/**"
  ]
}
```

### Multiple Source Directories

```jsonc
{
  "include": [
    "src/**/*.py",
    "lib/**/*.py",
    "utils/**/*.py"
  ]
}
```

