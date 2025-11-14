---
layout: default
title: Getting Started
permalink: /getting-started
---

# Getting Started

This guide will help you get up and running with Serger in just a few minutes.

## Installation

Serger is a single-file Python script that requires **Python 3.10 or higher**. No pip, no dependencies, no package managers.

### Option 1: Download the Script

Download the self-contained executable from the repository:

```bash
curl -O https://raw.githubusercontent.com/apathetic-tools/serger/main/bin/serger.py
chmod +x serger.py
```

### Option 2: Clone the Repository

```bash
git clone https://github.com/apathetic-tools/serger.git
cd serger
python3 bin/serger.py --version
```

### Option 3: Use as a Module

If you have Serger installed as a package:

```bash
poetry run python -m serger --version
```

## Verify Installation

Run the built-in self-test to verify everything works:

```bash
python3 serger.py --selftest
```

You should see output indicating that the self-test passed successfully.

## Basic Usage

### Quick Example

Create a simple project structure:

```
myproject/
├── src/
│   └── mypkg/
│       ├── __init__.py
│       ├── utils.py
│       └── main.py
└── .serger.jsonc
```

Create a config file `.serger.jsonc`:

```jsonc
{
  "builds": [
    {
      "package": "mypkg",
      "include": ["src/mypkg/**/*.py"],
      "exclude": ["**/__init__.py", "**/__pycache__/**"],
      "out": "dist/mypkg.py"
    }
  ]
}
```

Run Serger:

```bash
python3 serger.py
```

This will create `dist/mypkg.py` — a single-file executable containing all your module code.

### Command-Line Usage

You can also use Serger without a config file:

```bash
# Basic usage with positional arguments
python3 serger.py src/mypkg/**/*.py dist/mypkg.py

# With explicit flags
python3 serger.py --include "src/mypkg/**/*.py" --out dist/mypkg.py

# Exclude patterns
python3 serger.py --include "src/**/*.py" --exclude "**/test*.py" --out dist/app.py
```

## Next Steps

- Learn about [Configuration](/configuration) options
- Check out the [CLI Reference](/cli-reference) for all available options
- See [Examples](/examples) for real-world usage patterns

