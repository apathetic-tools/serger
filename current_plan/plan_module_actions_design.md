# Plan: Module Actions (Rename/Move/Copy/Delete)

## Overview

Add fine-grained control over package/module organization, allowing users to rename, move, copy, or delete specific parts of the module hierarchy. Module actions can affect shim generation, stitching, or both (via `affects` key).

**Important**: Module actions can affect both shim generation and stitching (via `affects: "shims" | "stitching" | "both"`). The include/exclude system controls initial file selection. See Section 18 for details on the relationship between module actions and include/exclude.

### 0. Feature Naming and Shim Setting

#### 0.1. Decision: Feature Renamed to Module Actions

**Decision**: The feature has been renamed from "module actions" to "module actions" to reflect that it operates on modules and can affect both shims and stitching.

**Changes**:
- `module_mode` → `module_mode` (convenience presets that generate actions)
- `module_actions` → `module_actions` (user-specified actions)
- `ModuleAction*` types → `ModuleAction*` types
- All terminology updated to use "module" instead of "shim" for this feature

**Rationale**:
- **More accurate**: Feature operates on modules (files), not just shims
- **Affects both domains**: Can affect shims AND stitching (via `affects` key)
- **Clearer**: "Module" maps to both file-based stitching and package-based shims
- **Consistent**: Matches codebase terminology (modules are the atomic unit)

#### 0.2. Decision: Shim Setting

**Decision**: `shim: "all" | "public" | "none"` (default `"all"`) - Controls whether shims are generated and which modules get shims.

**Values**:
- `"all"` (default) - Generate shims for all modules
- `"public"` - Only generate shims for public modules (future: based on `_` prefix or `__all__`)
- `"none"` - Don't generate shims at all

**Rationale**:
- **Single setting**: Combines on/off with mode selection
- **Clear values**: `"none"` is explicit, `"all"` is default
- **Extensible**: Can add more values later if needed
- **No naming conflict**: Doesn't conflict with old `module_mode` values (multi, force, etc.)

**Example**:
```jsonc
{
  "shim": "all",  // or "public" or "none"
  "module_mode": "multi",  // convenience mode (generates module_actions internally)
  "module_actions": [
    {"source": "pkg1", "dest": "newpkg", "affects": "both"}
  ]
}
```

## Goals

1. **Rename/Move packages**: Change package names in module organization (e.g., `apathetic_logs` → `grinch`)
2. **Flatten subpackages**: Flatten all subpackages under a source package onto a destination
3. **Multi-level operations**: Support operations on subpackages, not just top-level packages
4. **Copy operations**: Allow copying modules to multiple locations
5. **Delete operations**: Hide specific parts of the module hierarchy from shims
6. **Validation**: Raise errors for invalid operations (conflicts, non-existent sources, etc.)

## Design Decisions

### 1. Configuration Location: Separate `module_actions` Setting

**Decision**: Use a new `module_actions` configuration setting, separate from `module_mode` and `package`.

**Rationale**:
- `package` is used for display_name, metadata, and other non-shim purposes - mixing shim-specific actions here would be confusing
- `module_mode` provides high-level presets (multi, force, unify, etc.) - actions provide fine-grained control
- Clear separation of concerns: `module_mode` = "global strategy/convenience preset", `module_actions` = "specific transformations/overrides"
- Internally, `module_mode` generates actions that are prepended to user-specified `module_actions`
- Both keys remain at the top level of the config for clarity and discoverability

### 2. Action Types

**Actions**: `move`, `copy`, `delete` (with `none` as alias for `delete`)

- **`move`**: Rename/relocate a package/module (source no longer exists in shims)
- **`copy`**: Duplicate a package/module to another location (source still exists)
- **`delete`/`none`**: Remove a package/module from shims entirely (not exposed)

### 3. Flattening Mode

**Mode parameter**: `preserve` (default) vs `flatten`

- **`preserve`** (default): Keep subpackage structure (e.g., `apathetic_logs.utils` → `grinch.utils`)
- **`flatten`**: Flatten all subpackages onto destination (e.g., `apathetic_logs.utils` → `grinch`)

