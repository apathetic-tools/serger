<!-- REJECTED.md -->
# Rejected / Deferred Ideas

A record of design experiments and ideas that were explored but intentionally not pursued.


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

