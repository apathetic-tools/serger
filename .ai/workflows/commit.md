# Writing Commit Messages

When committing changes, follow these conventions for writing clear, conventional commit messages.

## Commit Message Format

Use the format: `type(scope): subject`

### Components

- **type**: The type of change (feat, fix, docs, style, refactor, test, chore)
- **scope**: The feature or module being worked on (optional but recommended)
- **subject**: A concise description of what was done

### Subject Line Requirements

- **Important**: The subject line must summarize the overall work across all staged files, not just the last change
- If the subject line cannot summarize all changes in a short sentence, prioritize the most impactful change to the project
- All changes should still be detailed in the commit message body
- Include the feature being worked on in the scope, and if appropriate, a concise description of what was done

### Commit Message Body

After the first line, include a traditional bulleted list summarizing the key changes made in the commit.

- **Important**: The body must cover all significant changes across all staged files, not just the most recent change
- If many files were changed, group related changes together in the bulleted list
- Each bullet should be concise but descriptive
- Focus on what changed and why, not how (implementation details)

## Examples

### Single-line (for simple changes)

```
feat(build): add support for custom output paths
```

### Multi-line with bulleted list (for complex changes)

```
docs(ai-rules): update code quality rules with comprehensive guidelines

- Add detailed line length guidance with readability emphasis
- Add examples for comments, strings, and inline statements
- Add comprehensive Python version compatibility guidelines
- Add detailed static checks, type checking, formatting, linting, and tests section
- Add checkpoint commit guidance with prompt template
- Reference git_conventions.mdc for commit messages
```

### Other Examples

- `fix(config): resolve validation error for empty build configs`
- `refactor(utils): simplify path normalization logic`
- `test(integration): add tests for log level handling`

## Type Categories

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, whitespace, etc.)
- **refactor**: Code refactoring without changing functionality
- **test**: Adding or modifying tests
- **chore**: Maintenance tasks, dependency updates, build changes

## Scope Guidelines

- Use the module, feature, or area of the codebase being changed
- Keep scope concise (1-2 words when possible)
- Use lowercase with hyphens if needed (e.g., `ai-guidance`, `build-script`)
- Omit scope for very general changes that affect the entire project

## Best Practices

- **Be specific**: Avoid vague subjects like "fix bug" or "update code"
- **Use imperative mood**: Write as if completing "This commit will..." (e.g., "add feature" not "added feature")
- **Keep subject under 72 characters**: Traditional git convention for readability
- **Start with lowercase**: Unless the subject starts with a proper noun or acronym
- **No period at end**: Subject line should not end with a period
- **Group related changes**: If multiple files changed for the same reason, group them in the body

## When to Use Multi-line vs Single-line

- **Single-line**: Use for simple, focused changes that can be fully described in the subject
- **Multi-line**: Use when:
  - Multiple files were changed
  - Changes span multiple areas
  - The change requires explanation beyond the subject line
  - You want to document the rationale or approach

## Checking for Checkpoint Commits

Before making a regular commit, check for checkpoint commits since the last regular commit:

1. Find the last commit that is NOT a checkpoint (subject line doesn't start with "checkpoint("):
   ```bash
   LAST_REGULAR=$(git log --format="%H|%s" | awk -F'|' '$2 !~ /^checkpoint\(/ {print $1; exit}')
   ```

2. Check for checkpoint commits between that and HEAD (subject line starts with "checkpoint("):
   ```bash
   git log --format="%H|%s" ${LAST_REGULAR}..HEAD | awk -F'|' '$2 ~ /^checkpoint\(/ {print $1, $2}'
   ```

3. Count the checkpoint commits and if any are found, ask the user: "I see [N] checkpoint commit(s). Squash with this commit?" and wait for response.

**Important**: 
- Checkpoint commits have the format `checkpoint(scope): brief description` in the subject line
- The check must examine the subject line only (not the commit message body), as commits may mention "checkpoint" in the body without being checkpoint commits
- Do NOT use `git log --grep="checkpoint"` alone, as it searches the entire message (including body) and will incorrectly match commits that mention "checkpoint" in the body but are not checkpoint commits
- The awk approach uses a pipe delimiter to separate hash from subject, then matches the subject line pattern `^checkpoint\(` to identify checkpoint commits

