# Iteration 09: Expand Tests for Mode-to-Actions
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Add comprehensive tests for mode-to-actions conversion, including integration with parsing and validation.

## Changes

### 1. Expand Tests (`tests/5_core/test_module_actions.py`)
- Test mode-generated actions can be parsed
- Test mode-generated actions pass validation
- Test mode-generated actions can be applied
- Test combining mode-generated actions with user actions
- Test that mode-generated actions have correct defaults (scope: "original")

### 2. Add Integration-Style Tests
- Test full flow: mode → actions → validation → application
- Test that mode-generated actions produce same result as old mode logic (for comparison)
- Test edge cases:
  - Empty detected_packages
  - package_name in detected_packages
  - Multiple packages with same root name

### 3. Update Previous Tests
- Expand tests from iteration 05-08 to cover mode-generated actions
- Ensure all tests still pass with mode-generated actions

## Notes
- This iteration focuses on test coverage
- Ensures mode-to-actions conversion is well-tested
- Prepares for integration in next iteration

## Testing
- Run `poetry run poe check:fix` - must pass
- All new tests pass
- All previous tests still pass

## Commit Message
```
test(module_actions): expand tests for mode-to-actions conversion

- Add comprehensive tests for mode-to-actions integration
- Test mode-generated actions with parsing and validation
- Test combining mode-generated and user actions
- Test full flow from mode to applied actions
- Expand previous tests to cover mode-generated actions
```

