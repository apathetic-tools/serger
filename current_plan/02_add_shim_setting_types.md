# Iteration 02: Add `shim` Setting Types

> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Add the new `shim` setting type (`"all" | "public" | "none"`) to control shim generation. This is type-only, not yet used in logic.

## Changes

### 1. Add Type Definition (`src/serger/config/config_types.py`)
```python
ShimSetting = Literal["all", "public", "none"]
```

### 2. Add to Config Types
- Add `shim: NotRequired[ShimSetting]` to `BuildConfig`
- Add `shim: NotRequired[ShimSetting]` to `RootConfig`
- Add `shim: ShimSetting` to `BuildConfigResolved` (required, default `"all"`)

### 3. Update Config Resolution (`src/serger/config/config_resolve.py`)
- In `resolve_build_config()`, resolve `shim` setting:
  - Default: `"all"` if not specified
  - Cascade from root config if not in build config
  - Validate value using `literal_to_set(ShimSetting)` to get valid values
- Store resolved value in `BuildConfigResolved`

### 4. Add Tests
- `tests/5_core/test_config_resolve.py`: Test `shim` setting resolution
  - Test default value (`"all"`)
  - Test cascade from root config
  - Test invalid values raise error
  - Test valid values are accepted

## Notes
- The `shim` setting is not yet used in stitch logic - that comes later
- This iteration only adds types and config resolution
- Code that will use this setting can be added but not called yet

## Testing
- Run `poetry run poe check:fix` - must pass
- New tests for `shim` setting resolution
- Existing tests should still pass

## Commit Message
```
feat(config): add shim setting type and resolution

- Add ShimSetting type: "all" | "public" | "none"
- Add shim key to BuildConfig, RootConfig, BuildConfigResolved
- Resolve shim setting in config_resolve.py (default: "all")
- Add tests for shim setting resolution
- Not yet used in stitch logic (coming in later iteration)
```

