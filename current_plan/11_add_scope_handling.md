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

## Commit Message
```
feat(module_actions): refine scope handling

- Ensure scope: "original" actions validated upfront
- Ensure scope: "shim" actions validated incrementally
- Ensure actions applied in correct order
- Add tests for scope handling edge cases
- Improve error messages to indicate scope
```

