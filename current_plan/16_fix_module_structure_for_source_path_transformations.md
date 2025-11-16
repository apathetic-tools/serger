# Iteration 16: Fix Module Structure for `source_path` Transformations
> **Context**: See `current_plan/00_overview.md` for overall strategy and principles.

## Goal
Fix the module structure creation when `source_path` files are transformed using `scope: "original"` actions. The test `test_source_path_end_to_end_excluded_to_stitched` currently fails because transformed module names are used for the structure, but the actual module objects in `globals()` are still registered with original names.

## Background

In iteration 15, we implemented the `source_path` feature to allow re-including excluded files. However, there's a remaining issue with module structure creation when `scope: "original"` actions are applied to `source_path` files.

**Current behavior**:
- Headers are correctly updated with transformed names (e.g., `# === public.utils ===`)
- Module structure is built using `transformed_order_names` (e.g., `mypkg.public.utils`)
- But module objects in `globals()` are still registered with original names (e.g., `mypkg.utils`)
- When `_setup_pkg_modules()` tries to set up the structure, it can't find the module objects because they're registered with different names

**Expected behavior**:
- Module objects should be accessible via transformed names (e.g., `module.public.utils`)
- The module structure should match the transformed names used in headers
- Both original and transformed names should work (for backward compatibility)

## Problem Analysis

The issue occurs in `build_final_script()` in `src/serger/stitch.py`:

1. **Header updates** (lines 1829-1890): `transformed_order_names` is computed and headers are updated correctly ✓
2. **Shim generation** (lines 1892+): `shim_names` is built from original names (for shim generation) ✓
3. **Module structure** (lines 2227-2270): `module_names_for_structure` uses `transformed_order_names` if available, but:
   - `transformed_order_names` contains names relative to `package_root` (e.g., `"public.utils"`)
   - These are converted to full paths (e.g., `"mypkg.public.utils"`)
   - But `_setup_pkg_modules()` expects modules to exist in `sys.modules` with these names
   - The actual module objects in `globals()` are registered with original names (e.g., `"mypkg.utils"`)

**Root cause**: Module objects are registered in `sys.modules` during stitching with original names, but the module structure setup tries to use transformed names.

## Changes

### 1. Register Modules with Transformed Names (`src/serger/stitch.py`)

When `scope: "original"` actions are applied, modules should be registered in `sys.modules` with both original and transformed names.

**Location**: In `build_final_script()`, after header updates and before shim generation

**Implementation**:
```python
# After header updates (around line 1890)
# If transformed_order_names is available, create a mapping from original to transformed names
if transformed_order_names is not None:
    # Build mapping: original_name -> transformed_name
    name_mapping: dict[str, str] = {}
    for i, original_name in enumerate(order_names):
        if i < len(transformed_order_names):
            transformed_name = transformed_order_names[i]
            if transformed_name != original_name:
                name_mapping[original_name] = transformed_name
    
    # Store mapping for use in module registration
    # (will be used when registering modules in sys.modules)
```

### 2. Update Module Registration Logic (`src/serger/stitch.py`)

When modules are registered in `sys.modules` via `_setup_pkg_modules()`, also register them with transformed names if available.

**Location**: In shim generation code, when `_setup_pkg_modules()` is called (around line 2358)

**Current code**:
```python
shim_blocks.append(
    f"_setup_pkg_modules({pkg_name!r}, [{module_names_str}])"
)
```

**Updated code**:
```python
# Register modules with original names (for backward compatibility)
shim_blocks.append(
    f"_setup_pkg_modules({pkg_name!r}, [{module_names_str}])"
)

# If transformed names exist, also register modules with transformed names
# This allows module.public.utils to work when utils -> public.utils
if transformed_order_names is not None:
    # Convert transformed_order_names to full paths (same logic as before)
    transformed_full_names = [...]
    if transformed_full_names:
        transformed_module_names_str = ", ".join(repr(name) for name in transformed_full_names)
        # Register with transformed names
        shim_blocks.append(
            f"_setup_pkg_modules({pkg_name!r}, [{transformed_module_names_str}])"
        )
```

**Note**: This approach registers modules twice - once with original names and once with transformed names. This ensures backward compatibility while enabling the new structure.

### 3. Alternative Approach: Update `_setup_pkg_modules()` Logic

Instead of registering modules twice, update `_setup_pkg_modules()` to handle name mappings:

**Location**: In shim generation code, update the `_setup_pkg_modules()` function definition

**Implementation**:
```python
# Update _setup_pkg_modules() to accept optional name mapping
shim_blocks.append(
    "def _setup_pkg_modules("
    "pkg_name: str, module_names: list[str], "
    "name_mapping: dict[str, str] | None = None"
    ") -> None:"
)
shim_blocks.append(
    '    """Set up package module attributes and register submodules."""'
)
# ... existing code ...
shim_blocks.append("    # Register all modules under this package")
shim_blocks.append("    for _name in module_names:")
shim_blocks.append("        _mod = sys.modules.get(_name)")
shim_blocks.append("        if _mod:")
shim_blocks.append("            sys.modules[_name] = _mod")
shim_blocks.append("        elif name_mapping:")
shim_blocks.append("            # Try to find module by original name")
shim_blocks.append("            _original_name = name_mapping.get(_name)")
shim_blocks.append("            if _original_name:")
shim_blocks.append("                _mod = sys.modules.get(_original_name)")
shim_blocks.append("                if _mod:")
shim_blocks.append("                    # Register with transformed name")
shim_blocks.append("                    sys.modules[_name] = _mod")
```

