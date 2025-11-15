# Iteration 08: Create Mode-to-Actions Conversion
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Create `generate_actions_from_mode()` function that converts `module_mode` values to equivalent `module_actions`. This allows modes to generate actions internally.

## Changes

### 1. Add Conversion Function (`src/serger/module_actions.py`)
```python
def generate_actions_from_mode(
    module_mode: str,
    detected_packages: set[str],
    package_name: str,
) -> list[ModuleActionFull]:
    """
    Generate module_actions equivalent to a module_mode.
    
    Converts module_mode presets into explicit actions that are prepended to
    user-specified actions. Returns list of actions that would produce the
    same result as the mode.
    
    All generated actions have scope: "original".
    """
```

### 2. Mode-to-Actions Mapping
- `"force"`: For each detected root package (except `package_name`), generate:
  ```python
  {"source": pkg, "dest": package_name, "mode": "preserve", "scope": "original"}
  ```
- `"force_flat"`: For each detected root package (except `package_name`), generate:
  ```python
  {"source": pkg, "dest": package_name, "mode": "flatten", "scope": "original"}
  ```
- `"unify"`: For each detected package (except `package_name`), generate:
  ```python
  {"source": pkg, "dest": f"{package_name}.{pkg}", "mode": "preserve", "scope": "original"}
  ```
- `"unify_preserve"`: Same as `"unify"` (preserve is default)
- `"multi"`: Return empty list (no actions needed - default behavior)
- `"none"`: Return empty list (no shims, handled separately via `shim` setting)
- `"flat"`: Cannot be expressed as actions (requires file-level detection) - raise `NotImplementedError` or return empty list with comment

### 3. Implementation Details
- Generate actions with required fields (`source`, `dest` where needed)
- Apply defaults using `set_mode_generated_action_defaults()` from iteration 05
  - This sets `scope: "original"` (always for mode-generated)
  - Sets other defaults (action: "move", mode: "preserve", affects: "shims", cleanup: "auto")
- Actions are generated in sorted order for determinism
- Handle edge cases (no packages, package_name in detected_packages, etc.)

### 4. Add Tests
- `tests/5_core/test_module_actions.py`: Test mode-to-actions conversion
  - Test `"force"` mode generates correct actions
  - Test `"force_flat"` mode generates correct actions
  - Test `"unify"` mode generates correct actions
  - Test `"unify_preserve"` mode (same as unify)
  - Test `"multi"` mode returns empty list
  - Test `"none"` mode returns empty list
  - Test `"flat"` mode (NotImplementedError or empty list)
  - Test that all generated actions have `scope: "original"`
  - Test that package_name is excluded from actions
  - Test sorted order for determinism

## Notes
- Function is ready but not yet called from stitch logic
- This allows modes to be converted to actions internally
- All mode-generated actions operate on original tree

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all mode conversions
- Test edge cases (empty packages, package_name matches, etc.)

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that all mode values are correctly mapped to actions
   - Verify that generated actions have correct defaults (`scope: "original"`, `affects: "shims"`)
   - Check that actions are generated in sorted order for determinism
   - Verify edge cases (empty packages, package_name in detected_packages)

2. **Document any questions**:
   - How should we handle `"flat"` mode (cannot be expressed as actions)?
   - Are there any differences between mode behavior and generated actions?
   - Should we validate that generated actions match expected mode behavior?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 09
   - Update implementation if needed
   - Update iteration 09 plan if decisions affect it

**Questions to consider**:
- Should `"flat"` mode raise `NotImplementedError` or return empty list with a comment?
- How should we handle `package_name` that appears in `detected_packages`?
- Are there any edge cases with mode conversion that need special handling?

## Commit Message
```
feat(module_actions): add mode-to-actions conversion

- Add generate_actions_from_mode() to convert module_mode to actions
- Map all mode values (force, force_flat, unify, multi, none, flat)
- All generated actions have scope: "original" and affects: "shims"
- Actions generated in sorted order for determinism
- Add comprehensive tests for all mode conversions
- Not yet integrated into stitch logic (coming in later iteration)
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 08 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to iteration 09
- Include a brief summary of what was done (e.g., "Added generate_actions_from_mode() to convert module_mode values to equivalent module_actions")

This ensures the next chat session can pick up where this one left off.

