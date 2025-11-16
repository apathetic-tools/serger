<!-- DECISIONS.md -->
# DECISIONS.md

A record of major design and implementation choices in **serger** — what was considered, what was chosen, and why.

Each decision:

- Is **atomic** — focused on one clear choice.  
- Is **rationale-driven** — the “why” matters more than the “what.”  
- Should be written as if explaining it to your future self — concise, readable, and honest.  
- Includes **Context**, **Options Considered**, **Decision**, and **Consequences**.  

For formatting guidelines, see the [DECISIONS.md Style Guide](./DECISIONS_STYLE_GUIDE.md).

---

## 🚀 Aggressively Allow Defaults and Auto-Detection for Zero-Config Usage
<a id="dec14"></a>*DEC 14 — 2025-11-16*

### Context

Serger should "just work" when someone downloads it and runs it without any configuration files or CLI arguments. The goal is to enable a seamless, **zero-configuration experience** where users can immediately generate a stitched script from their Python package without needing to understand Serger's configuration system or provide explicit paths, package names, or output locations.

When configuration is necessary, it should require the **least config possible** — only specifying what differs from sensible defaults, not re-stating everything explicitly.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Aggressive defaults and auto-detection** | ✅ Zero-configuration experience<br>✅ Lower barrier to entry<br>✅ Works immediately after installation<br>✅ Encourages exploration and adoption | ⚠️ May produce unexpected output if assumptions are wrong<br>⚠️ Less explicit control for advanced users |
| **Require explicit configuration** | ✅ Clear, explicit behavior<br>✅ No ambiguity about what will happen<br>✅ Forces users to understand the tool | ❌ High barrier to entry<br>❌ Requires learning configuration format before first use<br>❌ Slower initial adoption |
| **Minimal defaults with warnings** | ✅ Safe defaults<br>✅ Warns users about assumptions | ⚠️ Still requires user interaction<br>⚠️ Interrupts the "just works" experience |

### Decision

**Aggressively allow defaults and auto-detection** to enable **zero-configuration usage** and **minimal configuration** when needed. When no config file or CLI arguments are provided, Serger should:

- **Auto-detect packages** from the project structure (scanning `src/` and other common directories)
- **Auto-detect source files** using sensible defaults (e.g., `src/**/*.py`)
- **Use safe default output paths** — specifically, `dist/<package>.py` is considered a safe default output location
- **Auto-detect package names** from directory structure or `pyproject.toml`
- **Apply sensible defaults** for all configuration options (stitch mode, import handling, post-processing, etc.)

The output path `dist/<package>.py` is considered safe because:
- The `dist/` directory is a standard Python convention for distribution artifacts
- It's unlikely to conflict with source code
- It's a clear, predictable location that users can easily find and understand
- It aligns with common Python packaging workflows

This approach prioritizes **immediate usability** over **explicit control**. When configuration is needed, users should only specify what differs from defaults — the **least config possible**. Advanced users can always override defaults with configuration files or CLI arguments, but new users should be able to run Serger and get useful output immediately, and users who need customization should only need to configure what's different.


<br/><br/>

---

---

<br/><br/>

## 🔧 Choose Post-Processing Tools: Ruff, Black, and isort
<a id="dec13"></a>*DEC 13 — 2025-11-11*

### Context

After stitching source files into a single script, Serger needs to ensure the output meets quality standards — static checking, formatting, and import organization. The tool should support a flexible, priority-based system where users can configure which tools run in which order, with fallbacks when preferred tools aren't available.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Ruff only** | ✅ Single tool for all categories<br>✅ Extremely fast<br>✅ Unified configuration | ⚠️ Less flexibility for teams with existing tool preferences<br>⚠️ Newer tool, some teams prefer established alternatives |
| **Ruff + Black + isort** | ✅ Ruff as primary (fast, modern)<br>✅ Black as formatting fallback (widely adopted)<br>✅ isort as import fallback (mature, configurable)<br>✅ Supports teams with existing toolchains | ⚠️ Multiple tools to potentially install<br>⚠️ Slight configuration complexity |
| **Black + isort only** | ✅ Established, widely-used tools<br>✅ No newer dependencies | ❌ Slower than Ruff<br>❌ Two separate tools instead of one unified solution |
| **No post-processing** | ✅ Simplest implementation<br>✅ No external dependencies | ❌ Users must manually format/check output<br>❌ Inconsistent output quality |

### Decision

