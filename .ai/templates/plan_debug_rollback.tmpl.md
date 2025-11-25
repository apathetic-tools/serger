# Plan Format

Implementation plans should follow this structure:

```markdown
# Implementation Plan: [Brief Description]

## Overview
Brief description of what this plan covers.

## Last Passing Commit
- **Commit hash**: [to be determined]
- **Commit message**: [to be determined]
- **Date**: [to be determined]
- **Status**: [Found / Searching]

## Phases/Features/Changes Since Last Passing Commit

### Phase 1: [Name]
- Description of what this phase covers
- Files likely affected
- Expected outcome

### Phase 2: [Name]
- ...

## Implementation Tasks

### Task 1: Find Last Passing Commit
- [ ] Check git history for last commit where tests passed
- [ ] Verify with `poetry run poe check:fix`
- [ ] Document commit hash, message, and date

### Task 2: Analyze Changes Since Last Passing Commit
- [ ] Review commits between last passing commit and current state
- [ ] Review stashed changes
- [ ] List all phases/features/changes
- [ ] Present summarized list to user for approval

### Task 3: [First Feature/Change]
- [ ] [Subtask 1]
- [ ] [Subtask 2]
- [ ] Run tests: `poetry run poe check:fix`
- [ ] Request checkpoint commit if tests pass

### Task 4: [Next Feature/Change]
- ...

## Status
- **Current Phase**: [Phase name]
- **Current Task**: [Task name]
- **Last Updated**: [Timestamp]

## Notes
- Any relevant notes or observations
```

