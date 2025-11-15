# Iteration 10: Integrate Module Actions into Stitch Logic

> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Replace `module_mode` logic in `stitch.py` with `module_actions` processing. This is the main integration point.

## Changes

### 1. Update `stitch.py` (`src/serger/stitch.py`)
- In `_build_final_script()`, replace `shim_mode` logic with:
  1. Generate actions from `module_mode` (if specified and not "none"/"multi")
  2. Get user-specified `module_actions` from `BuildConfigResolved` (already normalized)
  3. Combine mode-generated actions (scope: "original") with user actions (scope: "shim" already set)
  4. Separate actions by scope
  5. Validate and apply `scope: "original"` actions first
  6. Validate and apply `scope: "shim"` actions incrementally
  7. Use transformed module names for shim generation
  
**Important**: `module_actions` from `BuildConfigResolved` is already fully normalized with all defaults applied (per iteration 03.5 Q1/Q2/Q3). No parsing needed - use directly.

### 2. Integration Flow
```python
# After detecting packages and initial module names
shim_names = [...]  # Initial module names from structure
original_shim_names = shim_names.copy()  # Keep original for scope: "original" validation

# Generate actions from module_mode if specified
all_actions = []
if module_mode and module_mode not in ("none", "multi"):
    auto_actions = generate_actions_from_mode(
        module_mode, detected_packages, package_name
    )
    # Apply defaults to mode-generated actions (scope: "original" set here)
    for action in auto_actions:
        action = set_mode_generated_action_defaults(action)
        # scope: "original" is set by set_mode_generated_action_defaults()
    all_actions.extend(auto_actions)

# Add user-specified module_actions from BuildConfigResolved
# These are already fully normalized with scope: "shim" set (iteration 04)
if module_actions:  # Already list[ModuleActionFull] with all defaults applied
    all_actions.extend(module_actions)

# Separate actions by scope
original_scope_actions = [a for a in all_actions if a["scope"] == "original"]
shim_scope_actions = [a for a in all_actions if a["scope"] == "shim"]

# Validate and apply scope: "original" actions first
if original_scope_actions:
    validate_module_actions(original_scope_actions, original_shim_names, detected_packages, scope="original")
    shim_names = apply_module_actions(shim_names, original_scope_actions, detected_packages)

# Validate and apply scope: "shim" actions (incremental validation)
if shim_scope_actions:
    for action in shim_scope_actions:
        validate_action_source_exists(action, set(shim_names))
        shim_names = apply_single_action(shim_names, action, detected_packages)

# Continue with existing shim generation using transformed shim_names...
```

**Key points**:
- `module_actions` from `BuildConfigResolved` is already `list[ModuleActionFull]` with all fields present
- User actions already have `scope: "shim"` set (per iteration 03.5 Q3)
- Mode-generated actions get defaults applied (including `scope: "original"`) when created
- No parsing or scope checking needed - actions are ready to use

### 3. Handle `shim` Setting
- Check `shim` setting from config:
  - `"none"`: Don't generate shims (skip shim generation entirely)
  - `"all"`: Generate shims for all modules (default, existing behavior)
  - `"public"`: Only generate shims for public modules (future: based on `_` prefix)

### 4. Update Function Signatures
- Update `_build_final_script()` to accept `module_actions: list[ModuleActionFull]` and `shim` from config
- `module_actions` is already normalized from `BuildConfigResolved` - type is `list[ModuleActionFull]` with all fields present
- Update `stitch_modules()` to pass these through

### 5. Add Tests
- `tests/9_integration/test_module_actions_integration.py`: Integration tests
  - Test mode + user actions work together
  - Test scope: "original" vs scope: "shim" behavior
  - Test that transformed module names are used for shim generation
  - Test `shim: "none"` setting
  - Test end-to-end: config → stitched file → import test

### 6. Update Existing Tests
- Update tests that use `shim_mode` to use `module_mode` and `module_actions`
- Ensure all existing tests still pass

## Notes
- This is the main integration point
- Old `shim_mode` logic is replaced with `module_actions` processing
- `shim` setting controls whether shims are generated at all
- **Important**: `module_actions` from `BuildConfigResolved` is already fully normalized (iteration 04)
  - All defaults applied (action, mode, affects, cleanup)
  - `scope: "shim"` already set for user actions (per iteration 03.5 Q3)
  - No parsing needed - use directly
- Mode-generated actions need defaults applied when created (use `set_mode_generated_action_defaults()`)

## Testing
- Run `poetry run poe check:fix` - must pass
- All existing tests should pass (with updated config)
- New integration tests pass
- Test that old `shim_mode` behavior is preserved when using equivalent `module_actions`

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that integration works correctly with existing stitch logic
   - Verify that mode-generated actions are combined correctly with user actions
   - Check that scope handling works as expected (original first, then shim)
   - Verify that `shim` setting is respected
   - Check that transformed module names are used correctly for shim generation

2. **Document any questions**:
   - Are there any integration issues with existing code?
   - Are there any edge cases in the integration that need clarification?
   - How should we handle backward compatibility with old `shim_mode` configs?
   - Are there any performance concerns with the new integration?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 11
   - Update implementation if needed
   - Update iteration 11 plan if decisions affect it

**Questions to consider**:
- Should we support backward compatibility with old `shim_mode` configs, or require migration?
- Are there any edge cases with combining mode-generated and user actions?
- How should we handle errors during action application in the stitch flow?
- Since `module_actions` is already normalized, do we need to validate it again, or trust config resolution?

## Commit Message
```
feat(stitch): integrate module_actions into stitch logic

- Replace shim_mode logic with module_actions processing
- Generate actions from module_mode and combine with user actions
- Apply scope: "original" actions first, then scope: "shim" actions
- Support shim setting ("all" | "public" | "none")
- Update _build_final_script() and stitch_modules() signatures
- Add integration tests for module_actions
- Update existing tests to use module_mode and module_actions
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 10 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to iteration 11
- Include a brief summary of what was done (e.g., "Integrated module_actions into stitch logic, replacing shim_mode processing")

This ensures the next chat session can pick up where this one left off.