Support **Ruff as the primary tool** for all three categories (static checking, formatting, and import sorting), with **Black** and **isort** as fallback options.

The default configuration prioritizes Ruff for its speed and unified approach, but allows teams with existing Black or isort workflows to use those tools instead. This provides:

- **Fast defaults** — Ruff handles all three categories efficiently
- **Flexibility** — Users can override priorities to match their existing toolchains
- **Graceful degradation** — If Ruff isn't available, Black and isort can step in

The three categories (`static_checker`, `formatter`, `import_sorter`) run in order, and within each category, tools are tried in priority order until one succeeds. This ensures consistent output while respecting user preferences and tool availability.

<br/><br/>

---

---

<br/><br/>

## 📄 Only Support `pyproject.toml` for Project Metadata
<a id="dec12"></a>*DEC 12 — 2025-11-11*

### Context

Serger needs to extract project metadata (name, version, description, license) for embedding in stitched scripts. Historically, Python projects used `setup.py` and `setup.cfg` for this information, but modern Python packaging has standardized on `pyproject.toml` (PEP 621).

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Only `pyproject.toml`** | ✅ Modern standard (PEP 621)<br>✅ Single source of truth<br>✅ Widely adopted<br>✅ Simpler implementation | ⚠️ Doesn't support legacy projects |
| **Support `setup.py` and `setup.cfg`** | ✅ Backward compatible with older projects | ❌ Legacy formats being phased out<br>❌ More complex parsing logic<br>❌ Multiple sources of truth |
| **Support all formats** | ✅ Maximum compatibility | ❌ Significant implementation complexity<br>❌ Maintenance burden<br>❌ Conflicts when multiple formats exist |

### Decision

**Only support `pyproject.toml`** for extracting project metadata.

This aligns with modern Python packaging standards and keeps the implementation focused. Projects using legacy formats can migrate to `pyproject.toml` or manually specify metadata in their Serger config.

<br/><br/>

---
---

<br/><br/>

## 🪵 Adopt Standard Library `logging`
<a id="dec11"></a>*DEC 11 — 2025-10-15 → revised 2025-10-31*  

### Context  

Early in development, the project required a **consistent and colorized logging system** that worked seamlessly in both modular and single-file builds.  
At the time, the built-in Python `logging` module seemed overkill for such a small utility — especially since the tool needed lightweight log-level control and minimal setup.  
We initially built a **custom logger** to provide:  

- Compact, dependency-free logging.  
- Inline color formatting for terminals.  
- Simpler test injection and patching for trace output.  

This approach fit the project's early ethos of *“small, inspectable, and standalone.”*  

### Options Considered  

| Option | Pros | Cons |
|--------|------|------|
| **Custom lightweight logger** | ✅ Fully under our control<br>✅ Compact and easily embedded<br>✅ Works identically in single-file builds | ⚠️ Duplicates standard functionality<br>⚠️ Harder to test and mock<br>⚠️ Configuration drift between modules |
| **Standard Library `logging`** | ✅ Mature and battle-tested<br>✅ Configurable handlers, filters, and levels<br>✅ Works natively with external libraries<br>✅ Simple integration with pytest and CLI flags | ⚠️ Significantly more verbose setup for color and formatting |
| **Third-party libraries (e.g. `loguru`, `rich.logging`)** | ✅ Rich formatting and features out-of-the-box | ❌ Adds runtime dependencies<br>❌ Conflicts with minimalism goal |

### Decision — *2025-10-15*  

Implement a **custom, lightweight logger** tailored for the project.  
It would provide clear output, colorized levels, and simple hooks for tracing (`TRACE`) without bringing in external dependencies or complex handler hierarchies.  
This custom module fit our goals of **portability** and **transparency**, keeping the tool’s behavior explicit and easy to inspect.  

### Follow-up and Evolution (*2025-10-31*)

As the codebase grew, the in-house logger **expanded significantly** — gaining configuration flags, test-time injection, and shims for different runtime modes.  
It became increasingly **difficult to test, maintain, and integrate** with third-party tooling.  

We also realized (belatedly) that the **standard `logging` module already supports** most of what we built manually — including level control, handler injection, and structured message formatting — all without external dependencies.  

The custom logger was therefore deprecated and removed, and the project migrated fully to **Python’s built-in `logging`** system.  



<br/><br/>

---
---

<br/><br/>

## ⚙️ Adopt a Three-Tier Distribution Strategy
<a id="dec10"></a>*DEC 10 — 2025-10-11*  

### Context 

