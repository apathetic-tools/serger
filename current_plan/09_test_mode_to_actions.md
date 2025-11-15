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

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that all tests cover the intended scenarios
   - Verify that mode-generated actions work correctly with parsing and validation
   - Check that combining mode-generated and user actions works as expected
   - Verify that test coverage is comprehensive

2. **Document any questions**:
   - Are there any test scenarios that are missing?
   - Are there any edge cases that need additional tests?
   - Do the tests adequately verify that mode-generated actions match old mode behavior?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 10
   - Add additional tests if needed
   - Update iteration 10 plan if decisions affect it

**Questions to consider**:
- Should we add comparison tests to verify mode-generated actions produce same results as old mode logic?
- Are there any integration scenarios that need testing before iteration 10?

## Commit Message
```
test(module_actions): expand tests for mode-to-actions conversion

- Add comprehensive tests for mode-to-actions integration
- Test mode-generated actions with parsing and validation
- Test combining mode-generated and user actions
- Test full flow from mode to applied actions
- Expand previous tests to cover mode-generated actions
```

