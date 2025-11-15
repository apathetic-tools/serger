# Iteration 11: Add Scope Handling
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Ensure scope handling works correctly in the integrated system. This includes proper validation timing and action ordering.

## Changes

### 1. Refine Scope Handling (`src/serger/stitch.py`)
- Ensure `scope: "original"` actions are validated upfront (all at once)
- Ensure `scope: "shim"` actions are validated incrementally (one at a time)
- Ensure actions are applied in correct order (original scope first, then shim scope)

### 2. Update Validation Logic (`src/serger/module_actions.py`)
- Ensure `validate_module_actions()` handles upfront validation correctly
- Ensure incremental validation works for `scope: "shim"` actions
- Add better error messages that indicate which scope failed

### 3. Add Tests
- `tests/9_integration/test_module_actions_integration.py`: Test scope handling
  - Test that `scope: "original"` actions are validated upfront
  - Test that `scope: "shim"` actions are validated incrementally
  - Test that actions are applied in correct order
  - Test that `scope: "shim"` actions can reference results of previous actions
  - Test error messages indicate correct scope

### 4. Edge Cases
- Test `module_mode: "none"` + user actions with `scope: "original"`
- Test chaining user actions (each references previous result)
- Test mixing `scope: "original"` and `scope: "shim"` in user actions

## Notes
- This iteration refines scope handling that was added in iteration 10
- Ensures validation timing is correct
- Ensures action ordering is correct

## Testing
- Run `poetry run poe check:fix` - must pass
- All scope-related tests pass
- Existing tests still pass

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that scope handling works correctly in all scenarios
   - Verify that validation timing is correct (upfront vs incremental)
   - Check that action ordering is correct
   - Verify that error messages clearly indicate which scope failed

2. **Document any questions**:
   - Are there any edge cases in scope handling that need clarification?
   - Are there any scenarios where scope behavior is ambiguous?
   - Should we add more validation for scope consistency?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 12
   - Update implementation if needed
   - Update iteration 12 plan if decisions affect it

**Questions to consider**:
- How should we handle user actions that mix `scope: "original"` and `scope: "shim"`?
- Are there any validation rules we should add for scope consistency?
- Should we warn about potentially confusing scope usage?

## Commit Message
```
feat(module_actions): refine scope handling

- Ensure scope: "original" actions validated upfront
- Ensure scope: "shim" actions validated incrementally
- Ensure actions applied in correct order
- Add tests for scope handling edge cases
- Improve error messages to indicate scope
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 11 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to iteration 12
- Include a brief summary of what was done (e.g., "Refined scope handling with proper validation timing and action ordering")

This ensures the next chat session can pick up where this one left off.

