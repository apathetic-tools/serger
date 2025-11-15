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
- **Iteration 03.5**: Resolve clarifying questions from iterations 01-03
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
- **Ask clarifying questions**: If design decisions are unclear, add a clarifying questions section to the iteration plan and resolve them before proceeding
- **Review at end of iteration**: After implementing changes and before committing, review the implementation for ambiguous decisions, edge cases, or unclear behavior. Document any new clarifying questions that arise and resolve them before proceeding to the next iteration.

## Clarifying Questions Pattern

When implementing iterations, if you encounter design decisions that need clarification:

1. **Add a "Clarifying Questions" section** to the iteration plan file
2. **Document the question** with context and options
3. **Create a separate iteration** (e.g., 03.5) if questions span multiple iterations or are critical
4. **Answer all questions** before proceeding to the next iteration
5. **Update implementation plans** based on the answers

Example structure:
```markdown
## Clarifying Questions

**Q: [Question title]**
- Context: [Why this question matters]
- **Decision needed**: [Options A, B, C]
- **Answer**: [To be determined - see iteration X.Y]
```

This ensures design decisions are made explicitly and documented, preventing confusion or rework later.

## Review and Clarifying Questions at End of Iteration

**Standard practice**: At the end of each iteration, after implementing changes and running tests:

1. **Review the implementation**:
   - Check for ambiguous behavior or edge cases
   - Verify the implementation matches the design decisions
   - Look for inconsistencies with existing code patterns
   - Identify any unclear or potentially problematic areas

2. **Document clarifying questions**:
   - Add a "Review and Clarifying Questions" section to the iteration file
   - Document any questions that arose during implementation
   - If questions are critical or affect multiple iterations, create a separate iteration (e.g., 03.5) to resolve them
   - If questions are minor, document them and answer them inline

3. **Resolve before proceeding**:
   - Answer all questions before moving to the next iteration
   - Update the implementation if needed based on answers
   - Update the next iteration's plan if decisions affect it

**Example structure for iteration files**:
```markdown
## Review and Clarifying Questions

After implementing this iteration, review the changes and document any questions:

**Q: [Question that arose during implementation]**
- Context: [What made this unclear]
- Options: [Possible approaches]
- Decision: [Answer or "To be resolved in iteration X.Y"]
```

This practice catches issues early and ensures each iteration is complete and unambiguous before moving forward.

