<!-- REJECTED.md -->
# Rejected / Deferred Ideas

A record of design experiments and ideas that were explored but intentionally not pursued.


## 📦 Making `package` Optional with Auto-Detection
<a id="rej02"></a>*REJ 02 — 2025-11-15*

### Context
Explored making the `package` configuration field optional or removed, relying on auto-detection from:
- File structure analysis (detecting `__init__.py` files to identify packages)
- Module name extraction (parsing package names from included file paths)
- Entry point detection (finding packages containing `main()` functions for output filename/display name)

The codebase already has sophisticated package detection logic that supplements the configured `package` name, suggesting it could potentially replace it entirely.

### Reason for Rejection
While technically feasible, making `package` optional creates confusing edge cases that hurt user experience:

1. **Multiple packages without main()**: When stitching multiple packages, auto-detection can't determine which package name to use for output filename or display name fallback.

2. **Mixed files (package + loose files)**: When including both package directories and loose files, loose files need a package namespace but there's no clear source for it.

3. **No packages at all**: When stitching only loose files (no `__init__.py` files), everything needs a package name but there's nothing to auto-detect from.

These scenarios create a "works until it doesn't" experience where users successfully use serger with simple configs, then encounter confusing failures when they add more files or packages. Making `package` required ensures:
- **Explicit intent**: Users clearly declare what package they're building
- **Consistent behavior**: Works the same way in all scenarios (single package, multi-package, loose files)
- **No surprise failures**: Edge cases are handled explicitly from the start
- **Better UX**: Clear, predictable configuration over "magic" auto-detection

The auto-detection logic remains valuable internally for multi-package support, but requiring `package` in user configuration provides better developer experience.

### Follow-up and Evolution (*2025-11-15*)
- File structure analysis (detecting `__init__.py` files to identify packages) - **This is now the only detection method used** with `package` used as the fallback


## 🧵 Incremental Stitching with Dependency Caching
<a id="rej01"></a>*REJ 01 — 2025-11-11*  

### Context
Considered implementing incremental stitching with dependency caching to speed up rebuilds in watch mode. The idea was to cache AST parse results and dependency graphs per file, only re-parsing files that changed between builds.

### Reason for Rejection
- Significant implementation complexity (mtime tracking, content hashing, cache invalidation, storage management)
- Negligible performance benefit: even for a project like serger itself (7,300+ lines across 17 modules), only provides sub-second improvement (~0.07s saved) per rebuild
- Build time is dominated by post-processing tools (ruff/black) which take ~1.5–1.8 seconds and cannot be cached
- Larger projects (50+ files, 20k+ lines) that would benefit more are unlikely to use serger due to global namespace conflicts when stitching multiple large modules into a single file
- Doesn't align with serger's target audience of small-to-medium, focused projects

### Revisit If
- Users report significant build time issues on larger projects
- Watch mode becomes a primary workflow and users complain about slow rebuild times
- A simpler caching approach emerges that provides meaningful benefit without significant complexity