### 4. Configuration Format

**Decision**: Support both dict and list formats for convenience.

**List format** (full control):
```jsonc
{
  "module_actions": [
    {
      "source": "apathetic_logs",
      "dest": "grinch",
      "action": "move",  // default: "move"
      "mode": "preserve"  // default: "preserve"
    },
    {
      "source": "apathetic_logs.utils",
      "dest": "grinch",
      "action": "move",
      "mode": "flatten"  // flatten onto grinch
    },
    {
      "source": "apathetic_logs.utils",
      "dest": "grinch.xmas.topper",
      "action": "move",
      "mode": "flatten"  // flatten onto nested path
    },
    {
      "source": "old_pkg.schema",
      "action": "delete"  // no dest needed
    }
  ]
}
```

**Dict format** (simple renames):
```jsonc
{
  "module_actions": {
    "apathetic_logs": "grinch",  // simple move, preserve mode
    "old_pkg.schema": null  // delete
  }
}
```

**Behavior**:
- **Simple dict format**: For quick renames (`{"old": "new"}` or `{"old": null}` for delete). Defaults to `scope: "shim"` (user actions).
- **List format**: For full control (action, mode, multi-level paths, explicit scope)

**Type definition**:
```python
ModuleActionSimple = dict[str, str | None]  # source -> dest (None = delete)
ModuleActionFull = TypedDict("ModuleActionFull", {
    "source": str,  # required
    "dest": NotRequired[str],  # required for move/copy, not for delete
    "action": NotRequired[Literal["move", "copy", "delete", "none"]],  # default: "move"
    "mode": NotRequired[Literal["preserve", "flatten"]],  # default: "preserve"
})
ModuleActions = ModuleActionSimple | list[ModuleActionFull]
```

### 5. Processing Order

**Order of operations** (Chosen approach - modes generate actions):
1. Detect packages and generate initial shim names from module structure
2. If `module_mode` is specified (and not "none" or "multi"), generate equivalent actions from the mode
3. Prepend mode-generated actions to user-specified `module_actions`
4. Apply all actions in order (mode-generated first, then user actions) to transform shim names
5. Generate shim code from transformed names

**Why this order?**
- **Unified implementation**: Modes generate actions internally, single code path for all transformations
- **User actions come after**: User-specified actions are applied after mode-generated ones, allowing overrides/refinements
- **Clearer mental model**: Modes are convenience shortcuts that generate actions
- **Easier to reason about**: All transformations go through the same action system
- **Better troubleshooting**: All actions visible in one place (mode-generated + user actions)

### 6. Relationship to `module_mode`

`module_mode` and `module_actions` work together: `module_mode` generates actions internally that are prepended to user-specified `module_actions`. This allows using `module_mode` for global strategy while `module_actions` provides specific overrides.

**Example**: 
- `module_mode: "multi"` + `module_actions: [{"source": "apathetic_logs", "dest": "grinch"}]`
- Result: All packages preserved (multi), but `apathetic_logs` specifically renamed to `grinch`

**Special cases**:
- `module_mode: "none"` + `module_actions`: Error or ignore actions (no shims will be generated)
- `module_mode: "flat"` + `module_actions`: Flat mode affects loose file detection before actions; document interaction carefully

#### 6.1. Decision: Keep Both Keys, Modes Generate Actions

**Decision**: Keep `module_mode` and `module_actions` as separate configuration keys. Internally, `module_mode` generates equivalent actions that are prepended to user-specified `module_actions`. All transformations go through a unified action processing pipeline.

**Implementation**:
1. If `module_mode` is specified (and not "none" or "multi"), generate equivalent actions from the mode
2. Prepend mode-generated actions to user-specified `module_actions`
3. Apply all actions in order (mode-generated first, then user actions)

### 7. Action Scope: Original Tree vs Transformed Tree

#### 7.1. Decision: Configurable Scope with Smart Defaults

