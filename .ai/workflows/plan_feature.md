# Plan Document Format Specification

## When to Use This Format

This format is designed for **complex changes** that require careful planning and coordination with AI assistance. Consider using this format when:

- **Use this format for:**
  - Complex features or refactors
  - API changes or breaking changes
  - Multi-file changes requiring coordination
  - Changes affecting multiple subsystems
  - Changes requiring design decisions
  - Changes where order of operations matters

- **Optional/simpler format for:**
  - Simple bug fixes
  - Documentation-only changes
  - Trivial one-line changes
  - Changes with clear, single-path solutions

## File Naming

- Format: `XXX_<summary>.md` where:
  - `XXX` is a 3-digit number (001, 002, etc.)
  - `<summary>` is a brief description of the feature or topic
  - Example: `001_make_get_app_logger_safe.md`
- Numbering:
  - Use the next available number higher than existing plans
  - Check `.plan/` directory for existing plans
  - If no plans exist, start with `001`

## File Management

**First step when working with plans**: Before creating or updating any plan document, check for old plan files:
- Check `.plan/` directory for plan files (`XXX_*.md` where XXX is a 3-digit number)
- If plan files older than 24 hours exist, ask the developer if they should be deleted
- This keeps the active plans directory clean and focused on current work

## Using the Template

**For AI assistants**: When creating a new plan document, start by copying `.ai/templates/plan_feature.tmpl.md` and filling in the structure. The template follows this specification (`.ai/workflows/plan_feature.md`). The template provides:
- All required phases with proper structure
- Quick reference checklist pre-populated
- Standard phase actions and checkpoints
- Consistent formatting

This ensures new plans follow the format specification and include all required elements.

## Document Structure

Each plan document must be organized into **phases**. Phases should be clearly marked with headers (e.g., `## Phase 1: Design Questions`).

**Quick Reference Checklist**: Include a phase checklist at the top of the document (after Summary/Context) showing all phases and their completion status. Update this checklist as the last action in each phase.

**Living Document**: The plan is updated in real-time as work progresses. Document decisions, progress, and blockers as they occur.

## Required Phases

### Phase 1: Design Questions
**Always the first phase.**

- Identify all design questions that need developer input
- List questions clearly
- Include context for each question if needed
- Do not proceed to implementation until all questions are answered

### Phase 2: Developer Q&A
**Always the second phase.**

- Ask questions **one at a time** in sequence
- For each question:
  - Present the question clearly
  - Provide all available choices/options
  - Include any necessary reasoning or context
  - Provide your recommendations
  - **Wait for developer response before proceeding**
- Handle follow-ups:
  - If developer asks a follow-up question instead of answering:
    - Add the follow-up to the question list
    - Treat it as the "current question"
    - Answer the follow-up
    - Return to the previous unanswered question
- Verify all questions answered:
  - Verify all questions from Phase 1 have been answered
  - If any remain unanswered, go back and ask them one at a time
  - Do not proceed until all questions are resolved
- **Final question (must be last in Phase 2):**
  - Ask the developer: "Are you ready to proceed with implementation, or do you have additional questions?"
  - Wait for confirmation before proceeding to Phase 3
  - If developer has additional questions, treat them as follow-ups and add to the question list

### Phase 3: Baseline Check
**Always the third phase.**

- Run `poetry run poe check:fix` to identify pre-existing problems
- Document all issues found
- **Stop and ask the developer** what to do about pre-existing issues
- **After this phase, all errors are related to your changes** - fix all errors, even in untouched files
- Developer options:
  - Fix pre-existing issues first (add as new phase)
  - Proceed and document that issues were pre-existing
  - Create separate issue/ticket for pre-existing problems
  - Abandon plan if issues are blocking
- Do not proceed until developer provides direction

### Phase N-2: Additional Tests
**Always the second-to-last phase.**

- Review if additional tests should be added
- Consider edge cases, error conditions, and integration scenarios
- Document any test additions needed
- Implement tests if required

### Phase N-1: Documentation Updates
**Always the second-to-last phase.**

- Review what documentation needs updating:
  - API docs (`docs/api.md`) - update both snake_case and CamelCase versions
  - Examples (`docs/examples.md`)
  - README if needed
  - Other relevant docs
- Update relevant documentation files
- Ensure examples and API docs reflect changes
- Document any breaking changes or migration paths

### Phase N: Final Verification
**Always the final phase.**

- Run `poetry run poe check:fix` one final time
- Verify all checks pass (linting, type checking, tests)
- Confirm implementation is complete
- Document any remaining issues or follow-up work
- Update quick reference phase checklist

### Phase N+1: Process Improvement Recommendations
**Always the very last phase (after Final Verification).**

