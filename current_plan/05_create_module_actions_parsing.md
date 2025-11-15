# Iteration 05: Create `module_actions.py` with Parsing Functions
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.


## Goal
Create the core `module_actions.py` file with helper functions for processing module actions. **Note**: Config parsing and normalization is already done in iteration 04 (config resolution), so this focuses on helper functions for working with already-normalized actions and setting defaults on mode-generated actions.

## Changes

### 1. Create New File (`src/serger/module_actions.py`)
```python
"""Module actions processing for renaming, moving, copying, and deleting modules."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from serger.config.config_types import ModuleActionFull

def set_mode_generated_action_defaults(
    action: ModuleActionFull,
) -> ModuleActionFull:
    """
    Set default values for mode-generated actions.
    
    Mode-generated actions are created fresh (not from config), so they need
    defaults applied. All mode-generated actions have:
    - action: "move" (if not specified)
    - mode: "preserve" (if not specified)
    - scope: "original" (always set for mode-generated)
    - affects: "shims" (if not specified)
    - cleanup: "auto" (if not specified)
    
    Note: User actions from BuildConfigResolved already have all defaults
    applied (including scope: "shim") from config resolution (iteration 04).
    """
    # Implementation here
```

### 2. Implementation Details
- `set_mode_generated_action_defaults()`:
  - Set `action: "move"` if not specified
  - Set `mode: "preserve"` if not specified
  - **Always set** `scope: "original"` (mode-generated actions always use original scope)
  - Set `affects: "shims"` if not specified
  - Set `cleanup: "auto"` if not specified
  - Return action with all fields present

### 3. Notes on Config Resolution (Iteration 04)
- **User actions** from `BuildConfigResolved.module_actions` are already:
  - Normalized to list format
  - Have all defaults applied (action, mode, affects, cleanup)
  - Have `scope: "shim"` set (per Q3 decision)
  - Ready to use directly - no parsing needed
  
- **Mode-generated actions** are created fresh in iteration 08/10, so they need:
  - Defaults applied using `set_mode_generated_action_defaults()`
  - `scope: "original"` explicitly set (per Q3 decision)

### 4. Add Tests
- `tests/5_core/test_module_actions.py`: Test helper functions
  - Test `set_mode_generated_action_defaults()` sets all defaults correctly
  - Test that `scope: "original"` is always set for mode-generated actions
  - Test that all fields are properly set
  - Test with actions that already have some fields set (shouldn't override)

## Notes
- **Important**: Config parsing is done in iteration 04 (config resolution)
- User actions from `BuildConfigResolved` are already fully normalized - use directly
- This iteration focuses on helper functions for mode-generated actions
- Mode-generated actions need defaults applied when created (iteration 08/10)

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive unit tests for all parsing functions
- Test edge cases (empty dict, empty list, etc.)

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that parsing functions handle all edge cases correctly
   - Verify default values are set correctly for both mode-generated and user actions
   - Check that dict format conversion works correctly
   - Verify all fields are properly set in normalized actions
   - Check for any inconsistencies with config resolution logic (iteration 04)

2. **Document any questions**:
   - Are there edge cases in parsing that need clarification?
   - Are there any conflicts between this parsing and config resolution?
   - Are there any unclear behaviors that should be documented?
   - Should `parse_module_actions()` duplicate logic from config resolution, or should it reuse it?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 06
   - Update implementation if needed
   - Update iteration 06 plan if decisions affect it

**Questions to consider**:
- Should we add other helper functions for working with normalized actions?
- Are there any edge cases with setting defaults on mode-generated actions?

## Commit Message
```
feat(module_actions): add helper functions for mode-generated actions

- Create src/serger/module_actions.py
- Add set_mode_generated_action_defaults() to set defaults on fresh actions
- Mode-generated actions get scope: "original" and other defaults
- Note: User actions from BuildConfigResolved already normalized (iteration 04)
- Add comprehensive unit tests
- Not yet integrated into stitch logic (coming in later iteration)
```

