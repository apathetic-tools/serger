---
layout: default
title: Serger
description: Stitch your module into a single file
---

# Serger 🧵

**Stitch your module into a single file.**

*Because packaging is overrated.*

Serger is a Python module stitcher that combines multiple source files into a single executable script. It's purely focused on stitching — no file copying, no complex build systems, just clean, config-driven module combination.

## Quick Start

The self-contained executable script lives at [**`bin/serger.py`**](https://github.com/apathetic-tools/serger/blob/main/bin/serger.py).  
The only requirement is **Python 3.10+** — no pip, no dependencies.

Download or copy that one file anywhere and run it directly:

```bash
python3 serger.py
```

That's it. ✨

## Key Features

- **One responsibility**: Stitching only, no file copying
- **Config-driven**: Eliminate hardcoded module order
- **Self-hosting**: Serger builds itself using its own config
- **Well-tested**: Unit, integration, and E2E coverage
- **Zero dependencies**: Single-file executable, Python 3.10+ only

## Verify Your Install

Serger includes a built-in self-check — no pytest required.  
You can verify that the script works correctly on your system by running:

```bash
python3 serger.py --selftest
```

This creates a tiny temporary project, stitches a few test files, and confirms it completes successfully.  
If you see a ✅ "Self-test passed" message, your installation is working perfectly.

## Documentation

- **[Getting Started](/getting-started)** — Installation and first steps
- **[Configuration](/configuration)** — Config file format and options
- **[CLI Reference](/cli-reference)** — Command-line options and usage
- **[API Documentation](/api)** — Programmatic API for integrations
- **[Examples](/examples)** — Real-world usage examples

## License

[MIT-aNOAI License](https://github.com/apathetic-tools/serger/blob/main/LICENSE)

You're free to use, copy, and modify the script under the standard MIT terms.  
The additional rider simply requests that this project not be used to train or fine-tune AI/ML systems until the author deems fair compensation frameworks exist.  
Normal use, packaging, and redistribution for human developers are unaffected.

---

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="https://github.com/apathetic-tools/serger/blob/main/LICENSE">MIT-aNOAI</a></sub>
</p>