- Review the plan execution process
- Recommend improvements to `.ai/workflows/plan_feature.md` (don't implement, just recommend)
- Recommend changes to `.ai/rules/` and `.ai/commands/` that would reduce problems (don't implement, just recommend)
- These recommendations help improve the format and AI guidance for future plans

## Implementation Phases

Between Phase 3 and the final three phases, add implementation phases as needed:

- Each implementation phase should be focused on a specific aspect of the change
- **Phase granularity guidance:**
  - Too granular: Each function/method gets its own phase (e.g., "Phase 4: Add constant", "Phase 5: Add registry field")
  - Just right: Logical units of work (e.g., "Phase 4: Registry Storage" includes constant, registry field, setup)
  - Too coarse: Multiple unrelated changes in one phase (e.g., "Phase 4: Implement entire feature")
- **Error handling:** After Phase 3 (Baseline Check), all errors are related to your changes. Even if a file appears untouched, your changes may have introduced the error or require updates elsewhere. Only pre-existing errors (from before Phase 3) are unrelated.
- Document what was done in each phase
- **End of phase actions:**
  - Run `poetry run poe check:fix`
  - If all errors are resolved, commit the phase
  - **Update the quick reference phase checklist at the top of the document** (required, not optional)
- **Mid-implementation design changes:**
  - If a design decision needs reconsideration, pause and return to Phase 2 (Developer Q&A)
  - Document the change and rationale
  - Update affected phases if needed
  - Treat as refinement, not blocker
- **Feature additions during implementation:**
  - If a related feature is requested, assess if it fits the current plan
  - If it fits: Add as new implementation phase
  - If it doesn't fit: Ask the developer what to do (add to plan or split off) and wait for decision
  - Don't auto-create separate plans
- **Scope change handling:**
  - Minor refinement: Update current phase and continue
  - Significant change: Return to Phase 2 (Q&A)
  - Major expansion: Ask developer if it should be a separate plan

## General Guidelines

### Keep Plan Updated
- **Always** keep the plan document up to date
- Document decisions made during Q&A
- Record implementation progress
- Note any issues or blockers encountered
- Update status as work progresses

### Phase Completion
- Each phase should be clearly marked as complete or in progress
- Use checkboxes or status indicators (e.g., `[ ]`, `[x]`, `✅`, `⏳`)
- Document completion dates if relevant

### Clarity and Organization
- Use clear section headers
- Break complex phases into sub-phases if needed
- Use bullet points or numbered lists for clarity
- Include code examples where helpful
- Reference related files and line numbers

### Plan Document Lifecycle
- **Living document**: Update the plan as you progress through phases
- Document decisions, blockers, and deviations in real-time
- Mark phases as complete/in-progress/blocked
- If deviating from plan, document why and get approval
- The plan serves as both blueprint and progress tracker

### Handling Blockers and Abandonment
- **When blocked:**
  - Document the blocker clearly
  - Identify if it's temporary or permanent
  - Ask developer for direction (wait, workaround, or abandon)
- **When abandoning:**
  - Document what was completed
  - Document why it was abandoned
  - Note what would be needed to resume later
  - Mark plan as "Abandoned" with reason

### Commit Strategy
- **Commit after each phase** if `poetry run poe check:fix` passes with all errors resolved (including unrelated ones)
- Use descriptive commit messages referencing the plan number
- Create WIP commits for long-running phases if needed
- Follow project's git conventions (see `git_conventions.mdc`)

### Optional Sections to Consider
- **Dependencies**: External dependencies, blocking issues, prerequisites
- **Risk Assessment**: High-risk areas, potential breaking changes, areas needing extra testing

## Example Structure

```markdown
# Plan: <Title>

## Summary
Brief overview of the change.

## Context
Why this change is needed.

## Quick Reference - Phase Checklist
- [ ] Phase 1: Design Questions
- [ ] Phase 2: Developer Q&A
- [ ] Phase 3: Baseline Check
- [ ] Phase 4: Implementation - <Aspect 1>
- [ ] Phase 5: Implementation - <Aspect 2>
- [ ] Phase N-2: Additional Tests
- [ ] Phase N-1: Documentation Updates
- [ ] Phase N: Final Verification
- [ ] Phase N+1: Process Improvement Recommendations

## Phase 1: Design Questions
- [ ] Question 1
- [ ] Question 2

## Phase 2: Developer Q&A
- [x] Question 1 answered
- [ ] Question 2 pending
- [ ] Final: Ready to proceed? (must be last)

## Phase 3: Baseline Check
- [ ] Run check:fix
- [ ] Document issues
- [ ] Get developer direction

## Phase 4: Implementation - <Aspect 1>
- [ ] Step 1
- [ ] Step 2
- [ ] Verify check:fix passes

## Phase 5: Implementation - <Aspect 2>
- [ ] Step 1
- [ ] Step 2
- [ ] Verify check:fix passes

## Phase N-2: Additional Tests
- [ ] Review test coverage
- [ ] Add tests as needed

## Phase N-1: Documentation Updates
- [ ] Update relevant docs
- [ ] Review examples

## Phase N: Final Verification
- [ ] Run check:fix
- [ ] Verify all checks pass
- [ ] Mark complete
- [ ] Update quick reference checklist

## Phase N+1: Process Improvement Recommendations
- [ ] Review plan execution
- [ ] Recommend plan_feature.md improvements
- [ ] Recommend .ai/rules and .ai/commands changes
```

