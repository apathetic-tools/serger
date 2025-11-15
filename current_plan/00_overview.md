# Module Actions Implementation Plan - Overview

This directory contains the iterative implementation plan for the Module Actions feature. Each iteration is designed to:

1. **Maintain code in codebase** - Even if not called, code needed later is preserved
2. **Update documentation** - End goal documented without extra ROADMAP items
3. **Small iterations** - Each passes `check:fix` and can be committed
4. **Good test coverage** - Unit tests for each section, integration tests at end
5. **Full implementation** - Complete feature at the end

## Iteration Strategy

### Phase 1: Foundation (Types, Config, Renaming)
- **Iteration 01**: Rename `shim_mode` → `module_mode` in types and config
- **Iteration 02**: Add `shim` setting types (`"all" | "public" | "none"`)
- **Iteration 03**: Add `module_actions` types (ModuleActionFull, ModuleActions)
- **Iteration 04**: Update config resolution to accept new keys (validation only, not used yet)

### Phase 2: Core Infrastructure
- **Iteration 05**: Create `module_actions.py` with parsing functions
- **Iteration 06**: Add validation functions (upfront and incremental)
- **Iteration 07**: Add basic action application functions (move, copy, delete)

### Phase 3: Mode-to-Actions Conversion
- **Iteration 08**: Create `generate_actions_from_mode()` function
- **Iteration 09**: Add tests for mode-to-actions conversion

### Phase 4: Integration
- **Iteration 10**: Integrate module_actions into stitch.py (replace shim_mode logic)
- **Iteration 11**: Add scope handling (`"original"` vs `"shim"`)
- **Iteration 12**: Add `affects` and `cleanup` handling

### Phase 5: Documentation and Final Tests
- **Iteration 13**: Update `configuration-reference.md` with end goal
- **Iteration 14**: Add comprehensive integration tests

## Principles

- **Early types**: Add types and accept config early, even if not implemented
- **Early validation**: Validate and resolve config early
- **Early renaming**: Rename `shim_mode` → `module_mode` early
- **Preserve code**: Keep code that will be needed later, even if not called
- **Test incrementally**: Add tests as we go, expand previous tests as we add features

