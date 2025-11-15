# Iteration 12: Add `affects` and `cleanup` Handling
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Add support for `affects` key (shims/stitching/both) and `cleanup` key (auto/error/ignore) to handle shim-stitching mismatches.

## Changes

### 1. Update Action Processing (`src/serger/module_actions.py`)
- Separate actions by `affects` value when processing
- Track which modules are deleted from stitching vs shims
- After applying all actions, check for shims pointing to deleted modules
- Implement `cleanup` behavior:
  - `"auto"`: Auto-delete broken shims (with optional warning)
  - `"error"`: Raise error if action creates broken shims
  - `"ignore"`: Keep broken shims (advanced use case)

### 2. Update Stitch Logic (`src/serger/stitch.py`)
- Separate actions by `affects` value:
  - `affects: "shims"` → apply to shim generation only
  - `affects: "stitching"` → apply to file selection for stitching
  - `affects: "both"` → apply to both
- Track module-to-file mapping to determine which files to stitch
- After applying actions, check for shim-stitching mismatches
- Apply cleanup behavior based on `cleanup` key

### 3. File Selection Logic
- For `affects: "stitching"` or `affects: "both"` delete actions:
  - Track which modules are deleted
  - Determine which files contain deleted modules
  - Exclude those files from stitching (or handle mixed modules in file)
- For `affects: "stitching"` or `affects: "both"` move/copy actions:
  - Currently only affects shim paths, not file selection (files still stitched)
  - Future: could affect file organization

### 4. Cleanup Logic
- After all actions applied, check for shims pointing to modules deleted from stitching
- For each action that creates a mismatch:
  - `cleanup: "auto"`: Delete broken shims (with optional warning log)
  - `cleanup: "error"`: Raise `ValueError` with clear message
  - `cleanup: "ignore"`: Keep broken shims (no action)

### 5. Add Tests
- `tests/9_integration/test_module_actions_integration.py`: Test affects and cleanup
  - Test `affects: "shims"` only affects shim generation
  - Test `affects: "stitching"` only affects file selection
  - Test `affects: "both"` affects both
  - Test `cleanup: "auto"` deletes broken shims
  - Test `cleanup: "error"` raises error for broken shims
  - Test `cleanup: "ignore"` keeps broken shims
  - Test shim-stitching mismatch scenarios
  - Test file selection with deleted modules

## Notes
- This is the final feature iteration
- Handles the relationship between shims and stitching
- Provides flexible control over what gets affected

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all `affects` and `cleanup` combinations
- Test edge cases (mixed modules in files, etc.)

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that `affects` key works correctly for all values (shims/stitching/both)
   - Verify that file selection is correct for `affects: "stitching"` actions
   - Check that cleanup behavior works correctly (auto/error/ignore)
   - Verify that shim-stitching mismatches are detected and handled correctly

2. **Document any questions**:
   - Are there edge cases in affects handling that need clarification?
   - How should we handle files with mixed modules (some deleted, some kept)?
   - Are there any performance concerns with tracking module-to-file mapping?
   - Should cleanup warnings be logged or silent?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 13
   - Update implementation if needed
   - Update iteration 13 plan if decisions affect it

**Questions to consider**:
- How should we handle files that contain both deleted and kept modules?
- Should cleanup warnings be logged at a specific log level?
- Are there any edge cases with cleanup behavior that need special handling?

## Commit Message
```
feat(module_actions): add affects and cleanup handling

- Support affects key (shims/stitching/both) to control action scope
- Support cleanup key (auto/error/ignore) for shim-stitching mismatches
- Separate actions by affects value when processing
- Track module-to-file mapping for file selection
- Implement cleanup behavior (auto-delete, error, or ignore broken shims)
- Add comprehensive tests for affects and cleanup
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 12 as completed ✓
- Update the "Current status" section with what was accomplished in this iteration
- Update "Next step" to point to iteration 13
- Include a brief summary of what was done (e.g., "Added affects and cleanup handling for shim-stitching mismatches")

This ensures the next chat session can pick up where this one left off.

