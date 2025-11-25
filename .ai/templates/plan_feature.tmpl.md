# Plan: <Title>

> **Note:** This template follows `.ai/workflows/plan_feature.md`. Read that file for complete specifications.

## Summary
Brief overview of the change.

## Context
Why this change is needed.

## Quick Reference - Phase Checklist
- [ ] Phase 1: Design Questions
- [ ] Phase 2: Developer Q&A
- [ ] Phase 3: Baseline Check
- [ ] Phase N-2: Additional Tests
- [ ] Phase N-1: Documentation Updates
- [ ] Phase N: Final Verification
- [ ] Phase N+1: Process Improvement Recommendations

## Phase 1: Design Questions

- [ ] Question 1: [Describe question]
- [ ] Question 2: [Describe question]

## Phase 2: Developer Q&A

- [ ] Question 1: [Status - answered/pending]
- [ ] Question 2: [Status - answered/pending]
- [ ] Final: Ready to proceed? (must be last)

## Phase 3: Baseline Check

- [ ] Run `poetry run poe check:fix`
- [ ] Document all issues found
- [ ] Get developer direction on pre-existing issues
- [ ] Update quick reference checklist

## Phase 4: Implementation - <Aspect 1>

- [ ] Step 1: [Describe step]
- [ ] Step 2: [Describe step]
- [ ] Run `poetry run poe check:fix`
- [ ] Resolve all errors (all errors after Phase 3 are related)
- [ ] Commit phase if check:fix passes
- [ ] Update quick reference checklist (required - last action)

## Phase N-2: Additional Tests

- [ ] Review test coverage
- [ ] Identify edge cases and error conditions
- [ ] Add tests as needed
- [ ] Run `poetry run poe check:fix`
- [ ] Commit if check:fix passes
- [ ] Update quick reference checklist

## Phase N-1: Documentation Updates

- [ ] Review what documentation needs updating:
  - API docs (`docs/api.md`) - update both snake_case and CamelCase versions
  - Examples (`docs/examples.md`)
  - README if needed
  - Other relevant docs
- [ ] Update relevant documentation files
- [ ] Ensure examples and API docs reflect changes
- [ ] Document breaking changes or migration paths if any
- [ ] Run `poetry run poe check:fix`
- [ ] Commit if check:fix passes
- [ ] Update quick reference checklist

## Phase N: Final Verification

- [ ] Run `poetry run poe check:fix` one final time
- [ ] Verify all checks pass (linting, type checking, tests)
- [ ] Confirm implementation is complete
- [ ] Document any remaining issues or follow-up work
- [ ] Update quick reference checklist

## Phase N+1: Process Improvement Recommendations

- [ ] Review plan execution process
- [ ] Recommend improvements to `.ai/workflows/plan_feature.md` (don't implement, just recommend)
- [ ] Recommend changes to `.ai/rules/` and `.ai/commands/` that would reduce problems (don't implement, just recommend)
- [ ] Update quick reference checklist