As the early ad-hoc merger script evolved into a tested module, we want to ensure the project remains easy to distribute in forms that best suits different users.  

### Options Considered

| Option | Pros | Cons | Tools
|--------|------|------|------|
| **PyPI module (default)** | ✅ Easy to maintain and install<br>✅ Supports imports and APIs | ❌ Requires installation and internet | [`poetry`](https://python-poetry.org/), [`pip`](https://pypi.org/project/pip/) |
| **Single-file script** | ✅ No install step<br>✅ Human-readable source<br>✅ Ideal for quick CLI use | ❌ Not importable<br>❌ Harder to maintain merger logic | [`serger`](https://github.com/apathetic-tools/serger) |
| **Zipped module (`.pyz`)** | ✅ Bundled, portable archive<br>✅ Maintains import semantics | ⚠️ Requires unzip for source<br>⚠️ Slight startup overhead | [`zipapp`](https://docs.python.org/3/library/zipapp.html), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |
| **Executable bundlers** | ✅ Fully portable binaries<br>✅ No Python install required | ❌ Platform-specific<br>❌ Not source-transparent  | [`PyInstaller`](https://pyinstaller.org/en/stable/), [`shiv`](https://pypi.org/project/shiv/), [`pex`](https://pypi.org/project/pex/) |


---

### Decision

Adopt a **three-tier distribution model**:  

1. **PyPI package** — the canonical importable module with semantic versioning guarantees.  
2. **Single-file script** — a CLI build based on `ast` import parsing.  
3. **Zipped module (`.pyz`)** — optional for future releases and easy to produce.  

Each tier serves different users while sharing the same tested, modular codebase.  

This does not rule out an executable bundle in the future.


<br/><br/>

---
---

<br/><br/>


## 🧪 Adopt `Pytest` for Testing  
<a id="dec09"></a>*DEC 09 — 2025-10-10*  

### Context

The project required a lightweight, expressive testing framework compatible with modern Python and CI environments.  
Testing should be easy to write, discover, and extend — without verbose boilerplate or heavy configuration.  
The priority was to keep tests readable while supporting fixtures, parametrization, and integration with tools like coverage and tox.

### Options Considered

| Tool | Pros | Cons |
|------|------|------|
| **[`Pytest`](https://docs.pytest.org/)** | ✅ Simple test discovery (`test_*.py`)<br>✅ Rich fixtures and parametrization<br>✅ Integrates with CI and coverage tools<br>✅ Large ecosystem and community | ⚠️ Implicit magic can obscure behavior for beginners |
| **`unittest` (stdlib)** | ✅ Built into Python<br>✅ Familiar xUnit style | ❌ Verbose boilerplate<br>❌ Weak fixture system<br>❌ Slower iteration and less readable output |


### Decision

Adopt **Pytest** as the primary testing framework.  
It provides clean syntax, automatic discovery, and a thriving ecosystem — making it ideal for both quick unit tests and full integration suites.  
Pytest’s concise, declarative style aligns with the project’s principle of *clarity over ceremony*, enabling contributors to write and run tests effortlessly across all supported Python versions.


<br/><br/>

---
---

<br/><br/>


## 🔍 Adopt `Pylance` and `MyPy` for Type Checking  
<a id="dec08"></a>*DEC 08 — 2025-10-10*  

### Context

Static typing improves maintainability and clarity across the codebase, but Python’s ecosystem offers multiple overlapping tools.  
The goal was to balance **developer ergonomics** in VS Code with **strict, automated checks** in CI.  
We wanted instant feedback during development and deeper, slower analysis during builds — without fragmenting the configuration.

### Options Considered

| Tool | Pros | Cons |
|------|------|------|
| **[`Pylance`](https://github.com/microsoft/pylance-release)** | ✅ Deep integration with VS Code<br>✅ Fast, incremental type checking<br>✅ Excellent in-editor inference and documentation<br>✅ Minimal configuration (uses `pyrightconfig.json` or `pyproject.toml`) | ❌ IDE-only — cannot run in CI<br>❌ Limited control over advanced typing rules |
| **[`Pyright`](https://github.com/microsoft/pyright)** | ✅ CLI equivalent of Pylance<br>✅ Fast and scriptable for CI | ⚠️ Less flexible than MyPy for complex type logic |
| **[`MyPy`](https://github.com/python/mypy)** | ✅ Mature, standards-based type checker<br>✅ Detects deeper type inconsistencies<br>✅ Integrates easily into CI workflows | ⚠️ Slower than Pyright<br>⚠️ Sometimes stricter or inconsistent with Pylance behavior |
| **No static checking** | ✅ Simplifies setup | ❌ No type enforcement; increased maintenance burden |

### Decision

Adopt **Pylance** as the default IDE type checker for developers using VS Code, and **MyPy** as the canonical CI type checker.  
Pylance offers immediate, contextual feedback during development through its deep VS Code integration, while MyPy provides comprehensive type analysis in automated checks.  

This dual setup ensures fast iteration locally and rigorous verification in CI — complementing Ruff’s linting and formatting without overlapping responsibilities.

### Future Consideration

Future builds may experiment with **`pyright` CLI** to align IDE and CI checks under a single configuration, but for now, **Pylance in the editor** and **MyPy in CI** provide the best balance of speed, coverage, and reliability.


<br/><br/>

---
---

<br/><br/>


## 🪶 Adopt `editorconfig` and `Ruff` for Linting and Formatting  
<a id="dec07"></a>*DEC 07 — 2025-10-10 → revised 2025-10-30*  

### Context

The project needed a **consistent, automated style and linting toolchain** to enforce quality without slowing down iteration.  
Python’s ecosystem offers several specialized tools (`black`, `isort`, `flake8`, `mypy`, etc.), but managing them separately increases setup friction and configuration sprawl.  
The goal was to find a **fast, unified tool** that covers linting, formatting, and import management from a single configuration.


### Options Considered

| Tool | Pros | Cons |
|------|------|------|
| **[`Ruff`](https://github.com/astral-sh/ruff)** | ✅ Extremely fast (Rust-based)<br>✅ Replaces multiple tools (lint, format, import sort)<br>✅ Single configuration in `pyproject.toml`<br>✅ Compatible with Black-style formatting | ⚠️ Still evolving rapidly |
| **[`Black`](https://github.com/psf/black)** | ✅ Widely adopted<br>✅ Consistent formatting standard | ❌ Format-only — requires separate tools for linting and imports |
| **[`isort`](https://pycqa.github.io/isort/)** | ✅ Excellent import sorter<br>✅ Highly configurable | ❌ Separate config and step<br>❌ Slower and redundant when used with Ruff |
| **[`.editorconfig`](https://editorconfig.org/)** | ✅ Supported by most editors<br>✅ Defines consistent indentation, EOLs, and encoding<br>✅ Works across languages | ❌ Limited to basic formatting rules |

### Decision

Adopt **Ruff** as the unified linting and formatting tool, complemented by **EditorConfig** for cross-editor baseline consistency.
Ruff’s **speed**, **all-in-one scope**, and **`pyproject.toml` integration** reduce the need for multiple Python-specific tools, while EditorConfig ensures **consistent indentation, encoding, and newline behavior** in any environment.  

Together, they provide a lightweight, editor-agnostic foundation that enforces uniform style without excess configuration — aligning with the project’s “minimal moving parts” principle.

### Follow-up and Evolution (2025-10-11 → 2025-10-30)

For a brief period, **isort** was integrated alongside Ruff to handle complex import merging, as the team was unaware that Ruff’s configuration already supported equivalent sorting behavior.  
After confirming Ruff’s import management features, **isort was removed**, consolidating all style and linting functions under Ruff alone.



<br/><br/>

---
---

<br/><br/>


## 📦 Choose `Poetry` for Dependency and Environment Management  
<a id="dec06"></a>*DEC 06 — 2025-10-10*  

### Context

The project needs a **single-source, reproducible setup** covering dependency management, packaging, and development workflows.  
The goal is to reduce moving parts — **one configuration, one lockfile, one entrypoint.**

### Options Considered

| Tool | Pros | Cons |
|------|------|------|
| **[`Poetry`](https://python-poetry.org/)** | ✅ Unified `pyproject.toml` for dependencies and metadata<br>✅ Built-in lockfile for reproducible builds<br>✅ Manages virtual environments automatically<br>✅ Extensible with plugins (e.g. [`poethepoet`](https://github.com/nat-n/poethepoet)) for task automation | ⚠️ Slightly heavier CLI<br>⚠️ Requires learning its workflow |
| **`pip` + `requirements.txt`** | ✅ Ubiquitous and simple<br>✅ Works with system Python or virtualenv | ❌ No lockfile by default<br>❌ Fragmented setup (requires separate tools for packaging and scripts)<br>❌ Harder to track metadata and extras |
| **`pip-tools`** | ✅ Adds lockfile support to `pip` | ⚠️ Partial overlap; still requires setup scripts |
| **Manual `venv` + Makefile** | ✅ Transparent and minimal | ❌ Scattered configuration<br>❌ Manual sync and version drift |

### Decision

Adopt **Poetry** as the project’s canonical environment and dependency manager.  
It provides a **batteries-included workflow** — unified configuration (`pyproject.toml`), reproducible installs (`poetry.lock`), isolated environments, and task automation via the `poethepoet` plugin instead of maintaining Makefiles.  

This mirrors the **familiar ergonomics of `package.json` + `pnpm`** for developers coming from JavaScript ecosystems while preserving full Python portability.


<br/><br/>

---
---

<br/><br/>


## 🤝 Adopt `Contributor Covenant 3.0` as Code of Conduct  
<a id="dec05"></a>*DEC 05 — 2025-10-10*  

### Context

The project needed a **clear, inclusive standard of behavior** for contributors and maintainers.  
As the Apathetic Tools ecosystem grows, shared norms for collaboration, respect, and conflict resolution become essential — especially for open projects that welcome community participation.  
Rather than inventing custom language, the team wanted a **widely recognized, well-maintained template** that could be easily understood, translated, and enforced.

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Contributor Covenant 3.0** | ✅ Industry-standard and widely adopted<br>✅ Legally sound and CC BY-SA 4.0 licensed<br>✅ Clearly defines expectations, reporting, and enforcement<br>✅ Includes inclusive language and repair-focused approach | ⚠️ Template language can feel formal or corporate |
| **Custom in-house code** | ✅ Tailored tone and structure | ❌ Risk of omissions or unclear enforcement<br>❌ Higher maintenance burden |
| **No formal code** | ✅ Less administrative work | ❌ Unclear expectations<br>❌ Difficult to moderate conflicts fairly |

### Decision

Adopt the **Contributor Covenant 3.0** as the foundation for the project’s `CODE_OF_CONDUCT.md`, adapted for the Apathetic Tools community.  
This provides a **consistent, transparent behavioral framework** while avoiding the overhead of authoring and maintaining a custom code.  
It defines reporting, enforcement, and repair processes clearly, reinforcing the community’s emphasis on accountability and respect.  

This version is lightly customized with local contact details and references to community moderation procedures, maintaining alignment with upstream guidance.


<br/><br/>

---
---

<br/><br/>


## 🧭 Target `Python` Version `3.10`
<a id="dec04"></a>*DEC 04 — 2025-10-10*  


### Context

Following the choice of Python *(see [DEC 03](#dec03))*, this project must define a minimum supported version balancing modern features, CI stability, and broad usability.  
The goal is to stay current without excluding common environments.

### Options Considered

The latest Python version is *3.14*.

| Version | Pros | Cons |
|---------|------|------|
| **3.8+** | ✅ Works on older systems | ❌ Lacks modern typing (`\|`, `match`, `typing.Self`) and adds maintenance overhead |
| **3.10+**  | ✅ Matches Ubuntu 22.04 LTS (baseline CI)<br>✅ Includes modern syntax and typing features | ⚠️ Slightly narrower audience but covers all active LTS platforms
| **3.12+** | ✅ Latest stdlib and type system | ❌ Too new; excludes many CI and production environments |

### Platform Baselines
Windows WSL typically runs Ubuntu 22.04 or 24.04 LTS.

| Platform | Default Python | Notes |
|-----------|----------------|-------|
| Ubuntu 22.04 LTS | 3.10 | Minimum baseline |
| Ubuntu 24.04 LTS | 3.12 | Current CI default |
| macOS / Windows | 3.12 | User-installed or Store LTS |
| GitHub Actions `ubuntu-latest` | 3.10 → 3.12 | Transition period coverage |

### Python Versions

| Version | Status | Released | EOL |
|---------|--------|----------|-----|
| 3.14 | bugfix | 2025-10 | 2030-10 |
| 3.13 | bugfix | 2024-10 | 2029-10 |
| 3.12 | security | 2023-10 | 2028-10 |
| 3.11 | security | 2022-10 | 2027-10 |
| **3.10** | security | 2021-10 | 2026-10 |
| 3.9 | security | 2020-10 | 2025-10 |
| 3.8 | end of life | 2019-10-14 | 2024-10-07 |

### Decision

Target **Python 3.10 and newer** as the supported baseline.  
This version provides modern typing and syntax while staying compatible with Ubuntu 22.04 LTS — the lowest common denominator across CI and production systems.


<br/><br/>

---
---

<br/><br/>


## 🧭 Choose `Python` as the Implementation Language  
<a id="dec03"></a>*DEC 03 — 2025-10-09*  


### Context

The project aims to be a **lightweight, dependency-free build tool** that runs anywhere — Linux, macOS, Windows, or CI — without setup or compilation.  
Compiled languages (e.g. Go, Rust) would require distributing multiple binaries and would prevent in-place auditing and modification.
Python 3, by contrast, is preinstalled or easily available on all major platforms, balancing universality and maintainability.

---

### Options Considered

| Language | Pros | Cons |
|-----------|------|------|
| **Python** | ✅ Widely available<br>✅ No compile step<br>✅ Readable and introspectable  | ⚠️ Slower execution<br>⚠️ Limited single-file packaging |
| **JavaScript / Node.js** | ✅ Familiar to web developers | ❌ Not standard on all OSes<br>❌ Frequent version churn |
| **Bash** | ✅ Ubiquitous | ❌ Fragile for complex logic

### Decision

Implement the project in **Python 3**, targeting **Python 3.10+** *(see [DEC 04](#dec04))*.  
Python provides **zero-dependency execution**, **cross-platform reach**, and **transparent, editable source code**, aligning with the project’s principle of *clarity over complexity*.  
 It allows users to run the tool immediately and understand it fully.

The performance trade-off compared to compiled binaries is acceptable for small workloads.  
Future distributions may include `.pyz` or bundled binary releases as the project evolves.


<br/><br/>

---
---

<br/><br/>


## ⚖️ Choose `MIT-aNOAI` License
<a id="dec02"></a>*DEC 02 — 2025-10-09*  

### Context

This project is meant to be open, modifiable, and educational — a tool for human developers.  
The ethics and legality of AI dataset collection are still evolving, and no reliable system for consent or attribution yet exists.

The project uses AI tools but distinguishes between **using AI** and **being used by AI** without consent.

### Options Considered

- **MIT License (standard)** — simple and permissive, but allows unrestricted AI scraping.
- **MIT + “No-AI Use” rider (MIT-aNOAI)** — preserves openness while prohibiting dataset inclusion or model training; untested legally and not OSI-certified.

### Decision

Adopt the **MIT-aNOAI license** — the standard MIT license plus an explicit clause banning AI/ML training or dataset inclusion.
This keeps the project open for human collaboration while defining clear ethical boundaries.

While this may deter adopters requiring OSI-certified licenses, it can later be dual-licensed if consent-based frameworks emerge.

### Ethical Consideration

AI helped create this project but does not own it.  
The license asserts consent as a prerequisite for training use — a small boundary while the wider ecosystem matures.


<br/><br/>

---
---

<br/><br/>



## 🤖 Use `AI Assistance` for Documentation and Development  
<a id="dec01"></a>*DEC 01 — 2025-10-09*


### Context

This project started as a small internal tool. Expanding it for public release required more documentation, CLI scaffolding, and testing than available time allowed.

AI tools (notably ChatGPT) offered a practical way to draft and refine code and documentation quickly, allowing maintainers to focus on design and correctness instead of boilerplate.

### Options Considered

- **Manual authoring** — complete control but slow and repetitive.
- **Static generators (pdoc, Sphinx)** — good for APIs, poor for narrative docs.
- **AI-assisted drafting** — fast, flexible, and guided by human review.

### Decision

Use **AI-assisted authoring** (e.g. ChatGPT) for documentation and boilerplate generation, with final edits and review by maintainers.  
This balances speed and quality with limited human resources. Effort can shift from writing boilerplate to improving design and clarity.  

AI use is disclosed in headers and footers as appropriate.

### Ethical Note

AI acts as a **paid assistant**, not a data harvester.  
Its role is pragmatic and transparent — used within clear limits while the ecosystem matures.


<br/><br/>

---
---

<br/><br/>

_Written following the [Apathetic Decisions Style v1](https://apathetic-recipes.github.io/decisions-md/v1) and [ADR](https://adr.github.io/), optimized for small, evolving projects._  
_This document records **why** we build things the way we do — not just **what** we built._

> ✨ *AI was used to help draft language, formatting, and code — plus we just love em dashes.*

<p align="center">
  <sub>😐 <a href="https://apathetic-tools.github.io/">Apathetic Tools</a> © <a href="./LICENSE">MIT-aNOAI</a></sub>
</p>
