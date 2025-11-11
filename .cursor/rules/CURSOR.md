# Base

## Serger Project Context

### Project Overview
Serger is a Python module stitcher that combines multiple source files into a single executable script.

### Key Conventions

#### Code Quality
- **Line length**: Maximum 88 characters (enforced by Ruff) - **always fix violations, never ignore them**
- **Python version**: Target Python 3.10+ compatibility
- **Type checking**: Strict Pyright/Pylance + Mypy compliance required
- **Linting**: All code must pass `poetry run poe check:fix`
- **CI Requirements**: All linting and type checking errors must be resolved (CI fails otherwise). Either fix the error or add an appropriate ignore comment.

#### Type Checking and Linting Best Practices

##### General Principle: Fix Over Ignore
- **Always prioritize fixing errors over ignoring them** when possible
- Only use ignore comments when:
  - The error is a false positive that cannot be resolved by fixing the code
  - Fixing would require a significant architectural change that doesn't improve readability
  - The signature must match exactly (e.g., pytest hooks, interface implementations)
  - The check is intentionally defensive and provides value despite the warning
- When in doubt, attempt to fix the error first before resorting to ignore comments

##### Ignore Comments
- **Placement**: Warning/error ignore comments go at the end of lines and don't count towards line length limits
- **Examples**: `# type: ignore[error-code]`, `# pyright: ignore[error-code]`, `# noqa: CODE`

##### Common Patterns
- **Unused arguments**: Prefix with `_` (e.g., `_unused_param`) unless signature must match exactly (pytest hooks, interfaces) - then use ignore comments
- **Complexity/parameter warnings**: Consider refactoring only if it improves readability; otherwise add ignore comments
- **Type inference**: Use `cast_hint()` (from `utils`) or `cast()` when possible; mypy can often infer types better than pyright
- **Defensive checks**: Keep runtime checks like `isinstance()` with ignore comments if they provide reasonable safety

#### Execution and Workflow
- Always use `poetry run python3` (not bare `python3`) to ensure execution in the project's virtual environment
- **Use poe tasks** for all common operations:
  - `poetry run poe check` - Run linting, type checking, and tests
  - `poetry run poe fix` - Auto-format and fix linting issues
  - `poetry run poe test` - Run test suite
  - `poetry run poe coverage` - Generate code coverage report (dual runtime coverage)
  - `poetry run poe check:fix` - Fix, type check, and test (run before committing)
  - `poetry run poe build:script` - Generate the single-file dist/serger.py
- **Before committing**: Run `poetry run poe check:fix` and regenerate `dist/serger.py` if needed

#### Important Files
- `dist/serger.py` is **generated** - never edit directly
- Generate it using `poetry run poe build:script`
- `dist/` contains build outputs - do not edit

#### Project Structure
- `src/serger/` - Main source code
- `tests/` - Test suite
- `dev/` - Development scripts

#### Git Commit Conventions
- NEVER include AI tool attribution or Co-Authored-By trailers in commit messages
- Write clean, conventional commit messages

### See Also
- `pyproject.toml` - All tool configurations and poe tasks
- `ROADMAP.md` - Project roadmap and future plans


