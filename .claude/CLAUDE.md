# Build Requirements

## Build Reproducibility and Determinism

Serger builds must be **reproducible, deterministic, and idempotent**. This means:

- **Reproducible**: Running the same build configuration multiple times produces identical output
- **Deterministic**: Build output does not depend on iteration order of unordered collections (sets, dicts without explicit ordering)
- **Idempotent**: Running a build multiple times with the same inputs produces the same result

### Requirements

1. **Collection Iteration Order**
   - **Always sort** before iterating over collections that affect output:
     - Sets: `for item in sorted(my_set):`
     - Dict keys/values/items: `for key, value in sorted(my_dict.items()):`
     - Any collection where iteration order affects the final build output
   - **When sorting is redundant**: If a list is already sorted and you only perform operations that preserve sorted order (e.g., deleting items, filtering), you don't need to sort again before iterating
   - This applies to:
     - Module ordering
     - Import collection and ordering
     - Dependency resolution
     - Symbol extraction and collision detection
     - Package detection
     - Any other collection that ends up in the final output

2. **File System Ordering**
   - File collections from glob patterns or directory walks must be sorted
   - Example: `collect_included_files()` already returns `sorted(filtered)` to ensure deterministic file ordering

3. **Dependency Graph Ordering**
   - Dependency graphs (e.g., for module ordering via topological sort) provide a **partial order**
   - The graph determines which modules must come before others (dependency constraints)
   - When multiple valid orderings exist (modules with no dependencies between them), sorting is used to break ties and ensure determinism
   - The dependency graph (`deps`) must be built with sorted file paths to ensure consistent dict insertion order
   - This ensures `graphlib.TopologicalSorter.static_order()` produces deterministic results even when there are multiple valid topological orderings

