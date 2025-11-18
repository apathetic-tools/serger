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
- should we have parity of the CLI with the config file features?
- `--self-update` — update serger itself
- `--no-update-check` — skip automatic update check



## ⚙️ Config File Enhancements

- Add key to disable update checks directly in config
- Provide a JSON Schema for validation and autocomplete
- Module-level configuration (metadata, headers)
- Module actions glob pattern support: Phase 1 (simple wildcards in convenience dict)
- Module actions glob pattern support: Phase 2 (globs in list format)
- Module actions glob pattern support: Phase 3 (advanced patterns with multiple wildcards and named captures)
- how do we store the intermitent module trees? the "source" and "shim" trees? do we map tree back to the original file module where we can find it?
- stitch mode that prefixes symbols with the package name to keep it flat and avoid collisions. (would need to set up unprefixed import vars before every module)
- interactive mode to solve problems as they come up and make a config
- we need a way to specify --details, opposite of --quiet, for more INFO messages or less. (maybe a DETAILS and MINIMAL levels above and bellow INFO)
- add a rename action that only lets you rename the last node?


## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- Organize tests in classes? or separate files?
- split large test files
- split tests into logical sections further (instead of subfolders)
- review all tests before v1.0
- review all debug/trace statements before v1.0

## 🧑‍💻 Development
- implement stich mode: exec (see [docs/example_isolated_stiching.md](docs/example_isolated_stiching.md))
- implement stich mode: class (requires working assign import mode)
- if we moved the sys.modules shims as we went, would that allow us to do imports as long as the order was correct?
- might be able to optimize/cache package detection based on previous includes
- now that we have a module_base, we can probably "Follow the imports" and add includes as we find them, they only need to give us the first include
- improve output so we are "quieter" when the user told us something, but make sure to mention when we made an assumption on behalf of the user
- review all details/minimal statements before v1.0


## 🚀 Deployment
- Deploy action when I tag a release should create a release and attach it to the tagged release.

## 🔌 API

## 📚 Documentation
- Do we want a way to dump the schema for documentation purposes?
- Where do we document the structure of the project? What do we document inside it vs here?
- Where do we do longer usage documentation? README can get a bit big
- Logo? Images? Icon? README banner?
- API docs
- review all docs before v1.0

## AI tooling
- command to do common tasks based on reddit advice for dealing with AI.
- split out the sync ai command to a separate package, could include standard rules

## 💡 Ideas & Experiments
Potential quality-of-life features:

- split out and depend on (dev-only) a make_script CLI
- split out and depend on (dev-only) a list-project CLI
- split out and depend on (dev-only) a pytest multi-target plugin
- publish to PyPI, NPM, PACKAGIST, others?

## Other Tool Ideas

### CLI library
- split out and depend on a basic CLI module
- can we pull out common CLI elements with pocket-build into a single toplevel module? (that would include includes, excludes) we're not longer compatable on the builds vs single-build

### Type Ignore Comments
- How can we report what we comment tool ignore (e.g. #noqa:), in src and in tests?
- Evaluate ignores and determine if we can fix them instead of ignore them

> See [REJECTED.md](REJECTED.md) for experiments and ideas that were explored but intentionally not pursued.

---

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-aNOAI</a></sub>
</p>
