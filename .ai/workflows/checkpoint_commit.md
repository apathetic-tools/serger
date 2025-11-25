# Checkpoint Commit: Writing Prompts for New Chats

When you've made significant progress fixing errors but `poetry run poe check:fix` still has remaining issues, you can make a checkpoint commit and write a prompt for opening a new chat to continue with the remaining fixes.

## When to Use This

- You've fixed most errors but some remain
- The remaining errors are complex or time-consuming
- You want to save progress before continuing
- The work would benefit from a fresh context in a new chat

## Workflow

1. **Make the checkpoint commit**
   - Follow git conventions in `git_conventions.mdc`
   - Use format: `checkpoint(scope): brief description`
   - Commit the current state even if `poetry run poe check:fix` doesn't fully pass

2. **Write a prompt for the new chat**
   - The prompt should be comprehensive enough for a new AI assistant to understand the context
   - Include all the information listed below
   - Format it clearly for easy copy-paste

## Required Prompt Components

The prompt for the new chat must include:

### 1. Context
- Brief description of what was being worked on
- The feature, bug fix, or change being implemented
- Any relevant background information

### 2. Current Status
- What has been fixed successfully
- What progress has been made
- What is currently working

### 3. Remaining Issues
- List of specific errors or test failures that still need to be addressed
- Error messages (if available)
- Files that still need work
- Any known blockers or complications

### 4. Next Steps
- What needs to be done to get `poetry run poe check:fix` passing
- Priority order if there are multiple issues
- Any specific approaches to try

### 5. Files Changed
- List of files that were modified in this checkpoint
- This helps the new assistant understand the scope of changes

## Example Prompt Template

```
I'm working on [feature/change description]. I've made a checkpoint commit after fixing most issues, but `poetry run poe check:fix` still has [X] remaining errors.

**Fixed:**
- [List of what was fixed]
- [Specific errors resolved]
- [Tests that now pass]

**Remaining issues:**
- [Specific error messages or test failures]
- [Files that still need work]
- [Type checking errors, linting issues, test failures, etc.]

**Next steps:**
- [What needs to be done to resolve remaining issues]
- [Priority order if multiple issues]
- [Any specific approaches to try]

**Files modified:**
- [List of changed files with brief description of changes]

Please help me resolve the remaining issues to get `poetry run poe check:fix` passing.
```

## Tips for Writing Effective Prompts

- **Be specific**: Include actual error messages, not just descriptions
- **Provide context**: Explain why changes were made, not just what was changed
- **Include file paths**: Make it easy to find the relevant code
- **Set priorities**: If there are multiple issues, indicate which to tackle first
- **Mention what works**: Help the new assistant understand what's already correct
- **Include relevant code snippets**: If a specific pattern or approach is needed, show examples

## After Writing the Prompt

- Copy the prompt to share with the user
- The user can then open a new chat and paste the prompt to continue work
- The new assistant will have full context to continue fixing the remaining issues

