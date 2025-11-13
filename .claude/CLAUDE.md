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

# Git Conventions

### Git Commit Conventions
- NEVER include AI tool attribution or Co-Authored-By trailers in commit messages
- Write clean, conventional commit messages following the format: `type(scope): subject`
  - **type**: The type of change (feat, fix, docs, style, refactor, test, chore)
  - **scope**: The feature or module being worked on (optional but recommended)
  - **subject**: A concise description of what was done
- Include the feature being worked on in the scope, and if appropriate, a concise description of what was done
- **Commit message body**: After the first line, include a traditional bulleted list summarizing the key changes made in the commit

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
- **Before committing**: Run `poetry run poe check:fix` (this also regenerates `dist/serger.py` as needed)

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


