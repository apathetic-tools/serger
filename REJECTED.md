<!-- REJECTED.md -->
# Rejected / Deferred Ideas

A record of design experiments and ideas that were explored but intentionally not pursued.


## 📦 Package Detection Caching Optimization
<a id="rej03"></a>*REJ 03 — 2025-01-28*

### Context
Considered implementing caching for package detection to avoid redundant filesystem checks when processing multiple files in the same directory hierarchy. The idea was to cache directory-level results (e.g., whether `src/serger/` has `__init__.py`) so that when processing `src/serger/utils.py` and later `src/serger/config.py`, we could reuse cached results for common parent directories.

### Reason for Rejection
- Negligible performance benefit: even with 100 files in the same package hierarchy, only saves ~197 redundant `__init__.py` stat calls, which translates to approximately 0.2ms saved (filesystem stat calls are very fast at ~0.001ms each)
- Package detection is already fast and not a bottleneck; build time is dominated by post-processing tools (ruff/black: ~1.5–1.8 seconds)
- Implementation complexity exceeds benefit: would require cache state management, handling edge cases (symlinks, different filesystem types, source_bases context), and maintaining cache invalidation logic
- Current implementation is simple, correct, and maintainable; adding caching would introduce indirection and state management complexity
- Doesn't align with serger's target audience of small-to-medium, focused projects where package detection overhead is minimal

### Revisit If
- Profiling shows package detection is a significant bottleneck (>10% of build time)
- Users report slow builds specifically related to package detection
- Projects with 500+ files become common use cases
- **First step if needed**: Implement simple memoization using `@functools.lru_cache` on `__init__.py` existence checks rather than full caching infrastructure


## 🔧 Full AST Transformation and Symbol Renaming
<a id="rej02"></a>*REJ 02 — 2025-01-27*

### Context
Considered implementing full AST parsing and rewriting capabilities to rename symbol references everywhere. This would allow renaming not just function definitions, but all calls to those functions throughout the codebase.

### Reason for Rejection
- Would require becoming a full AST transformer/compiler, which is beyond serger's scope as a module stitcher
- Significant complexity: would need to track all symbol references, handle edge cases (dynamic references, string-based lookups, etc.), and ensure correctness across the entire codebase
- Opens up a "can of worms" — once you start transforming code, there are many edge cases and complexities that need to be handled
- Limited use case: renaming definitions (e.g., function definitions) is sufficient for most stitching needs without requiring full symbol reference rewriting
- Serger's goal is to be a simple, focused tool for stitching modules together, not a comprehensive code transformation tool

### Revisit If
- A clear, well-defined use case emerges that requires full symbol renaming
- A simpler approach is found that handles the common cases without full AST transformation complexity
- The project scope explicitly expands to include code transformation capabilities


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





