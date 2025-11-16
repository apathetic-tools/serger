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
- config setting for the main
- can we make the main() detection smarter?
- config setting for main
- tie the import mode defaults to the stitch mode
- Module actions glob pattern support: Phase 1 (simple wildcards in convenience dict)
- Module actions glob pattern support: Phase 2 (globs in list format)
- Module actions glob pattern support: Phase 3 (advanced patterns with multiple wildcards and named captures)
- package can likely be resolved in single-builds. and in multi builds if not user provided we probably raised an error so we only move forward if it was provided.
- evaluate the other NotRequired fields in resolved typedict to see if they are truly still optional or can be resolved or errored out before then.
- how do we store the intermitent module trees? the "source" and "shim" trees? do we map tree back to the original file module where we can find it?
- can make trully minimal builds using pyproject.toml, when not to?
- can make trully minimal builds when there is a src/ directory with only one package, when not to?

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- How can we report what we comment tool ignore, in src and in tests?
- Organize tests in classes? or separate files?
- split large test files
- is checking py_compiles overkill? should we also run it against the installed mode not just singlefile?
- make sure for our config_types TypeDicts, we have a make_ factory in tests/utils that has sane defaults for all fields it can and named parameters for overriding each. that way a test can focus on just overiding the values it cares about. make sure our tests use the factories.
- can we split integration into ones that check serger output and those that don't? what do our integration tests that only run in one runtime_mode do?
- review all docs before v1.0
- review all tests before v1.0
- review all debug/trace statements before v1.0

## 🧑‍💻 Development
- implement stich mode: exec (see [docs/example_isolated_stiching.md](docs/example_isolated_stiching.md))
- implement stich mode: class (requires working assign import mode)
- Evaluate ignores and determine if we can fix them instead of ignore them
- can we pull out common CLI elements with pocket-build into a single toplevel module?
- command to do common tasks based on reddit advice for dealing with AI.
- if we moved the sys.modules shims as we went, would that allow us to do imports as long as the order was correct?
- should more of our config settings be available to be set via ENV?
- can we parse the AST just once and store everything we need to know for later?
- might be able to optimize/cache package detection based on previous includes
- now that we have a module_base, we can probably "Follow the imports" and add includes as we find them, they only need to give us the first include

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
