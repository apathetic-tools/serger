# Iteration 10: Integrate Module Actions into Stitch Logic

## Goal
Replace `module_mode` logic in `stitch.py` with `module_actions` processing. This is the main integration point.

## Changes

### 1. Update `stitch.py` (`src/serger/stitch.py`)
- In `_build_final_script()`, replace `shim_mode` logic with:
  1. Generate actions from `module_mode` (if specified and not "none"/"multi")
  2. Parse user-specified `module_actions` (if present)
  3. Combine mode-generated actions (scope: "original") with user actions (default scope: "shim")
  4. Separate actions by scope
  5. Validate and apply `scope: "original"` actions first
  6. Validate and apply `scope: "shim"` actions incrementally
  7. Use transformed module names for shim generation

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
    # All mode-generated actions have scope: "original"
    for action in auto_actions:
        action["scope"] = "original"
    all_actions.extend(auto_actions)

# Add user-specified module_actions (default scope: "shim")
if module_actions:
    explicit_actions = parse_module_actions(module_actions)
    # Set default scope: "shim" for user actions that don't specify scope
    for action in explicit_actions:
        if "scope" not in action:
            action["scope"] = "shim"
    all_actions.extend(explicit_actions)

# Separate actions by scope
original_scope_actions = [a for a in all_actions if a.get("scope") == "original"]
shim_scope_actions = [a for a in all_actions if a.get("scope") == "shim"]

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

### 3. Handle `shim` Setting
- Check `shim` setting from config:
  - `"none"`: Don't generate shims (skip shim generation entirely)
  - `"all"`: Generate shims for all modules (default, existing behavior)
  - `"public"`: Only generate shims for public modules (future: based on `_` prefix)

### 4. Update Function Signatures
- Update `_build_final_script()` to accept `module_actions` and `shim` from config
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

## Testing
- Run `poetry run poe check:fix` - must pass
- All existing tests should pass (with updated config)
- New integration tests pass
- Test that old `shim_mode` behavior is preserved when using equivalent `module_actions`

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