**Then when calling**:
```python
# Build name mapping dict as string for shim code
if transformed_order_names is not None:
    name_mapping_dict = {}
    for i, original_name in enumerate(order_names):
        if i < len(transformed_order_names):
            transformed_name = transformed_order_names[i]
            if transformed_name != original_name:
                # Convert to full paths
                original_full = f"{package_name}.{original_name}"
                transformed_full = f"{package_name}.{transformed_name}"
                name_mapping_dict[transformed_full] = original_full
    
    name_mapping_str = (
        "{" + ", ".join(f"{k!r}: {v!r}" for k, v in name_mapping_dict.items()) + "}"
        if name_mapping_dict
        else "None"
    )
else:
    name_mapping_str = "None"

# Call with name mapping
shim_blocks.append(
    f"_setup_pkg_modules({pkg_name!r}, [{module_names_str}], {name_mapping_str})"
)
```

### 4. Handle Module Object Registration

The actual module objects in `globals()` are created during stitching with original names. We need to ensure they're also accessible via transformed names.

**Location**: In `_setup_pkg_modules()` logic, after registering in `sys.modules`

**Implementation**:
```python
# After registering in sys.modules, also set up the module structure
# This ensures module.public.utils works when utils -> public.utils
if name_mapping:
    for _transformed_name, _original_name in name_mapping.items():
        _mod = sys.modules.get(_original_name)
        if _mod:
            # Register with transformed name
            sys.modules[_transformed_name] = _mod
            # Set up parent-child relationships for transformed name
            _transformed_parts = _transformed_name.split(".")
            if len(_transformed_parts) > 1:
                _transformed_parent = ".".join(_transformed_parts[:-1])
                _transformed_child = _transformed_parts[-1]
                _parent_mod = sys.modules.get(_transformed_parent)
                if _parent_mod:
                    if not hasattr(_parent_mod, _transformed_child):
                        setattr(_parent_mod, _transformed_child, _mod)
```

### 5. Pass Name Mapping Through Function Calls

The `transformed_order_names` and name mapping need to be available when generating shims.

**Location**: In `build_final_script()`, pass name mapping to shim generation

**Current function signature**:
```python
def build_final_script(
    ...
    order_names: list[str],
    ...
) -> tuple[str, list[str]]:
```

**Updated approach**: Store name mapping as a variable in the function scope, then use it when generating shims.

## Implementation Strategy

### Option A: Register Modules Twice (Simpler)
- Register modules with both original and transformed names
- Pros: Simple, straightforward
- Cons: Duplicate registration, potential confusion

### Option B: Update `_setup_pkg_modules()` with Name Mapping (More Robust)
- Pass name mapping to `_setup_pkg_modules()`
- Function looks up modules by original name if transformed name not found
- Pros: More explicit, handles edge cases better
- Cons: More complex implementation

**Recommendation**: Start with Option A (simpler), then refactor to Option B if needed.

## Edge Cases

### 1. Multiple Transformations
- If multiple actions transform the same module, use the final transformed name
- Ensure name mapping reflects the final state after all transformations

### 2. Nested Transformations
- If `utils` -> `public.utils` and `public.utils` -> `api.public.utils`, handle both
- Build complete mapping chain

### 3. Circular References
- Should be caught by existing validation, but ensure no infinite loops

### 4. Module Not Found
- If transformed name doesn't map to an existing module, log warning but don't fail
- This can happen if module was deleted or filtered out

## Testing

### 1. Update Existing Test
- Fix `test_source_path_end_to_end_excluded_to_stitched` to verify module structure
- Ensure `module.public.utils` is accessible

### 2. Add Additional Tests
- Test with multiple transformations
- Test with nested transformations
- Test backward compatibility (original names still work)
- Test edge cases (module not found, circular references)

**Example test**:
```python
def test_source_path_transformed_module_structure(tmp_path: Path) -> None:
    """Test that transformed module names create correct structure."""
    # Setup similar to test_source_path_end_to_end_excluded_to_stitched
    # ...
    
    # Verify both original and transformed names work
    assert hasattr(module, "utils")  # Original name
    assert hasattr(module, "public")  # Transformed structure
    assert hasattr(module.public, "utils")  # Transformed name
    assert module.utils is module.public.utils  # Same object
```

## Notes

- **Backward compatibility**: Original module names should still work
- **Performance**: Name mapping lookup is O(1) dict lookup, minimal overhead
- **Clarity**: Name mapping should be clearly documented in code comments
- **Validation**: Ensure name mapping is consistent (no conflicts, valid names)

## Review and Clarifying Questions

**After implementing this iteration**, review the changes and document any questions:

1. **Review the implementation**:
   - Check that module structure is created correctly with transformed names
   - Verify backward compatibility (original names still work)
   - Test with multiple transformations
   - Check edge cases (module not found, circular references)

2. **Document any questions**:
   - Should we support both original and transformed names, or only transformed?
   - How should we handle conflicts if both original and transformed names exist?
   - Should we log warnings when modules aren't found?
   - Are there performance concerns with duplicate registration?

3. **Resolve before proceeding**:
   - Answer all questions before considering this feature complete
   - Update implementation if needed
   - Update documentation if behavior differs from plan

## Commit Message
```
fix(module_actions): fix module structure for source_path transformations

- Register modules with transformed names when scope: "original" actions applied
- Update _setup_pkg_modules() to handle name mappings for transformed modules
- Ensure module.public.utils works when utils -> public.utils transformation
- Add name mapping logic to connect original and transformed module names
- Fix test_source_path_end_to_end_excluded_to_stitched test
- Maintain backward compatibility with original module names
```

## Final Step: Update START_HERE.md

After completing this iteration, update `current_plan/START_HERE.md`:
- Mark iteration 16 as completed ✓
- Update the "Current status" section with what was accomplished
- Update "Next step" to point to next iteration (if any)
- Include a brief summary (e.g., "Fixed module structure creation for source_path transformations with scope: original actions")

