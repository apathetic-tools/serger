# Fix Singlefile Mode Test Failures

## Context

I've just completed a major refactoring to reorganize imports and test structure for the new `apathetic_schema` and `apathetic_utils` packages. The refactoring involved:

- Moving utility functions from `serger.utils` to new top-level packages `apathetic_schema` and `apathetic_utils`
- Updating all imports in `src/serger` to use the new packages directly
- Updating all test imports to use module-level imports with 'a' prefix for apathetic packages
- Moving test files from `tests/3_independant/` to `tests/2_packages/` based on which package they test

**Status**: All tests pass in **installed mode** (756 passed, 2 skipped), but **22 tests fail in singlefile mode**.

## Problem

When running `poetry run poe check:fix`, the singlefile mode tests (`test:pytest:script`) fail with several categories of errors:

### 1. Module Attribute Errors (19 tests)

Multiple tests fail with errors like:
```
AttributeError: module 'types' has no attribute 'safe_isinstance'
TypeError: Could not find 'safe_isinstance' on <module 'types' from '/usr/lib/python3.12/types.py'>
```

**Affected tests:**
- `tests/2_packages/apathetic_utils/test_safe_isinstance.py` (all 19 test cases)
- `tests/2_packages/apathetic_schema/test_priv__validate_scalar_value.py::test_validate_scalar_value_handles_fallback_path`

**Root cause**: In singlefile mode, when tests import `import apathetic_utils.types as amod_utils_types`, the stitched singlefile appears to be resolving this to the stdlib `types` module instead of `apathetic_utils.types`. This suggests the stitched file may not be properly exposing submodules or there's a naming conflict.

### 2. Submodule Attribute Missing (1 test)

```
tests/9_integration/test_subpackage_imports.py::test_serger_utils_subpackage_imports
AssertionError: apathetic_utils.text attribute should point to the module
```

**Root cause**: The test expects `apathetic_utils.text` to be accessible as an attribute on the `apathetic_utils` package (like `apathetic_utils_pkg.text`), but in the stitched singlefile, this attribute doesn't exist. The submodule exists in `sys.modules['apathetic_utils.text']`, but it's not exposed as a package attribute.

### 3. Runtime Mode Detection (1 test)

```
tests/0_tooling/test_pytest__runtime_mode_swap.py::test_pytest_runtime_cache_integrity
AssertionError: assert 'installed' == 'standalone'
```

**Root cause**: Runtime mode detection may not be working correctly in singlefile mode.

## Key Files to Investigate

1. **`src/apathetic_utils/__init__.py`** - Currently only imports functions, not submodules. May need to expose submodules as attributes for singlefile mode.

2. **`src/apathetic_schema/__init__.py`** - Similar issue, may need submodule exposure.

3. **`src/serger/build.py`** - The stitching logic that creates `dist/serger.py`. May need to ensure submodules are properly exposed as package attributes.

4. **`tests/2_packages/apathetic_utils/test_safe_isinstance.py`** - One of the failing test files that imports `import apathetic_utils.types as amod_utils_types`.

5. **`tests/9_integration/test_subpackage_imports.py`** - Integration test that verifies subpackage imports work in stitched singlefile.

## Investigation Steps

1. **Check how submodules are exposed in stitched singlefile**: Look at how `serger.utils.utils_modules` is exposed (since that test passes) vs how `apathetic_utils.text` should be exposed.

2. **Examine the stitched file**: Run `poetry run poe build:script` and inspect `dist/serger.py` to see how `apathetic_utils` and its submodules are structured.

3. **Check for naming conflicts**: Verify if there's a conflict between `apathetic_utils.types` and the stdlib `types` module in singlefile mode.

4. **Review build.py stitching logic**: The code that stitches modules together may need updates to properly handle the new `apathetic_*` package structure.

## Expected Outcome

After fixes:
- All tests should pass in both installed and singlefile modes
- `apathetic_utils.text`, `apathetic_utils.types`, etc. should be accessible as package attributes in singlefile mode
- Tests importing `import apathetic_utils.types as amod_utils_types` should correctly resolve to `apathetic_utils.types`, not the stdlib `types` module

## Command to Run

```bash
poetry run poe check:fix
```

This will run all checks including the singlefile mode tests that are currently failing.

