# Iteration 01: Rename `shim_mode` → `module_mode`

> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Rename `shim_mode` to `module_mode` throughout the codebase in types and config handling. This is a pure rename with no functional changes.

## Changes

### 1. Update Type Definitions (`src/serger/config/config_types.py`)
- Rename `ShimMode` → `ModuleMode`
- Update `BuildConfig` and `RootConfig`: `shim_mode: ShimMode` → `module_mode: ModuleMode`
- Update `BuildConfigResolved`: `shim_mode: ShimMode` → `module_mode: ModuleMode`
- Keep the same literal values: `"none" | "multi" | "force" | "force_flat" | "unify" | "unify_preserve" | "flat"`

### 2. Update Config Resolution (`src/serger/config/config_resolve.py`)
- Update any references to `shim_mode` in resolution logic
- Ensure backward compatibility by accepting both keys during transition (if needed, or just rename)

### 3. Update Stitch Logic (`src/serger/stitch.py`)
- Rename parameter `shim_mode` → `module_mode` in `_build_final_script()` and `stitch_modules()`
- Update all internal references

### 4. Update Tests
- Update all test files that reference `shim_mode`
- Ensure all tests pass

### 5. Update Documentation
- Update `docs/configuration-reference.md` to use `module_mode`
- Update any other docs that mention `shim_mode`

## Testing
- Run `poetry run poe check:fix` - must pass
- All existing tests should pass (no functional changes)
- Verify config files with `shim_mode` are still accepted (or document breaking change)

## Commit Message
```
refactor(config): rename shim_mode to module_mode

- Rename ShimMode type to ModuleMode
- Update BuildConfig, RootConfig, BuildConfigResolved
- Update stitch.py parameter names
- Update documentation
- No functional changes, pure rename
```