4. **No Time-Dependent Output**
   - Build timestamps in metadata are acceptable (they're explicitly time-dependent)
   - But the structure and content of the stitched code must not depend on build time or execution order

### Implementation Guidelines

When working with collections that affect build output:

```python
# ❌ BAD: Non-deterministic iteration
for pkg in detected_packages:  # set iteration order is undefined
    # process package

# ✅ GOOD: Deterministic iteration
for pkg in sorted(detected_packages):
    # process package
```

```python
# ❌ BAD: Dict iteration without sorting
for mod_name, source in module_sources.items():
    # process module

# ✅ GOOD: Deterministic iteration
for mod_name, source in sorted(module_sources.items()):
    # process module
```

**When sorting is redundant:**
```python
# ✅ GOOD: List already sorted, only deleting items preserves order
sorted_list = sorted(original_collection)
for item in sorted_list:
    if should_keep(item):
        process(item)
# Later iteration - still sorted, no need to sort again
for item in sorted_list:  # ✅ OK: still sorted after deletions
    process_remaining(item)

# ❌ BAD: Adding items without maintaining sort order
sorted_list = sorted(original_collection)
sorted_list.append(new_item)  # Breaks sorted order
for item in sorted_list:  # ❌ Need to sort again
    process(item)

# ✅ GOOD: If you can guarantee the list is still sorted
sorted_list = sorted(original_collection)
# Only operations that preserve order (delete, filter, slice)
filtered = [x for x in sorted_list if condition(x)]  # Still sorted
for item in filtered:  # ✅ OK: filtered list maintains sort order
    process(item)
```

**Dependency Graph Ordering:**
```python
# Dependency graphs provide partial ordering (A must come before B)
# But when multiple valid orderings exist, sorting ensures determinism

# ✅ GOOD: Build graph with sorted inputs for deterministic tie-breaking
# Note: file_paths is already sorted from collect_included_files()
# This ensures dict insertion order is deterministic, which makes
# topological sort deterministic even when multiple valid orderings exist
deps: dict[str, set[str]] = {
    file_to_module[fp]: set() for fp in file_paths  # already sorted
}
# Topological sort respects dependencies AND uses dict insertion order for ties
topo_modules = list(graphlib.TopologicalSorter(deps).static_order())
```

### Verification

- All tests must pass to verify correctness
- Builds should produce identical output when run multiple times with the same configuration
- When making changes that affect iteration order, verify that the output remains deterministic

# Code Quality

## Code Quality

Code quality standards apply to all code written by the user or AI. This includes:
- Project source code (`src/`)
- Development tooling (`dev/`)
- Test utilities (`tests/utils/`)
- Test files (`tests/`)

Code quality standards do **not** apply to:
- Externally sourced code
- Generated code that is never manually edited (e.g., `dist/`, `bin/`)

### Line Length

Maximum 88 characters per line (enforced by Ruff). **Always fix violations; never ignore them.**

**Principle**: Prioritize readability and comprehension over simply meeting the character limit.

#### Comments and Strings

Do not shorten comments or string literals to meet the line length limit if doing so significantly hurts readability, comprehension, or content. Instead, split them across multiple lines.

**Comments:**
- **Original** (too long): `# Validate user input before processing to ensure data integrity and prevent security vulnerabilities`
- **Good shortening**: `# Validate user input before processing` (preserves important context)
- **Bad shortening**: `# Validate input before processing` (removed "user" - important context lost)
- **Split long comments** across multiple lines (preferred for very long comments):
  ```python
  # Validate user input before processing to ensure data integrity
  # and prevent security vulnerabilities.
  ```

**String literals:**
- **Original** (too long): `msg = "Invalid user input provided in the form submission"`
- **Good shortening**: `msg = "Invalid user input"` (preserves important context)
- **Bad shortening**: `msg = "Invalid input"` (removed "user" - important context lost)
- **Split long strings** using parentheses for implicit line continuation (preferred for very long strings):
  ```python
  error_message = (
      "Failed to validate user input. Please check the format "
      "and ensure all required fields are present."
  )
  ```

#### Inline Statements

When inline statements (ternary expressions, comprehensions, generator expressions) exceed the line length limit, consider whether to wrap them across multiple lines or refactor into explicit if/else blocks or loops.

**Ternary expressions (conditional expressions):**
- **Original** (too long): `result = "success" if validate_user_input(data) and check_permissions(user) and process_data(data) else "failure"`
- **Wrapped** (split across lines):
  ```python
  result = (
      "success"
      if validate_user_input(data) and check_permissions(user) and process_data(data)
      else "failure"
  )
  ```
- **Refactored** (explicit if/else - preferred for complex conditions):
  ```python
  if validate_user_input(data) and check_permissions(user) and process_data(data):
      result = "success"
  else:
      result = "failure"
  ```

**Comprehensions (list/dict/set comprehensions):**
- **Original** (too long): `handler_types = {type(h).__name__ for h in typed_logger.handlers if isinstance(h, FileHandler) and h.level >= logging.WARNING}`
- **Wrapped** (split across lines):
  ```python
  handler_types = {
      type(h).__name__
      for h in typed_logger.handlers
      if isinstance(h, FileHandler) and h.level >= logging.WARNING
  }
  ```
- **Refactored** (explicit loop - preferred for complex logic):
  ```python
  handler_types = set()
  for h in typed_logger.handlers:
      if isinstance(h, FileHandler) and h.level >= logging.WARNING:
          handler_types.add(type(h).__name__)
  ```

**Generator expressions (in function calls):**
- **Original** (too long): `if all(i < len(list(p.parts)) and list(p.parts)[i] == part for p in resolved_paths[1:]):`
- **Wrapped** (split across lines):
  ```python
  if all(
      i < len(list(p.parts)) and list(p.parts)[i] == part
      for p in resolved_paths[1:]
  ):
  ```
- **Refactored** (explicit loop - preferred for complex conditions):
  ```python
  all_match = True
  for p in resolved_paths[1:]:
      if not (i < len(list(p.parts)) and list(p.parts)[i] == part):
          all_match = False
          break
  if all_match:
  ```

### Python Version

**Minimum version**: Python 3.10. All code must work on Python 3.10 and must never break when run there.

**Using newer features**: You may use features from Python 3.11+ as long as you can support them in both Python 3.10 and the newer version. Acceptable approaches include:
- `from __future__` imports
- `typing_extensions` for type hints
- Backported implementations of newer functionality

**Backporting strategy**: When a newer Python feature behaves differently or is unavailable in Python 3.10, **encapsulate the version differences in a function** so the calling code stays clean. The function handles the Python version detection internally and provides a consistent interface. Document the backport clearly, noting that it can be removed when the minimum Python version is bumped.

**Examples**:
- `fnmatch()` behaves differently in Python 3.10 vs 3.11+. We encapsulate this in `fnmatch_portable()` which uses `fnmatch()` in 3.11+ and a backported implementation for Python 3.10 (which may be slower but maintains compatibility). Calling code uses `fnmatch_portable()` without needing to know about version differences.
- TOML loading uses `load_toml()` which internally uses `tomllib` (built-in) in Python 3.11+ and the optional `tomli` library in Python 3.10. Calling code uses `load_toml()` without needing to handle version differences.

**Backport size limit**: Do not introduce a backport if the implementation would be large (more than roughly a few hundred lines of code).

**When to ask the developer**: If a modern feature exists that cannot be easily backported (due to size or complexity), **always ask the developer** for guidance on how to proceed. Do not make this decision yourself. The developer may choose to use a wrapper function (like `load_toml()`) that uses different libraries for different Python versions, or may decide on another approach.

### Static checks, Type Checking, Formatting, Linting, and Tests

**Requirement**: All code must pass `poetry run poe check:fix` **EVEN if the errors do not appear related to the work currently being done**. This command must be re-run every time until it is completely clean. It runs Static checks, Formatting, Type Checking, Linting, and Tests in both installed and singlefile runtimes.

**CI requirement**: `poetry run poe check:fix` must pass for CI to pass. **You cannot push code until this is resolved.**

For guidance on resolving type checking errors, see `type_checking.mdc`.

#### Available Commands

You can run individual tools using `poetry run poe <command>` (including `poetry run poe python`), but **before finishing a task, `poetry run poe check:fix` must complete successfully**.

**Main commands:**
- `poetry run poe check:fix` - Run all checks (fix, typecheck, test) - **must pass before completing work**
- `poetry run poe check` - Run all checks without fixing (lint, typecheck, test)
- `poetry run poe fix` - Auto-fix formatting and linting issues
- `poetry run poe lint` - Run linting checks only
- `poetry run poe typecheck` - Run type checking (mypy + pyright)
- `poetry run poe test` - Run test suite in both installed and singlefile runtimes

**Individual tool commands:**
- `poetry run poe lint:ruff` - Run ruff linting checks
- `poetry run poe fix:ruff:installed` - Auto-fix ruff linting issues
- `poetry run poe fix:format:installed` - Format code with ruff
- `poetry run poe typecheck:mypy` - Run mypy type checking
- `poetry run poe typecheck:pyright` - Run pyright type checking
- `poetry run poe test:pytest:installed` - Run tests in installed module mode
- `poetry run poe test:pytest:script` - Run tests in singlefile runtime mode

**Running tools on specific files:**
- Format a single file: `poetry run ruff format src/serger/build.py`
- Check a single file: `poetry run ruff check src/serger/build.py`
- Fix a single file: `poetry run ruff check --fix src/serger/build.py`
- Run a specific test (installed mode): `poetry run pytest tests/9_integration/test_log_level.py::test_specific_function`
- Run a specific test (singlefile mode): `RUNTIME_MODE=singlefile poetry run pytest tests/9_integration/test_log_level.py::test_specific_function`

#### Checkpoint Commits

You **CAN** check in code as a checkpoint after fixing most errors, and the AI can suggest doing so. **When committing, follow the conventions in `git_conventions.mdc`.** If you do this, the AI should write a prompt for opening a new chat to continue with the remaining fixes. The prompt should contain:

1. **Context**: Brief description of what was being worked on
2. **Current status**: What has been fixed and what remains
3. **Remaining issues**: List of specific errors or test failures that still need to be addressed
4. **Next steps**: What needs to be done to get `poetry run poe check:fix` passing
5. **Files changed**: List of files that were modified in this checkpoint

**Example prompt for new chat:**
```
I'm working on [feature/change description]. I've made a checkpoint commit after fixing most issues, but `poetry run poe check:fix` still has [X] remaining errors.

**Fixed:**
- [List of what was fixed]

**Remaining issues:**
- [Specific error messages or test failures]
- [Files that still need work]

**Next steps:**
- [What needs to be done]

**Files modified:**
- [List of changed files]

Please help me resolve the remaining issues to get `poetry run poe check:fix` passing.
```

### Test Module Naming

**Duplicate test module names**: When type checkers (mypy) report duplicate module names across different test directories (e.g., `tests/5_core/test_main_config.py` and `tests/9_integration/test_main_config.py`), **always rename the test files** to avoid conflicts rather than excluding them from type checking.

**Rationale**:
- Renaming maintains proper test organization and makes test purposes clear
- Excluding files from type checking reduces type safety coverage
- Descriptive names (e.g., `test_main_config_integration.py` vs `test_main_config.py`) improve code clarity

**Approach**:
1. Identify which test file should be renamed (typically the integration test or the newer one)
2. Choose a descriptive name that distinguishes it from the other (e.g., add `_integration`, `_unit`, or a specific feature suffix)
3. Update the file header comment to reflect the new name
4. Remove any type checker exclusions that were added as a workaround
5. Verify tests still run correctly with the new name

**Example**:
- ❌ **Bad**: Exclude `tests/9_integration/test_main_config.py` from mypy checking
- ✅ **Good**: Rename `tests/9_integration/test_main_config.py` to `tests/9_integration/test_main_config_integration.py`

# Communication

### Asking Questions

When asking questions, **wait for response** before proceeding. Exception: direct instructions (e.g., "add a function") are confirmation.

### Handling Developer Questions

If developer asks ANY question (including "do we need X?", "can we Y?"), you **must**:
1. Answer completely with recommendations
2. Ask what to do and **stop** - no implementation
3. Wait for response

Exploratory work (reading/searching) is allowed; no code changes.

### Troubleshooting When Stuck

Ask user for insight. Also ask if you should: stash changes, rollback, or add isolated changes one at a time. If yes, create plan in `.plan/` per `.ai/templates/plan_debug_rollback.tmpl.md` and consult `.ai/workflows/plan_debug_rollback.md`.

### Using Plan Documents

For complex features, refactors, API changes, or multi-phase work, use the plan format (`.ai/workflows/plan_feature.md`). Plans help coordinate work, track progress, and ensure all phases are completed.

# Git Conventions

### Git Commit Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

- NEVER include AI tool attribution or Co-Authored-By trailers in commit messages
- Write clean, conventional commit messages following the format: `type(scope): subject`
  - **type**: The type of change (feat, fix, docs, style, refactor, test, chore)
  - **scope**: The feature or module being worked on (optional but recommended)
  - **subject**: A concise description of what was done
    - **Important**: The subject line should account for all staged files in the commit
    - If the subject line cannot summarize all changes in a short sentence, prioritize the most impactful change to the project
    - All changes should still be detailed in the commit message body
- Include the feature being worked on in the scope, and if appropriate, a concise description of what was done
- **Commit message body**: After the first line, include a traditional bulleted list summarizing the key changes made in the commit
  - **Important**: The body should list all significant changes, ensuring all staged files are represented
  - If many files were changed, group related changes together in the bulleted list

**Examples:**

Single-line (for simple changes):
```
feat(build): add support for custom output paths
```

Multi-line with bulleted list (for more complex changes):
```
docs(ai-rules): update code quality rules with comprehensive guidelines

- Add detailed line length guidance with readability emphasis
- Add examples for comments, strings, and inline statements
- Add comprehensive Python version compatibility guidelines
- Add detailed static checks, type checking, formatting, linting, and tests section
- Add checkpoint commit guidance with prompt template
- Reference git_conventions.mdc for commit messages
```

Other examples:
- `fix(config): resolve validation error for empty build configs`
- `refactor(utils): simplify path normalization logic`
- `test(integration): add tests for log level handling`

# Project Overview

## Serger Project Context

### Project Overview
Serger is a Python module stitcher that combines multiple source files into a single executable script.

### See Also
- `pyproject.toml` - All tool configurations and poe tasks
- `ROADMAP.md` - Project roadmap and future plans

# Project Structure

### Important Files
- `dist/serger.py` is **generated** - never edit directly
- Generate it using `poetry run poe build:script`
- `dist/` contains build outputs - do not edit

### Project Structure
- `src/serger/` - Main source code
- `tests/` - Test suite
- `dev/` - Development scripts

# Pytest Structure

### PyTest Structure

## Packages
- Only `tests/` and `tests/utils/` should have `__init__.py`. Do NOT add `__init__.py` to test subdirectories (e.g., `tests/0_tooling/`, `tests/3_independant/`, `tests/5_core/`, etc.). Test subdirectories are not Python packages.
- Use `tests/utils/` to colocate utilities that are generally helpful for tests or used in multiple test files.

## Imports
- Never import from one test_* file into another test_* file.
- Never use `from <package> import <func>` for any `src/` packages, instead use `import <package> as mod_<package>` then use `mod_<package>.<func>`
- Don't import general utilities not under test from `src/` as test setup helpers. You may call related src functions in a test even if they are not primarily under test. Use `tests/utils/`as helpers only even if you have to replicate the src utility.
- You can import constants from `src/` code to use in tests, follow import rules.
- When writting new tests, be aware of our test utilities in `tests/utils/`, especially `patch_everywhere`

## Directories
- Integration tests go in their own directories separate from unit tests.

## Files
- Unit tests should have a single file per function tested.
- Integration tests should have a single file per feature or topic.
- Tests primarily testing private functions go in their own file `test_priv__<function name no leading underscore>.py` with a file level ignore statement.
- Tests primarily acting as a lint rule go in their own file  `test_lint__<purpose>.py` and should not be modified as a means of ignoring the failure. Fix the error reported instead.

## Runtime
- Tests run with `test` log-level by default so trace and debug statements bypass capsys and go to __stderr__.
- Tests are usually run twice, once against the `src/` directory, and again using our `tests/utils/runtime_swap.py` against the `dist/<package>.py` stitched file.

## Log Output Capture

### LOG_LEVEL=test Bypasses capsys
- By default, tests run with `LOG_LEVEL=test`, which is the most verbose level
- When `LOG_LEVEL=test` is set, TRACE and DEBUG messages bypass pytest's `capsys` capture and write directly to `sys.__stderr__`
- This means `capsys.readouterr()` will NOT capture TRACE/DEBUG messages when `LOG_LEVEL=test` is active
- This behavior is intentional to allow maximum visibility during test debugging

### Capturing Log Output with capsys
- If a test needs to assert against log output captured by `capsys`, it must set the log level to something other than `test`
- Use the `module_logger` fixture with `useLevel()` context manager to temporarily set a different log level:
  ```python
  def test_something(
      capsys: pytest.CaptureFixture[str],
      module_logger: mod_logs.AppLogger,
  ) -> None:
      # Set log level to info/debug so capsys can capture
      with module_logger.useLevel("info"):
          code = mod_cli.main(["--verbose"])
      
      captured = capsys.readouterr()
      out = (captured.out + captured.err).lower()
      assert "[debug" in out  # Now this will work
  ```
- Common log levels for capsys capture: `"info"`, `"debug"`, `"warning"` (avoid `"test"` if you need capsys)
- When using `module_logger.useLevel()`, the log level is automatically restored after the context exits

### Asserting Against stderr
- When `LOG_LEVEL=test` is active, check `sys.__stderr__` directly for TRACE/DEBUG messages
- Use `monkeypatch.setattr(sys, "__stderr__", StringIO())` to capture bypass messages:
  ```python
  from io import StringIO
  
  bypass_buf = StringIO()
  monkeypatch.setattr(sys, "__stderr__", bypass_buf)
  # ... run code ...
  bypass_output = bypass_buf.getvalue()
  assert "[trace" in bypass_output.lower()
  ```
- For INFO/WARNING/ERROR messages, use `capsys` with an appropriate log level (not `test`)

# Type Checking

### Type Checking and Linting Best Practices

#### General Principle: Fix Over Ignore
- **Always prioritize fixing errors over ignoring them** when possible
- Only use ignore comments when:
  - The error is a false positive that cannot be resolved by fixing the code
  - Fixing would require a significant architectural change that doesn't improve readability
  - The signature must match exactly (e.g., pytest hooks, interface implementations)
  - The check is intentionally defensive and provides value despite the warning
- When in doubt, attempt to fix the error first before resorting to ignore comments

#### Ignore Comments
- **Placement**: Warning/error ignore comments go at the end of lines and don't count towards line length limits
- **Examples**: `# type: ignore[error-code]`, `# pyright: ignore[error-code]`, `# noqa: CODE`
- **Ordering**: When multiple ignore comments are needed on the same line, **mypy `type: ignore` comments must come BEFORE `noqa` comments**
  - ✅ **Correct**: `from module import item  # type: ignore[import-not-found]  # noqa: PLC0415`
  - ❌ **Incorrect**: `from module import item  # noqa: PLC0415  # type: ignore[import-not-found]`
  - This ensures mypy processes the type ignore comment correctly

#### Common Patterns
- **Unused arguments**: Prefix with `_` (e.g., `_unused_param`) unless signature must match exactly (pytest hooks, interfaces) - then use ignore comments
- **Complexity/parameter warnings**: Consider refactoring only if it improves readability; otherwise add ignore comments
- **Type inference**: Use `cast_hint()` from `serger.utils` or `typing.cast()` when possible (not in tests); mypy can often infer types better than pyright
  - **`cast_hint()`**: Import from `serger.utils`. Use when:
    - You want to silence mypy's redundant-cast warnings
    - You want to signal "this narrowing is intentional"
    - You need IDEs (like Pylance) to retain strong inference on a value
    - **Do NOT use** for Union, Optional, or nested generics - use `cast()` for those
    - **Example**: `from serger.utils import cast_hint; items = cast_hint(list[Any], value)`
  - **`typing.cast()`**: Use for Union, Optional, or nested generics where type narrowing is meaningful
    - **Example**: `from typing import cast; result = cast(PathResolved, dict_obj)`
- **Defensive checks**: Runtime checks like `isinstance()` with ignore comments are only acceptable as defensive checks when data comes from external sources (function parameters, config files, user input). Do NOT use for constants or values that are known and can be typed properly within the function.
  - **Acceptable**: `if not isinstance(package, str):  # pyright: ignore[reportUnnecessaryIsInstance]` when `package` comes from parsed config file
  - **Not acceptable**: `if isinstance(CONSTANT_VALUE, str):` when `CONSTANT_VALUE` is a module-level constant that can be properly typed

#### TypedDict Maintenance
- **Always update TypedDict definitions when adding properties**: When adding a new property to a dictionary that is typed as a TypedDict (or should be), **always** update the corresponding TypedDict class definition to include that property. This ensures type safety and prevents runtime errors.
  - **Required**: If you add a field like `config["_new_field"] = value`, you must add `_new_field: NotRequired[Type]` (or `_new_field: Type` if required) to the TypedDict definition
  - **Never use `type: ignore` comments** to bypass missing TypedDict fields - instead, add the field to the type definition
  - **Example**: If adding `resolved_cfg["_pyproject_version"] = metadata.version`, add `_pyproject_version: NotRequired[str]` to the `RootConfigResolved` TypedDict
  - This applies to all TypedDict classes, including those in `config_types.py` and any other type definitions

#### Resolved TypedDict Pattern (config_types.py)
- **"Resolved" TypedDicts should not use `NotRequired` for fields that can be resolved**: In `config_types.py`, TypedDicts with "Resolved" suffix (e.g., `RootConfigResolved`, `PostProcessingConfigResolved`) represent fully resolved configurations. Fields that can be resolved (even to "empty" defaults) should **always be present**, not marked as `NotRequired`.
  - **Use `NotRequired` only for**: Fields that are truly optional throughout the entire resolution process and may never be set (e.g., `package`, `order` for non-stitch builds, or `_pyproject_version` when pyproject.toml is not used)
  - **Do NOT use `NotRequired` for**: Fields that can be resolved to a default value (empty list `[]`, empty dict `{}`, `False`, empty string `""`, etc.) - these should always be present in the resolved config
  - **Rationale**: A "Resolved" TypedDict represents a fully resolved state. If a field can be resolved (even to an empty default), it should be present to maintain the "fully resolved" contract and simplify usage (no need to check `if "field" in config`)
  - **Examples**:
    - ✅ **Correct**: `module_actions: list[ModuleActionFull]` in `RootConfigResolved` (always set to `[]` if not provided)
    - ✅ **Correct**: `post_processing: PostProcessingConfigResolved` in `RootConfigResolved` (always resolved with defaults)
    - ✅ **Correct**: `package: NotRequired[str]` in `RootConfigResolved` (only present for stitch builds)
    - ❌ **Incorrect**: `module_actions: NotRequired[list[ModuleActionFull]]` in `RootConfigResolved` (can be resolved to `[]`)

# Workflow

### Execution and Workflow
- Always use `poetry run python3` (not bare `python3`) to ensure execution in the project's virtual environment
- **Use poe tasks** for all common operations:
  - `poetry run poe check` - Run linting, type checking, and tests
  - `poetry run poe fix` - Auto-format and fix linting issues
  - `poetry run poe test` - Run test suite
  - `poetry run poe coverage` - Generate code coverage report (dual runtime coverage)
  - `poetry run poe check:fix` - Fix, type check, and test (run before committing)
  - `poetry run poe build:script` - Generate the single-file dist/serger.py
  - `poetry run poe sync:ai:guidance` - Sync AI guidance files from `.ai/` to `.cursor/` and `.claude/`
- **NEVER edit `.cursor/` or `.claude/` files directly**: These directories are generated from `.ai/` source files. Always edit files in `.ai/rules/` or `.ai/commands/` instead, then run `poetry run poe sync:ai:guidance` to sync changes.
- **When modifying `.ai/` files**: After changing any file in `.ai/rules/` or `.ai/commands/`, you **must**:
  1. Run `poetry run poe sync:ai:guidance` to sync changes to `.cursor/` and `.claude/`
  2. Include the generated files (`.cursor/rules/*.mdc`, `.cursor/commands/*.md`, `.claude/CLAUDE.md`) as part of the same changeset/commit
- **Before committing**: Run `poetry run poe check:fix` (this also regenerates `dist/serger.py` as needed)
- **Debugging failing tests**: Set `LOG_LEVEL=test` to output TRACE and DEBUG logs in failing tests, bypassing pytest's log capture. This is useful for debugging test failures:
  ```bash
  LOG_LEVEL=test poetry run poe test:pytest:installed tests/path/to/test.py::test_name -xvs
  ```
  The `test` log level is the most verbose and bypasses pytest's log capture, allowing you to see all TRACE and DEBUG logs even when tests fail.

# Claude Extra

## AI Model Strategy

When identifying tasks that require complex reasoning, planning, or analysis, ask for confirmation before proceeding:

> "This task appears to require significant planning and reasoning. Would you like me to use a hybrid model approach to create a detailed execution plan first, then switch to a faster model for implementation?"

If confirmed, follow this workflow:
1. **Check model availability**: Determine if the Opus model is available for the Task tool
2. **Planning phase**: 
   - If Claude Opus is available: Use the Task tool with `model: "opus"` and `subagent_type: "general-purpose"` to create a detailed execution plan and document the approach
   - If Claude Opus is not available: Use the Task tool with `model: "sonnet"` and `subagent_type: "general-purpose"` to create a detailed execution plan and document the approach
3. **Execution phase**: After receiving the plan:
   - If Opus was used for planning: Use Claude Sonnet to implement the plan following the documented steps
   - If Sonnet was used for planning: Use Claude Haiku to implement the plan following the documented steps

This hybrid approach combines the most capable model's superior reasoning for complex problems with faster models' speed for straightforward implementation.