**Decision**: Actions support a `scope` key that controls whether they operate on the original module tree or the transformed shim tree.

**Scope defaults**:
- **Mode-generated actions**: Always use `scope: "original"` (operate on original tree)
- **User actions**: Default to `scope: "shim"` (operate on transformed tree after mode actions)

**Rationale**:
- Modes "set up" the base transformation from original → shim tree
- User actions refine the resulting shim tree
- If `module_mode: "none"`, user actions need `scope: "original"` to create initial state

**Examples**:

**Mode + user actions (common case)**:
```jsonc
{
  "module_mode": "force",  // Generates actions with scope: "original"
  "module_actions": [
    {"source": "mypkg.pkg1", "dest": "custom"}  // scope: "shim" (default), operates on result
  ]
}
```

**No mode, start from scratch**:
```jsonc
{
  "module_mode": "none",
  "module_actions": [
    {"source": "pkg1", "dest": "new1", "scope": "original"},  // Must specify original
    {"source": "pkg2", "dest": "new2", "scope": "original"}
  ]
}
```

**Chaining user actions**:
```jsonc
{
  "module_actions": [
    {"source": "pkg1", "dest": "pkg2"},  // scope: "shim" (default)
    {"source": "pkg2", "dest": "pkg3"}   // scope: "shim" (default), pkg2 exists from previous
  ]
}
```

**Implementation**:
- Mode-generated actions are created with `scope: "original"` explicitly set
- User actions default to `scope: "shim"` if not specified
- Actions with `scope: "original"` are validated against original tree upfront
- Actions with `scope: "shim"` are validated incrementally after previous actions

### 8. Validation Rules

**Invalid operations should raise errors**:

1. **Source doesn't exist**: `{"source": "nonexistent.pkg"}` → Error
2. **Dest conflicts with existing**: `{"source": "pkg1", "dest": "pkg2"}` when `pkg2` already exists → Error (unless `action: "copy"`)
3. **Circular moves**: `{"source": "a", "dest": "b"}, {"source": "b", "dest": "a"}` → Error
4. **Delete conflicts**: Can't delete something that's being moved/copied in same config
5. **Invalid dest for delete**: `{"source": "pkg", "action": "delete", "dest": "something"}` → Error (dest not allowed for delete)
6. **Missing dest for move/copy**: `{"source": "pkg", "action": "move"}` → Error

**Validation timing** (Hybrid approach):
- **`scope: "original"` actions**: Validate upfront for the entire plan (at least check that sources exist in original module tree). Further validations (conflicts, circular moves, etc.) can happen incrementally as we go.
- **`scope: "shim"` actions**: Validate incrementally (after previous actions with same or earlier scope)
- After combining mode-generated actions (scope: "original") with user actions (default scope: "shim"), validate in order

### 9. Implementation Details

#### 9.1. Action Processing Functions

**Main action processing**:
```python
def apply_module_actions(
    shim_names: list[str],  # Initial module names
    actions: list[ModuleActionFull],  # Parsed actions
    detected_packages: set[str],
) -> list[str]:
    """
    Apply module actions to transform module names.
    
    Returns transformed shim_names list.
    Raises ValueError for invalid operations.
    """
```

**Action generation from modes**:
```python
def generate_actions_from_mode(
    module_mode: str,
    detected_packages: set[str],
    package_name: str,
) -> list[ModuleActionFull]:
    """
    Generate module_actions equivalent to a module_mode.
    
    Converts module_mode presets into explicit actions that are prepended to
    user-specified actions. Returns list of actions that would produce the
    same result as the mode.
    """
```

**Mode-to-actions mapping**:
- `"force"`: For each detected root package (except `package_name`), generate `{"source": pkg, "dest": package_name, "mode": "preserve"}`
- `"force_flat"`: For each detected root package (except `package_name`), generate `{"source": pkg, "dest": package_name, "mode": "flatten"}`
- `"unify"`: For each detected package (except `package_name`), generate `{"source": pkg, "dest": f"{package_name}.{pkg}", "mode": "preserve"}`
- `"unify_preserve"`: Same as `"unify"` (preserve is default)
- `"multi"`: Return empty list (no actions needed - default behavior)
- `"none"`: Return empty list (no shims, handled separately)
- `"flat"`: Cannot be expressed as actions (requires file-level detection)

