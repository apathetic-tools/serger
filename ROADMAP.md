<!-- Roadmap.md -->
# 🧭 Roadmap

**Important Clarification**: Serger is **purely a Python module stitcher** - it combines multiple source files into a single executable script. File copying/building is pocket-build's responsibility, not serger's. We brought in a lot of pocket-build code because some of the functionality overlapped in how it accomplished things. Some remnanent can be removed, while some can be reused.

## Key Points
- **One responsibility**: Stitching only, no file copying
- **Config-driven**: Eliminate hardcoded module order
- **Self-hosting**: Serger builds itself using its own config
- **Well-tested**: Unit, integration, and E2E coverage

Some of these we just want to consider, and may not want to implement.

## 🎯 Core Features
Major stitching capabilities and enhancements:


## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--check-config` or `--verify-config` or `--validate-config` command
- `--self-update` — update serger itself
- `--no-update-check` — skip automatic update check



## ⚙️ Config File Enhancements

- Add key to disable update checks directly in config
- Provide a JSON Schema for validation and autocomplete
- Module-level configuration (metadata, headers)

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- How can we report what we comment tool ignore, in src and in tests?

## 🧑‍💻 Development
- How can we keep internal imports in stitch mode and avoid conflicts? (see [docs/example_isolated_stiching.md](docs/example_isolated_stiching.md))
- Evaluate ignores and determine if we can fix them instead of ignore them
- can we pull out common CLI elements with pocket-build into a single toplevel module?
- set up stitch modes
- set up comment stripper toggle
- command to do common tasks based on reddit advice for dealing with AI.
- quiet mode for the ai program

## 🚀 Deployment
- Deploy action when I tag a release should create a release and attach it to the tagged release.

## 🔌 API

## 📚 Documentation
- Do we want a way to dump the schema for documentation purposes?
- Where do we document the structure of the project? What do we document inside it vs here?
- Where do we do longer usage documentation? README can get a bit big
- Logo? Images? Icon? README banner?
- API docs

## 💡 Ideas & Experiments
Potential quality-of-life features:

- split out and depend on a basic CLI module
- split out and depend on (dev-only) a make_script CLI
- split out and depend on (dev-only) a list-project CLI
- split out and depend on (dev-only) a pytest multi-target plugin
- publish to PyPI, NPM, PACKAGIST, others?

> See [REJECTED.md](REJECTED.md) for experiments and ideas that were explored but intentionally not pursued.

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-aNOAI</a></sub>
</p>
