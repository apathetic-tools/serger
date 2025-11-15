# Iteration 14: Add Comprehensive Integration Tests
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Add comprehensive integration tests that test the full module_actions feature end-to-end. This includes testing config → stitched file → import behavior.

## Changes

### 1. Expand Integration Tests (`tests/9_integration/test_module_actions_integration.py`)
- **End-to-end tests**:
  - Test config with `module_actions` → stitched file → import works
  - Test that transformed module names are correct in stitched file
  - Test that shims work correctly after transformations
  - Test that deleted modules are not accessible
  - Test that copied modules work in both locations
  
- **Mode + actions tests**:
  - Test `module_mode: "force"` + user actions
  - Test `module_mode: "unify"` + user actions
  - Test `module_mode: "none"` + user actions with `scope: "original"`
  - Test that mode-generated actions work correctly
  
- **Scope tests**:
  - Test `scope: "original"` actions operate on original tree
  - Test `scope: "shim"` actions operate on transformed tree
  - Test chaining `scope: "shim"` actions
  - Test mixing `scope: "original"` and `scope: "shim"` in user actions
  
- **Affects tests**:
  - Test `affects: "shims"` only affects shim generation
  - Test `affects: "stitching"` only affects file selection
  - Test `affects: "both"` affects both
  - Test that files are correctly included/excluded based on affects
  
- **Cleanup tests**:
  - Test `cleanup: "auto"` deletes broken shims
  - Test `cleanup: "error"` raises error for broken shims
  - Test `cleanup: "ignore"` keeps broken shims
  - Test shim-stitching mismatch scenarios
  
- **Shim setting tests**:
  - Test `shim: "all"` generates shims for all modules
  - Test `shim: "none"` generates no shims
  - Test `shim: "public"` (if implemented, or skip for now)

### 2. Test Data
- Create test projects with various package structures
- Test with nested packages, subpackages, etc.
- Test edge cases (empty packages, single module, etc.)

### 3. Test Helpers
- Add helpers to:
  - Create test configs with module_actions
  - Run stitch and verify output
  - Import from stitched file and verify behavior
  - Check that shims work correctly

### 4. Update Previous Tests
- Ensure all previous unit tests still pass
- Expand unit tests if needed based on integration test findings

## Notes
- This is the final test iteration
- Ensures full feature works end-to-end
- Catches any integration issues

## Testing
- Run `poetry run poe check:fix` - must pass
- All integration tests pass
- All unit tests still pass
- Test coverage is comprehensive

## Commit Message
```
test(integration): add comprehensive module_actions integration tests

- Add end-to-end tests (config → stitched file → import)
- Test mode + actions combinations
- Test scope behavior (original vs shim)
- Test affects key (shims/stitching/both)
- Test cleanup key (auto/error/ignore)
- Test shim setting (all/none/public)
- Add test helpers for common scenarios
- Ensure full feature works correctly
```

