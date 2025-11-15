# Iteration 04: Validate and Resolve `module_actions` Config
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.
> **Prerequisites**: Complete iteration 03.5 to resolve clarifying questions first.

## Goal
Add full validation and normalization of `module_actions` config in `config_resolve.py`. This includes parsing dict format to list format and validating all fields.

## Changes

### 1. Update Normalization Function (`src/serger/config/config_resolve.py`)

**Note**: `_validate_and_normalize_module_actions()` already exists from iteration 03. Update it to:
- Apply all default values (per Q1 decision)
- Set `scope: "shim"` for user actions (per Q3 decision)
- Explicitly set `scope: "shim"` when converting dict format (per Q4 decision)
- Validate `dest` presence/absence based on action type (per Q5 decision)
- Basic `source_path` validation (non-empty string if present, per Q6 decision - full implementation deferred)

**Default values to apply** (per iteration 03.5 Q1):
- `action`: `"move"` (if not specified)
- `mode`: `"preserve"` (if not specified)
- `scope`: `"shim"` (for user actions - set at config resolution, per Q3)
- `affects`: `"shims"` (if not specified)
- `cleanup`: `"auto"` (if not specified)

### 2. Validation Logic
- **Dict format**: Convert `{"old": "new"}` or `{"old": None}` to list format
  - `{"old": "new"}` → `[{"source": "old", "dest": "new", "action": "move", "mode": "preserve", "scope": "shim", "affects": "shims", "cleanup": "auto"}]`
  - `{"old": None}` → `[{"source": "old", "action": "delete", "mode": "preserve", "scope": "shim", "affects": "shims", "cleanup": "auto"}]`
  - **Important**: Explicitly set `scope: "shim"` for dict format (per Q4)
- **List format**: Validate each action, then apply defaults:
  - `source` is required and must be non-empty string
  - `dest` validation (per Q5):
    - Required for `move`/`copy` actions (or if action not specified, defaults to "move")
    - Must NOT be present for `delete` actions
  - `action` must be in `literal_to_set(ModuleActionType)` (if present)
  - `mode` must be in `literal_to_set(ModuleActionMode)` (if present)
  - `scope` must be in `literal_to_set(ModuleActionScope)` (if present)
    - **Note**: User actions get `scope: "shim"` default if not specified (per Q3)
  - `affects` must be in `literal_to_set(ModuleActionAffects)` (if present)
  - `cleanup` must be in `literal_to_set(ModuleActionCleanup)` (if present)
  - `source_path` must be a non-empty string (if present) - basic validation only (per Q6)

### 3. Update `resolve_build_config()`
- Call `_validate_and_normalize_module_actions()` on `module_actions` from config
- Store normalized list in `BuildConfigResolved` (all fields present with defaults, per Q1/Q2)
- Raise `ValueError` with clear message for invalid config
- **Important**: Normalized actions have all fields present (fully resolved, per Q2)

### 4. Add Tests
- `tests/5_core/test_config_resolve.py`: Test normalization and validation
  - Test dict format normalization
  - Test list format validation
  - Test invalid `source` (missing, empty, wrong type)
  - Test invalid `dest` (missing for move/copy, present for delete)
  - Test invalid `action`, `mode`, `scope`, `affects`, `cleanup` values
  - Test `source_path` validation
  - Test error messages are clear

## Notes
- **Important**: This iteration implements decisions from iteration 03.5. See `current_plan/03.5_resolve_clarifying_questions.md` for full context.
- Config is fully validated and normalized with all defaults applied (per Q1/Q2)
- Normalized format is stored in `BuildConfigResolved` for later use (all fields present)
- All validation happens at config resolution time
- User actions get `scope: "shim"` default; mode-generated actions will set `scope: "original"` when created (per Q3)
- `dest` validation happens upfront (per Q5)
- `source_path` has basic validation only; full implementation deferred (per Q6)

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all validation cases
- Existing tests should still pass

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions that arise:

1. **Review the implementation**:
   - Check that all default values are applied correctly
   - Verify `scope: "shim"` is set for user actions (both dict and list format)
   - Verify `dest` validation works correctly for all action types
   - Check that error messages are clear and helpful
   - Verify all fields are present in normalized actions (fully resolved)

2. **Document any questions**:
   - Are there edge cases in default application that need clarification?
   - Are there validation scenarios that are ambiguous?
   - Are there any inconsistencies with existing code patterns?
   - Are there any unclear behaviors that should be documented?

3. **Resolve before proceeding**:
   - Answer all questions before moving to iteration 05
   - Update implementation if needed
   - Update iteration 05 plan if decisions affect it

**Questions to consider**:
- What happens if `source` is an empty string? (Should be caught by validation)
- What happens if `action` is `"none"` (alias for `"delete"`)? (Should be normalized to `"delete"`)
- Should we validate that `source` doesn't contain invalid characters?
- Are there any conflicts between defaults and explicit values that need handling?

## Commit Message
```
feat(config): validate and normalize module_actions config

- Add _normalize_module_actions() function
- Convert dict format to list format
- Validate all action fields (source, dest, action, mode, etc.)
- Store normalized list in BuildConfigResolved
- Add comprehensive validation tests
- Config is validated but not yet applied (coming in later iteration)
```