**Algorithm for `apply_module_actions`**:
1. Parse actions (normalize simple dict to list format, set default scope: "shim" for user actions)
2. Separate actions by scope: `scope: "original"` vs `scope: "shim"`
3. Validate `scope: "original"` actions upfront (check sources exist in original tree)
4. Apply `scope: "original"` actions to create initial transformed state
5. Validate `scope: "shim"` actions incrementally (check sources exist after previous actions)
6. Apply `scope: "shim"` actions to further transform
7. Handle package creation (if dest path doesn't exist, create intermediate packages)

#### 9.2. Name Transformation Logic

**For `move` with `preserve` mode**:
- `apathetic_logs` → `grinch` (root rename)
- `apathetic_logs.utils` → `grinch.utils` (subpackages preserved)
- `apathetic_logs.utils.text` → `grinch.utils.text`

**For `move` with `flatten` mode**:
- `apathetic_logs.utils` → `grinch` (flattened)
- `apathetic_logs.utils.text` → `grinch.text` (flattened)
- `apathetic_logs.utils.schema.validator` → `grinch.validator` (all intermediate levels flattened)

**For `copy`**:
- Source remains in original location
- Also appears at destination (with preserve/flatten logic)

**For `delete`**:
- Remove from shim_names entirely
- Also remove all subpackages/modules under it

#### 9.3. Package Path Creation

When destination path doesn't exist (e.g., `grinch.xmas.topper`), we need to:
1. Create intermediate package shims (`grinch`, `grinch.xmas`, `grinch.xmas.topper`)
2. Ensure parent-child relationships are set up correctly
3. This happens during shim generation (existing `_create_pkg_module` logic handles this)

#### 9.4. Integration Point

**Location**: `src/serger/stitch.py` in `_build_final_script()`

**Implementation flow** (modes generate actions with scope):
```python
# After detecting packages and initial module names
shim_names = [...]  # Initial module names from structure
original_shim_names = shim_names.copy()  # Keep original for scope: "original" validation

# Generate actions from module_mode if specified (all have scope: "original")
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
    validate_actions(original_scope_actions, original_shim_names, detected_packages)
    shim_names = apply_module_actions(
        shim_names, 
        original_scope_actions, 
        detected_packages
    )

# Validate and apply scope: "shim" actions (incremental validation)
if shim_scope_actions:
    for action in shim_scope_actions:
        validate_action(action, shim_names, detected_packages)  # Incremental
        shim_names = apply_single_action(shim_names, action, detected_packages)

# Continue with existing shim generation...
```

**Note**: This approach requires refactoring existing `module_mode` logic to generate actions instead of directly transforming names. This provides a cleaner, unified implementation where all transformations go through the action processing pipeline with proper scope handling.

### 10. Type Definitions

**Add to `src/serger/config/config_types.py`**:

```python
ModuleActionType = Literal["move", "copy", "delete", "none"]
ModuleActionMode = Literal["preserve", "flatten"]
ModuleActionScope = Literal["original", "shim"]
ModuleActionAffects = Literal["shims", "stitching", "both"]
ModuleActionCleanup = Literal["auto", "error", "ignore"]

class ModuleActionFull(TypedDict, total=False):
    source: str  # required - module name
    source_path: NotRequired[str]  # optional - filesystem path to module file (for re-including excluded modules)
    dest: NotRequired[str]  # required for move/copy
    action: NotRequired[ModuleActionType]  # default: "move"
    mode: NotRequired[ModuleActionMode]  # default: "preserve"
    scope: NotRequired[ModuleActionScope]  # default: "shim" for user actions, "original" for mode-generated
    affects: NotRequired[ModuleActionAffects]  # default: "shims" for backward compatibility
    cleanup: NotRequired[ModuleActionCleanup]  # default: "auto" for handling shim-stitching mismatches

# Simple format: dict[str, str | None]
# Full format: list[ModuleActionFull]
ModuleActions = dict[str, str | None] | list[ModuleActionFull]
```

**Add to `BuildConfig`**:
```python
module_actions: NotRequired[ModuleActions]
```

**Add to `BuildConfigResolved`**:
```python
module_actions: list[ModuleActionFull]  # Always present, empty list if not provided
```

### 11. Examples

#### Example 1: Simple rename (original tree)
```jsonc
{
  "package": "mypkg",
  "module_mode": "multi",
  "module_actions": {
    "apathetic_logs": "grinch"
  }
}
```
Result: `apathetic_logs` → `grinch`, `apathetic_logs.utils` → `grinch.utils`

#### Example 2: Flatten subpackage
```jsonc
{
  "module_actions": [
    {
      "source": "apathetic_logs.utils",
      "dest": "grinch",
      "mode": "flatten"
    }
  ]
}
```
Result: `apathetic_logs.utils` → `grinch`, `apathetic_logs.utils.text` → `grinch.text`

#### Example 3: Multi-level flatten
```jsonc
{
  "module_actions": [
    {
      "source": "apathetic_logs.utils",
      "dest": "grinch.xmas.topper",
      "mode": "flatten"
    }
  ]
}
```
Result: `apathetic_logs.utils` → `grinch.xmas.topper`, creates intermediate packages

#### Example 4: Delete specific subpackage
```jsonc
{
  "module_actions": [
    {
      "source": "apathetic_logs.utils.schema",
      "action": "delete"
    }
  ]
}
```
Result: `apathetic_logs.utils.schema` and all submodules removed from shims

#### Example 5: Copy to multiple locations
```jsonc
{
  "module_actions": [
    {
      "source": "common.utils",
      "dest": "pkg1.utils",
      "action": "copy"
    },
    {
      "source": "common.utils",
      "dest": "pkg2.utils",
      "action": "copy"
    }
  ]
}
```

#### Example 6: Combined with module_mode
```jsonc
{
  "package": "mypkg",
  "module_mode": "multi",  // Preserve all packages (generates no actions)
  "module_actions": [
    {"source": "old_pkg", "dest": "new_pkg"},  // scope: "shim" (default), operates on preserved packages
    {"source": "unwanted", "action": "delete"}  // scope: "shim" (default)
  ]
}
```
Result: All packages preserved (multi mode generates no actions), then user actions (scope: "shim") rename `old_pkg` to `new_pkg` and delete `unwanted`

#### Example 7: Mode with tidying actions
```jsonc
{
  "package": "mypkg",
  "module_mode": "force",  // Generates actions with scope: "original" to move all root packages to mypkg
  "module_actions": [
    {"source": "mypkg.pkg1", "dest": "custom"},  // scope: "shim" (default), operates on transformed result
    {"source": "mypkg.unwanted.sub", "action": "delete"}  // scope: "shim" (default)
  ]
}
```
Result: Mode-generated actions (scope: "original") move all packages to `mypkg`, then user actions (scope: "shim") rename `mypkg.pkg1` to `custom` and delete `mypkg.unwanted.sub`

#### Example 8: No mode, start from scratch
```jsonc
{
  "module_mode": "none",
  "module_actions": [
    {"source": "pkg1", "dest": "new1", "scope": "original"},  // Must specify original
    {"source": "pkg2", "dest": "new2", "scope": "original"}
  ]
}
```
Result: No mode actions, user actions with `scope: "original"` create initial shim structure

### 12. Testing Strategy

**Unit tests** (`tests/5_core/test_module_actions.py`):
- Simple rename (dict format)
- Flatten with flatten mode
- Multi-level paths
- Delete operations
- Copy operations
- Scope behavior: `scope: "original"` vs `scope: "shim"` (default)
- Scope validation: original scope validated upfront, shim scope validated incrementally
- Mode-generated actions have `scope: "original"`
- User actions default to `scope: "shim"`
- Convenience dict format defaults to `scope: "shim"`
- Validation errors (conflicts, missing sources, etc.)
- Interaction with module_mode

**Integration tests** (`tests/9_integration/test_module_actions_integration.py`):
- End-to-end: config → stitched file → import test
- Verify shims work correctly after transformations
- Verify deleted modules are not accessible
- Verify copied modules work in both locations
- Mode + user actions with different scopes
- `module_mode: "none"` + user actions with `scope: "original"`

### 13. Documentation

**Update `docs/configuration-reference.md`**:
- Add `module_actions` section
- Explain relationship to `module_mode`
- Document `scope` key: defaults, when to use `"original"` vs `"shim"`
- Explain that mode-generated actions use `scope: "original"`, user actions default to `scope: "shim"`
- Explain that `module_mode: "none"` requires `scope: "original"` in user actions
- Provide examples for common use cases (mode + actions, no mode, chaining)
- Document validation rules and error messages

### 14. Compatibility with Existing Code

- **`module_actions` is optional**: Can be added to existing configs
- **`module_mode` behavior preserved**: Modes generate the same results, but now through action generation internally
- **Can be used together**: `module_mode` and `module_actions` can coexist in the same config
- **Config format unchanged**: Existing configs using `module_mode` continue to work without modification

### 15. Code Organization

**New files**:
- `src/serger/module_actions.py` - Action processing logic
  - `parse_module_actions()` - Normalize config to internal format
  - `validate_module_actions()` - Check for errors
  - `apply_module_actions()` - Transform shim names
  - `generate_actions_from_mode()` - Convert module_mode to equivalent actions

**Modified files**:
- `src/serger/config/config_types.py` - Add type definitions
- `src/serger/config/config_resolve.py` - Resolve module_actions config
- `src/serger/stitch.py` - Refactor `module_mode` logic to use `generate_actions_from_mode()`, integrate action processing
- `docs/configuration-reference.md` - Document feature

### 16. Edge Cases

1. **Empty actions**: `module_actions: []` or `module_actions: {}` → No-op
2. **Action on non-existent source**: Error during validation
3. **Action creates duplicate names**: Error (unless copy)
4. **Action on already-transformed name**: Apply in order (first wins, or error if conflict)
5. **Nested actions**: `{"source": "a", "dest": "b"}, {"source": "b.x", "dest": "c"}` → Process in order
6. **Delete then move**: Delete removes, move won't find source → Error
7. **Move then copy same source**: First move removes, copy won't find → Error (validate all at once)

### 17. Glob Pattern Support

**Decision**: No glob pattern support for initial implementation.

**Rationale**:
- Adds significant complexity for validation, error handling, and user understanding
- Most use cases can be handled with explicit actions
- Can be added later without breaking changes

**Future Phases** (see ROADMAP.md):
- **Phase 1**: Simple wildcards in convenience dict format (e.g., `{"old_*": "new_*"}`)
- **Phase 2**: Globs in list format `source` key
- **Phase 3**: Advanced patterns with multiple wildcards and named captures

### 18. Module Actions and Include/Exclude Relationship

**Key Insight**: Include/exclude and module actions operate in different domains:
- **Include/exclude**: Works on **filesystem paths** - we need to know where files are located
- **Module actions**: Works on **package/module tree** - which doesn't exist until we have files

**Decision**: Keep both systems. Include/exclude determines initial file set, then package tree is generated. Module actions can affect both shims and stitching via the `affects` key.

**Configurable `affects` Key**:
- Add `affects` key to actions: `"shims" | "stitching" | "both"`
- Default: `"shims"` for backward compatibility
- Each action can specify what it affects

**Syntax**:
```jsonc
{
  "module_actions": [
    {"source": "internal.utils", "action": "delete", "affects": "both"},  // Remove from both
    {"source": "pkg1", "dest": "newpkg", "affects": "shims"},  // Only affect shims (default)
    {"source": "test_utils", "action": "delete", "affects": "stitching"}  // Only remove from stitching
  ]
}
```

**Implementation**:
- Track module-to-file mapping
- Separate actions by `affects` value
- Apply shim-only actions to shim generation
- Apply stitching-only or both actions to determine final file set

**Edge Case Handling**:

**1. File with mixed modules**: If file contains both visible and deleted modules, stitch the entire file (simpler approach)

**2. Copy actions**: Stitch once (copy only affects shim paths, not source files)

**3. Move actions**: Stitch once (move only affects shim paths, source file still stitched)

**4. Conflicting affects**: If same module has both shims-only and stitching-only actions, apply both independently

**5. Shim-Stitching Mismatch (Critical Edge Case)**:

**Problem**: If a module is deleted from stitching (`affects: "stitching"`), but a shim still points to it (from mode-generated actions or other shim-only actions), the shim will point to a non-existent module.

**Example**:
```jsonc
{
  "module_mode": "multi",  // Generates shims for all packages
  "module_actions": [
    {"source": "internal.utils", "action": "delete", "affects": "stitching"}  // Delete from stitching only
  ]
}
// Problem: shim for internal.utils exists, but module doesn't exist in stitched code
```

**Decision**: Per-action `cleanup` key (`"auto" | "error" | "ignore"`), default `"auto"`

**Implementation**:
- Add `cleanup` key to `ModuleActionFull` TypedDict: `"auto" | "error" | "ignore"`
- Default: `"auto"` for all actions
- After applying all actions, check for shims pointing to deleted modules
- For each action that creates a mismatch:
  - `"auto"`: Delete broken shims (with optional warning)
  - `"error"`: Raise error if this action creates broken shims
  - `"ignore"`: Keep broken shims (advanced use case)

**Example**:
```jsonc
{
  "module_actions": [
    {"source": "internal.utils", "action": "delete", "affects": "stitching", "cleanup": "auto"},  // Auto-delete broken shims
    {"source": "test_utils", "action": "delete", "affects": "stitching", "cleanup": "error"},  // Error if shim exists
    {"source": "debug", "action": "delete", "affects": "stitching", "cleanup": "ignore"}  // Keep broken shim
  ]
}
```

### 19. Specifying Filesystem Paths in Actions

**Decision**: Support optional `source_path` key in actions to reference modules that weren't included initially or were excluded.

**Use Case**: "Go back and include this module that was excluded, or reference a module from a different location"

**Example**:
```jsonc
{
  "include": ["src/**/*.py"],
  "exclude": ["src/internal/**/*.py"],  // Excluded internal modules
  "module_actions": [
    {
      "source": "internal.utils",
      "source_path": "src/internal/utils.py",  // Specify filesystem path
      "dest": "public.utils",
      "affects": "both"  // Re-include this module
    }
  ]
}
```

**Implementation**:
- Add optional `source_path: str` to `ModuleActionFull`
- If `source_path` is specified:
  - Validate file exists and is parseable
  - Extract module name from file (must match `source` or be derivable)
  - Add file to stitching set if `affects` includes "stitching"
  - Use module in action processing
- If `source_path` not specified, use existing behavior (module from included files)

**Edge Cases**:
- **Path doesn't exist**: Error during validation
- **Module name mismatch**: `source` must match module name from file, or error
- **Already included**: If file is already in include set, use existing behavior (no duplicate)
- **Conflicts with exclude**: `source_path` overrides exclude for that specific file

### 20. Future Considerations

**Potential enhancements** (not in initial implementation):
- Pattern matching for sources (e.g., `"apathetic_*"` → `"grinch_*"`) - see section 17
- Conditional actions based on package detection
- Action ordering control (currently process in config order)
- Wildcard destinations (see section 16 for challenges)
- Optional stitching control via module actions (see section 18.4)
- Optional `source_path` for re-including excluded modules (see section 19)

## Summary

This plan provides a flexible, well-validated system for fine-grained module manipulation, while maintaining clear separation from existing `module_mode` functionality. The system can be implemented with or without `module_mode` depending on design goals.

