# Iteration 04: Validate and Resolve `module_actions` Config

## Goal
Add full validation and normalization of `module_actions` config in `config_resolve.py`. This includes parsing dict format to list format and validating all fields.

## Changes

### 1. Create Parsing Function (`src/serger/config/config_resolve.py`)
```python
def _normalize_module_actions(
    module_actions: ModuleActions | None,
) -> list[ModuleActionFull] | None:
    """
    Normalize module_actions config to list format.
    
    Converts dict format to list format and validates structure.
    Returns None if module_actions is None or empty.
    """
```

### 2. Validation Logic
- **Dict format**: Convert `{"old": "new"}` or `{"old": None}` to list format
  - `{"old": "new"}` → `[{"source": "old", "dest": "new", "action": "move"}]`
  - `{"old": None}` → `[{"source": "old", "action": "delete"}]`
- **List format**: Validate each action:
  - `source` is required and must be non-empty string
  - `dest` is required for `move`/`copy`, must not be present for `delete`
  - `action` must be one of `"move"`, `"copy"`, `"delete"`, `"none"` (if present)
  - `mode` must be one of `"preserve"`, `"flatten"` (if present)
  - `scope` must be one of `"original"`, `"shim"` (if present)
  - `affects` must be one of `"shims"`, `"stitching"`, `"both"` (if present)
  - `cleanup` must be one of `"auto"`, `"error"`, `"ignore"` (if present)
  - `source_path` must be a non-empty string (if present)

### 3. Update `resolve_build_config()`
- Call `_normalize_module_actions()` on `module_actions` from config
- Store normalized list in `BuildConfigResolved`
- Raise `ValueError` with clear message for invalid config

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
- Config is fully validated and normalized, but not yet used in stitch logic
- Normalized format is stored in `BuildConfigResolved` for later use
- All validation happens at config resolution time

## Testing
- Run `poetry run poe check:fix` - must pass
- Comprehensive tests for all validation cases
- Existing tests should still pass

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

