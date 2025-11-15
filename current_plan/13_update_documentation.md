# Iteration 13: Update Documentation with End Goal

## Goal
Update `configuration-reference.md` and other documentation to reflect the complete module_actions feature. Document the end goal without extra ROADMAP items.

## Changes

### 1. Update `docs/configuration-reference.md`
- Add section for `module_mode` (renamed from `shim_mode`)
- Add section for `shim` setting (`"all" | "public" | "none"`)
- Add comprehensive section for `module_actions`:
  - Configuration formats (dict and list)
  - All action types (move, copy, delete)
  - All parameters (source, dest, action, mode, scope, affects, cleanup)
  - Examples for common use cases
  - Relationship with `module_mode`
  - Scope behavior (`"original"` vs `"shim"`)
  - `affects` key behavior
  - `cleanup` key behavior
  - Validation rules and error messages

### 2. Update Examples
- Add examples showing:
  - Simple rename (dict format)
  - Flatten subpackage
  - Multi-level operations
  - Copy operations
  - Delete operations
  - Mode + user actions
  - Scope: "original" vs scope: "shim"
  - Affects: "shims" vs "stitching" vs "both"
  - Cleanup: "auto" vs "error" vs "ignore"

### 3. Update Other Documentation
- Update any other docs that reference `shim_mode`
- Ensure all terminology is consistent (module_mode, module_actions, shim setting)

### 4. Remove/Update ROADMAP Items
- Remove any ROADMAP items that are now implemented
- Keep only future enhancements (glob patterns, etc.)

## Notes
- This documents the complete feature
- All functionality is documented
- Examples show real-world usage

## Testing
- Run `poetry run poe check:fix` - must pass
- Documentation is clear and complete
- Examples are accurate and tested

## Commit Message
```
docs: update configuration reference for module_actions

- Add comprehensive module_actions documentation
- Document module_mode (renamed from shim_mode)
- Document shim setting (all/public/none)
- Add examples for all action types and parameters
- Document scope, affects, and cleanup behavior
- Update terminology throughout documentation
```

