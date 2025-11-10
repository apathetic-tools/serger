<!-- Roadmap.md -->
# 🧭 Roadmap

## Stitching Refactoring (Current Focus)

**Important Clarification**: Serger is **purely a Python module stitcher** - it combines multiple source files into a single executable script. File copying/building is pocket-build's responsibility, not serger's.

### Phases

**Phase 1: Extract stitching utilities** ✅ COMPLETE
- Extracted helpers from `src/make_script.py` into `src/serger/stitch.py`
- Utilities: `split_imports()`, `compute_module_order()`, `detect_name_collisions()`, `verify_no_broken_imports()`, etc.
- Full test coverage in `tests/5_core/test_*.py`
- Exception handling refactored: RuntimeError instead of SystemExit

**Phase 2: Add config structure for stitching** ✅ COMPLETE
- Extended `BuildConfig` and `BuildConfigResolved` TypedDict types with optional `package` and `order` fields
- Reused existing pocket-build `include`, `exclude`, and `out` fields (no new parallel structures)
- Created `.serger.jsonc` with serger's self-hosting build configuration (package, module order, includes, excludes, output path)

**Phase 3: Implement orchestration function** ✅ COMPLETE
- Created `stitch_modules(config)` orchestration function in `src/serger/stitch.py` (lines 512-640)
- Refactored into focused helpers: `_collect_modules()` and `_build_final_script()` for maintainability
- Coordinates all stitching utilities in proper sequence: validation → collection → collision detection → assembly → verification → output
- Handles metadata embedding (version, commit, build date), import shims, and comprehensive logging
- Full type safety with proper guards and casts; passes all linting and type checkers
- **Comprehensive test coverage**: 49 new tests across 3 test files:
  - `test_stitch_modules.py` (37 tests): validation, basic stitching, collisions, metadata, shims, output
  - `test_priv__collect_modules.py` (13 tests): module collection, imports, ordering, edge cases
  - `test_priv__build_final_script.py` (17 tests): script assembly, metadata, imports, shims, docstrings
  - All tests passing (561 total), full code quality compliance

**Phase 4-7: CLI integration and cleanup** ⏳ PENDING
- Integrate stitching into main CLI (load `.serger.jsonc` and invoke `stitch_modules()`)
- Remove copy-based `build.py` (belongs in pocket-build)
- Replace `dev/make_script.py` with config-driven approach
- Update selftest with stitch validation

### Key Points

- **One responsibility**: Stitching only, no file copying
- **Config-driven**: Eliminate hardcoded module order
- **Self-hosting**: Serger builds itself using its own config
- **Backward compatible**: Existing utilities unchanged
- **Well-tested**: Unit, integration, and E2E coverage

### Future (Post-Phase 7)

- run ruff on resulting script if available
- how does pyproject.toml factor into it?
- Auto-discovery of module order via topological sort
- Module-level configuration (metadata, headers)
- Multi-package stitching support
- Incremental stitching with dependency caching

---

# Once Stitch refactor into pocket-build CLI is complete:

## TODO

- have it's own configuration file
- don't repeat files
- allow you to specify a file for order, then include the rest of the dir
- builds without a version should have timestamp

---

# Once the TODO are done:

## 🧰 CLI Parameters
Planned command-line flags for future releases:

- `--self-update` — update serger itself
- `--no-update-check` — skip automatic update check

## ⚙️ Config File Enhancements

- Add key to disable update checks directly in config
- Provide a JSON Schema for validation and autocomplete

## 🧩 Joiner Scripts (Build System)
Exploring bundling options for generating the single-file release:

- zip file: zipapp / shiv / pyinstaller --onefile

## 🧪 Tests
- Flesh out tests once we have ported make_script.py into the CLI framework
- Update selftest to stitch a file

## 🧑‍💻 Development

## deployment
  - Deploy action when I tag a release should create a release and attach it to the tagged release.
  
## API
  - put utils into a submodule (as long as our sticher can handle it)
  - can utils/config be made into a single submodule? how does that play with the bundler?
  - do we want a way to dump the schema for documentation purposes?

## Documentation
  - where do we document the structure of the project? what do we document inside it vs here?
  - where do we do longer usage documentation? README can get a bit big
  - logo? images? icon? readme banner?
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
