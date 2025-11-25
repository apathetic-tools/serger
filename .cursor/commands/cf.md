# Fix all lint and test errors.

Alias of `checkfix` command.

1. Run `poetry run poe check:fix` to check and auto-fix (each iteration must use this command, subcommands are OK for troubleshooting)
2. If errors remain, fix manually
3. Iterate until exit code 0
4. Fix ALL errors, even if unrelated to current changes. CI fails on any remaining errors
5. If stuck/unsure, stop and ask user, don't guess

