# src/serger/stitch.py
"""Stitching logic for combining multiple Python modules into a single file.

This module handles the core functionality for stitching together modular
Python source files into a single executable script. It includes utilities for
import handling, code analysis, and assembly.
"""

import ast
import importlib
import json
import os
import re
import subprocess
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from apathetic_utils import (
    detect_packages_from_files,
    is_ci,
    literal_to_set,
    load_toml,
)

from .config import (
    CommentsMode,
    DocstringMode,
    DocstringModeLocation,
    DocstringModeSimple,
    ExternalImportMode,
    IncludeResolved,
    InternalImportMode,
    ModuleActionFull,
    ModuleMode,
    PostProcessingConfigResolved,
    RootConfigResolved,
    ShimSetting,
    StitchMode,
)
from .constants import (
    BUILD_TOOL_FIND_MAX_LINES,
    DEFAULT_COMMENTS_MODE,
    DEFAULT_DOCSTRING_MODE,
    DEFAULT_EXTERNAL_IMPORTS,
    DEFAULT_INTERNAL_IMPORTS,
    DEFAULT_MODULE_MODE,
    DEFAULT_SHIM,
    DEFAULT_STITCH_MODE,
)
from .logs import getAppLogger
from .main_config import (
    MainBlock,
    detect_collisions,
    detect_function_parameters,
    detect_main_blocks,
    find_main_function,
    generate_auto_renames,
    rename_function_in_source,
    select_main_block,
)
from .meta import PROGRAM_PACKAGE
from .module_actions import (
    apply_cleanup_behavior,
    apply_module_actions,
    apply_single_action,
    check_shim_stitching_mismatches,
    generate_actions_from_mode,
    separate_actions_by_affects,
    set_mode_generated_action_defaults,
    validate_action_source_exists,
    validate_module_actions,
)
from .utils import derive_module_name, shorten_path_for_display
from .utils.utils_validation import validate_required_keys
from .verify_script import (
    _cleanup_error_files,  # pyright: ignore[reportPrivateUsage]
    _write_error_file,  # pyright: ignore[reportPrivateUsage]
    post_stitch_processing,
    verify_compiles_string,
)


def extract_version(pyproject_path: Path) -> str:
    """Extract version string from pyproject.toml.

    Checks both top-level and [project] section for version field.

    Args:
        pyproject_path: Path to pyproject.toml file

    Returns:
        Version string, or "unknown" if not found
    """
    if not pyproject_path.exists():
        return "unknown"
    data = load_toml(pyproject_path, required=False)
    if data:
        # Check [project] section first (standard location)
        project = data.get("project", {})
        version = project.get("version", "")
        if isinstance(version, str) and version:
            return version
        # Fallback to top-level version (for simplified test cases)
        version = data.get("version", "")
        if isinstance(version, str) and version:
            return version
    return "unknown"


def extract_commit(root_path: Path) -> str:  # noqa: PLR0915
    """Extract git commit hash.

    Only embeds commit hash if in CI or release tag context.

    Args:
        root_path: Project root directory

    Returns:
        Short commit hash, or "unknown (local build)" if not in CI
    """
    logger = getAppLogger()
    # Comprehensive logging for troubleshooting
    in_ci = is_ci()
    ci_env = os.getenv("CI")
    github_actions = os.getenv("GITHUB_ACTIONS")
    git_tag = os.getenv("GIT_TAG")
    github_ref = os.getenv("GITHUB_REF")
    logger.trace(
        "extract_commit called: root_path=%s, in_ci=%s, CI=%s, GITHUB_ACTIONS=%s, "
        "GIT_TAG=%s, GITHUB_REF=%s",
        root_path,
        in_ci,
        ci_env,
        github_actions,
        git_tag,
        github_ref,
    )
    logger.trace(
        "extract_commit: root_path=%s, in_ci=%s, CI=%s, GITHUB_ACTIONS=%s, "
        "GIT_TAG=%s, GITHUB_REF=%s",
        root_path,
        in_ci,
        ci_env,
        github_actions,
        git_tag,
        github_ref,
    )

    # Only embed commit hash if in CI or release tag context
    if not in_ci:
        result = "unknown (local build)"
        logger.trace("extract_commit: Not in CI context, returning: %s", result)
        return result

    # Resolve path and verify it exists
    resolved_path = root_path.resolve()
    logger.info("extract_commit: resolved_path=%s", resolved_path)
    logger.trace("extract_commit: resolved_path=%s", resolved_path)

    if not resolved_path.exists():
        logger.warning("Git root path does not exist: %s", resolved_path)
        logger.trace("extract_commit: Path does not exist: %s", resolved_path)
        return "unknown"

    # Check if .git exists (directory or file for worktrees)
    git_dir = resolved_path / ".git"
    parent_git = resolved_path.parent / ".git"
    git_dir_exists = git_dir.exists()
    parent_git_exists = parent_git.exists()
    logger.info(
        "extract_commit: git_dir=%s (exists=%s), parent_git=%s (exists=%s)",
        git_dir,
        git_dir_exists,
        parent_git,
        parent_git_exists,
    )
    logger.trace(
        "extract_commit: git_dir=%s (exists=%s), parent_git=%s (exists=%s)",
        git_dir,
        git_dir_exists,
        parent_git,
        parent_git_exists,
    )

    if not (git_dir_exists or parent_git_exists):
        logger.warning("No .git directory found at %s", resolved_path)
        logger.trace("extract_commit: No .git found, returning 'unknown'")
        return "unknown"

    commit_hash = "unknown"
    try:
        # Convert Path to string for subprocess compatibility
        cwd_str = str(resolved_path)
        logger.info("extract_commit: Running git rev-parse in: %s", cwd_str)
        logger.trace("extract_commit: Running git rev-parse in: %s", cwd_str)

        git_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=cwd_str,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_hash = git_result.stdout.strip()
        logger.info(
            "extract_commit: git rev-parse stdout=%r, stderr=%r",
            git_result.stdout,
            git_result.stderr,
        )
        logger.trace(
            "extract_commit: git rev-parse stdout=%r, stderr=%r",
            git_result.stdout,
            git_result.stderr,
        )

        if not commit_hash:
            logger.warning("git rev-parse returned empty string")
            logger.trace("extract_commit: Empty commit hash, using 'unknown'")
            commit_hash = "unknown"
        else:
            logger.info("extract_commit: Successfully extracted: %s", commit_hash)
            logger.trace("extract_commit: Successfully extracted: %s", commit_hash)

    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.strip() or "no error message"
        logger.warning(
            "git rev-parse failed at %s: %s (stderr: %s, returncode: %s)",
            resolved_path,
            stderr_msg,
            stderr_msg,
            e.returncode,
        )
        logger.trace(
            "extract_commit: git rev-parse failed: returncode=%s, stderr=%s",
            e.returncode,
            stderr_msg,
        )
    except FileNotFoundError:
        logger.warning("git not available in environment")
        logger.trace("extract_commit: git not found in PATH")

    # In CI, always log the final commit value for debugging
    if in_ci:
        logger.info(
            "Final commit hash for embedding: %s (from %s)",
            commit_hash,
            resolved_path,
        )
        logger.trace(
            "extract_commit: FINAL RESULT: %s (from %s)",
            commit_hash,
            resolved_path,
        )

    return commit_hash


# Maximum number of lines to read when checking if a file is a serger build
def is_serger_build(file_path: Path, max_lines: int | None = None) -> bool:
    """Check if a file is a serger-generated build.

    Checks for the "# Build Tool: serger" comment line that appears early
    in the metadata section of serger-generated files (typically around
    line 11, after the docstring and before imports).

    Args:
        file_path: Path to the file to check
        max_lines: Maximum number of lines to read. If None, uses
            BUILD_TOOL_FIND_MAX_LINES constant.

    Returns:
        True if the file appears to be a serger build, False otherwise
    """
    if not file_path.exists():
        return False

    # Use provided max_lines or fall back to constant
    line_limit = max_lines if max_lines is not None else BUILD_TOOL_FIND_MAX_LINES

    try:
        # Read first N lines to catch the metadata section
        # where "# Build Tool: serger" appears (typically around line 11)
        with file_path.open(encoding="utf-8") as f:
            lines: list[str] = []
            for i, line in enumerate(f):
                if i >= line_limit:
                    break
                lines.append(line)

        content = "".join(lines)

        # Check for "# Build Tool: serger" comment line
        # Pattern matches the line with optional whitespace and case-insensitive
        pattern = r"#\s*Build\s+Tool:\s*serger"
        return bool(re.search(pattern, content, re.IGNORECASE))

    except (OSError, UnicodeDecodeError):
        # If we can't read the file, assume it's not a serger build
        # (safer to err on the side of caution)
        return False


def split_imports(  # noqa: C901, PLR0912, PLR0915
    text: str,
    package_names: list[str],
    external_imports: ExternalImportMode = "top",
    internal_imports: InternalImportMode = "force_strip",
) -> tuple[list[str], str]:
    """Extract external imports and body text using AST.

    Separates internal package imports from external imports, handling them
    according to the external_imports and internal_imports modes. Recursively
    finds imports at all levels, including inside functions.

    Args:
        text: Python source code
        package_names: List of package names to treat as internal
            (e.g., ["serger", "other"])
        external_imports: How to handle external imports. Supported modes:
            - "top": Hoist module-level external imports to top, but only if
              not inside conditional structures (try/if blocks) (default).
              `if TYPE_CHECKING:` blocks are excluded from this check.
            - "force_top": Hoist module-level external imports to top of file.
              Always moves imports, even inside conditional structures (if, try,
              etc.). Module-level imports are collected and deduplicated at the
              top. Empty structures (if, try, etc.) get a `pass` statement.
              Empty `if TYPE_CHECKING:` blocks (including those with only pass
              statements) are removed entirely.
            - "keep": Leave external imports in their original locations
            - "force_strip": Remove all external imports regardless of location
              (module-level, function-local, in conditionals, etc.). Empty
              structures (if, try, etc.) get a `pass` statement. Empty
              `if TYPE_CHECKING:` blocks (including those with only pass
              statements) are removed entirely.
            - "strip": Remove external imports, but skip imports inside
              conditional structures (if, try, etc.). `if TYPE_CHECKING:` blocks
              are always processed (imports removed). Empty `if TYPE_CHECKING:`
              blocks (including those with only pass statements) are removed
              entirely.
        internal_imports: How to handle internal imports. Supported modes:
            - "force_strip": Remove all internal imports regardless of location
              (default). Internal imports break in stitched mode, so they are
              removed by default.
            - "keep": Keep internal imports in their original locations within
              each module section.
            - "strip": Remove internal imports, but skip imports inside
              conditional structures (if, try, etc.). `if TYPE_CHECKING:` blocks
              are always processed (imports removed). Empty `if TYPE_CHECKING:`
              blocks (including those with only pass statements) are removed
              entirely.
            - "assign": **[EXPERIMENTAL/WIP]** Transform imports into assignments.
              Converts imports like `from module import name` to `name = name`
              (direct reference). In stitched mode, all modules share the same
              global namespace and execute in topological order, so symbols can be
              referenced directly. Preserves original indentation and location of
              imports. Assignments are included in collision detection. Note: `import
              module` statements for internal packages may not work correctly as
              there are no module objects in stitched mode.

    Returns:
        Tuple of (external_imports, body_text) where external_imports is a
        list of import statement strings (empty for "keep" mode), and body_text
        is the source with imports removed according to the mode
    """
    logger = getAppLogger()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        logger.exception("Failed to parse file")
        return [], text

    lines = text.splitlines(keepends=True)
    external_imports_list: list[str] = []
    # Separate list for TYPE_CHECKING imports
    type_checking_imports_list: list[str] = []
    all_import_ranges: list[tuple[int, int]] = []
    # For assign mode: track imports to replace with assignments
    # Maps (start, end) range to assignment code
    import_replacements: dict[tuple[int, int], str] = {}

    def find_parent(
        node: ast.AST,
        tree: ast.AST,
        target_type: type[ast.AST] | tuple[type[ast.AST], ...],
    ) -> ast.AST | None:
        """Find if a node is inside a specific parent type by tracking parent nodes."""
        # Build a mapping of child -> parent
        parent_map: dict[ast.AST, ast.AST] = {}

        def build_parent_map(parent: ast.AST) -> None:
            """Recursively build parent mapping."""
            for child in ast.iter_child_nodes(parent):
                parent_map[child] = parent
                build_parent_map(child)

        build_parent_map(tree)

        # Walk up the parent chain to find target type
        current: ast.AST | None = node
        while current is not None:
            if isinstance(current, target_type):
                # Type checker can't infer the specific type from isinstance check
                # We know it's the target_type due to the isinstance check
                return current  # mypy: ignore[return-value]
            current = parent_map.get(current)
        return None

    def has_no_move_comment(snippet: str) -> bool:
        """Check if import has a # serger: no-move comment."""
        # Look for # serger: no-move or # serger:no-move (with or without space)
        pattern = r"#\s*serger\s*:\s*no-move"
        return bool(re.search(pattern, snippet, re.IGNORECASE))

    def is_in_conditional(node: ast.AST, tree: ast.AST) -> bool:
        """Check if node is inside a conditional structure (try/if).

        Returns True if node is inside a try block or if block (excluding
        `if TYPE_CHECKING:` blocks). Returns False otherwise.

        Args:
            node: AST node to check
            tree: Root AST tree (for building parent map)

        Returns:
            True if node is in a conditional structure, False otherwise
        """
        # Build parent map once
        parent_map: dict[ast.AST, ast.AST] = {}

        def build_parent_map(parent: ast.AST) -> None:
            """Recursively build parent mapping."""
            for child in ast.iter_child_nodes(parent):
                parent_map[child] = parent
                build_parent_map(child)

        build_parent_map(tree)

        # Walk up the parent chain
        current: ast.AST | None = node
        while current is not None:
            # Check for try blocks
            if isinstance(current, ast.Try):
                return True

            # Check for if blocks (but exclude `if TYPE_CHECKING:`)
            if isinstance(current, ast.If):
                # Check if this is `if TYPE_CHECKING:`
                # It must be: test is a Name with id == "TYPE_CHECKING"
                if (
                    isinstance(current.test, ast.Name)
                    and current.test.id == "TYPE_CHECKING"
                ):
                    # This is `if TYPE_CHECKING:` - don't count as conditional
                    # Continue checking parent chain
                    pass
                else:
                    # This is a regular if block - count as conditional
                    return True

            current = parent_map.get(current)

        return False

    def generate_assignments_from_import(
        node: ast.Import | ast.ImportFrom,
        _package_names: list[str],
    ) -> str:
        """Generate assignment statements from an import node.

        In the stitched output, all modules share the same global namespace and
        are executed in topological order. So we can reference symbols directly
        instead of using sys.modules (which isn't set up until after all module
        code runs).

        Converts imports like:
        - `from module import name` → (skipped, no-op: `name = name`)
        - `from module import name as alias` → `alias = name` (direct reference)
        - `import module` → (skipped, no-op: `module = module`)
        - `import module as alias` → `alias = module` (direct reference)

        Note: No-op assignments (where local_name == imported_name) are skipped
        since they're redundant.

        Note: For `import a.b.c`, Python creates variable 'a' in the namespace,
        but in stitched mode, we can't easily reference 'a.b.c' directly.
        This case may need special handling or may not be fully supported.

        Args:
            node: AST Import or ImportFrom node
            package_names: List of package names (unused, kept for API consistency)

        Returns:
            String containing assignment statements, one per line
        """
        assignments: list[str] = []

        if isinstance(node, ast.ImportFrom):
            # Handle: from module import name1, name2, ...
            # In stitched mode, all symbols are in the same global namespace,
            # so we can reference them directly
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname if alias.asname else imported_name
                # Skip no-op assignments (name = name)
                if local_name != imported_name:
                    # Direct reference: symbol is already in global namespace
                    assignment = f"{local_name} = {imported_name}"
                    assignments.append(assignment)

        else:
            # Handle: import module [as alias]
            for alias in node.names:
                module_name = alias.name
                if alias.asname:
                    # import module as alias
                    local_name = alias.asname
                    # For simple imports like "import json", we can reference
                    # directly. But this assumes the module was already imported
                    # as an external import (hoisted to top).
                    # For internal imports, this won't work - we'd need the
                    # module object, which doesn't exist in stitched mode.
                    # This is a limitation of assign mode for "import module".
                    # Skip no-op (alias == module_name)
                    if local_name != module_name:
                        assignment = f"{local_name} = {module_name}"
                        assignments.append(assignment)
                else:
                    # import module or import a.b.c
                    # For dotted imports like "import a.b.c", Python creates
                    # variable 'a' pointing to the 'a' module.
                    # In stitched mode, we can't reference 'a.b.c' directly,
                    # so we just reference the first component.
                    # This may not work correctly for all cases.
                    # Skip no-op assignments (module = module would be redundant)
                    # Note: For non-aliased imports, we skip since it would be
                    # a no-op (first_component = first_component)
                    pass

        return "\n".join(assignments)

    def collect_imports(node: ast.AST) -> None:  # noqa: C901, PLR0912, PLR0915
        """Recursively collect all import nodes from the AST."""
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start = node.lineno - 1
            end = getattr(node, "end_lineno", node.lineno)
            snippet = "".join(lines[start:end])

            # Check for # serger: no-move comment
            if has_no_move_comment(snippet):
                # Keep import in place - don't add to external_imports or ranges
                return

            # --- Determine whether it's internal ---
            is_internal = False
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if node.level > 0:
                    is_internal = True
                else:
                    # Check if module is exactly a package name or starts with one
                    for pkg in package_names:
                        if mod == pkg or mod.startswith(f"{pkg}."):
                            is_internal = True
                            break
            else:
                # Check if any alias starts with any of the package names
                for pkg in package_names:
                    if any(
                        alias.name == pkg or alias.name.startswith(f"{pkg}.")
                        for alias in node.names
                    ):
                        is_internal = True
                        break

            # Check if import is inside if TYPE_CHECKING block
            # Must be exactly 'if TYPE_CHECKING:' (not 'if TYPE_CHECKING and
            # something:')
            type_checking_block = find_parent(node, tree, ast.If)
            is_type_checking = (
                type_checking_block
                and isinstance(type_checking_block, ast.If)
                and isinstance(type_checking_block.test, ast.Name)
                and type_checking_block.test.id == "TYPE_CHECKING"
            )

            # Handle internal imports according to mode
            if is_internal:
                if internal_imports == "keep":
                    # Keep internal imports in place - don't add to ranges
                    pass
                elif internal_imports == "force_strip":
                    # Remove all internal imports regardless of location
                    all_import_ranges.append((start, end))
                elif internal_imports == "strip":
                    # Strip internal imports, but skip imports inside conditional
                    # structures (if, try, etc.). TYPE_CHECKING blocks are always
                    # processed (imports removed).
                    if is_type_checking:
                        # Always process TYPE_CHECKING blocks - remove imports
                        all_import_ranges.append((start, end))
                    elif is_in_conditional(node, tree):
                        # In conditional (but not TYPE_CHECKING) - keep import
                        # Don't add to ranges
                        pass
                    else:
                        # Not in conditional - remove import
                        all_import_ranges.append((start, end))
                elif internal_imports == "assign":
                    # Transform imports into assignments
                    # Get indentation from the original import line
                    import_line = lines[start] if start < len(lines) else ""
                    indent_match = re.match(r"^(\s*)", import_line)
                    indent = indent_match.group(1) if indent_match else ""
                    # Generate assignment code
                    assignment_code = generate_assignments_from_import(
                        node, package_names
                    )
                    # Indent each assignment line to match original import
                    indented_assignments = "\n".join(
                        f"{indent}{line}" for line in assignment_code.split("\n")
                    )
                    # Add newline at end if original had one
                    if end < len(lines) and lines[end - 1].endswith("\n"):
                        indented_assignments += "\n"
                    # Store replacement
                    import_replacements[(start, end)] = indented_assignments
                    # Mark import for removal
                    all_import_ranges.append((start, end))
                else:
                    # Unknown mode
                    msg = (
                        f"internal_imports mode '{internal_imports}' is not "
                        "supported. Only 'force_strip', 'keep', 'strip', and "
                        "'assign' modes are currently supported."
                    )
                    raise ValueError(msg)
            # External: handle according to mode
            elif external_imports == "keep":
                # Keep external imports in place - don't add to ranges or list
                pass
            elif external_imports == "force_top":
                # Hoist module-level to top, keep function-local in place
                is_module_level = not find_parent(
                    node, tree, (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                if is_module_level:
                    # Module-level external import - hoist to top section
                    all_import_ranges.append((start, end))
                    import_text = snippet.strip()
                    if import_text:
                        if not import_text.endswith("\n"):
                            import_text += "\n"
                        # Track TYPE_CHECKING imports separately
                        if is_type_checking:
                            type_checking_imports_list.append(import_text)
                        else:
                            external_imports_list.append(import_text)
                # Function-local external imports stay in place (not added to ranges)
            elif external_imports == "top":
                # Hoist module-level to top, but only if not in conditional
                # Keep function-local and conditional imports in place
                is_module_level = not find_parent(
                    node, tree, (ast.FunctionDef, ast.AsyncFunctionDef)
                )
                if is_module_level and not is_in_conditional(node, tree):
                    # Module-level external import not in conditional - hoist to top
                    all_import_ranges.append((start, end))
                    import_text = snippet.strip()
                    if import_text:
                        if not import_text.endswith("\n"):
                            import_text += "\n"
                        # Track TYPE_CHECKING imports separately
                        if is_type_checking:
                            type_checking_imports_list.append(import_text)
                        else:
                            external_imports_list.append(import_text)
                # Function-local and conditional external imports stay in place
            elif external_imports == "force_strip":
                # Strip all external imports regardless of location
                # (module-level, function-local, in conditionals, etc.)
                all_import_ranges.append((start, end))
                # Don't add to external_imports_list (we're stripping, not hoisting)
            elif external_imports == "strip":
                # Strip external imports, but skip imports inside conditional
                # structures (if, try, etc.). TYPE_CHECKING blocks are always
                # processed (imports removed).
                if is_type_checking:
                    # Always process TYPE_CHECKING blocks - remove imports
                    all_import_ranges.append((start, end))
                elif is_in_conditional(node, tree):
                    # In conditional (but not TYPE_CHECKING) - keep import
                    # Don't add to ranges
                    pass
                else:
                    # Not in conditional - remove import
                    all_import_ranges.append((start, end))
                # Don't add to external_imports_list (we're stripping, not hoisting)
            else:
                # Other modes (assign)
                # not yet implemented
                msg = (
                    f"external_imports mode '{external_imports}' is not yet "
                    "implemented. Only 'force_top', 'top', 'keep', "
                    "'force_strip', and 'strip' modes are currently supported."
                )
                raise ValueError(msg)

        # Recursively visit child nodes
        for child in ast.iter_child_nodes(node):
            collect_imports(child)

    # Collect all imports recursively
    for node in tree.body:
        collect_imports(node)

    # --- Remove *all* import lines from the body and insert assignments ---
    # Build new body with imports replaced by assignments
    new_lines: list[str] = []
    i = 0
    while i < len(lines):
        # Check if this line is part of an import to remove
        in_import_range = False
        replacement_range: tuple[int, int] | None = None
        for start, end in all_import_ranges:
            if start <= i < end:
                in_import_range = True
                replacement_range = (start, end)
                break

        if in_import_range and replacement_range:
            # This is an import to replace
            if replacement_range in import_replacements:
                # Insert assignment code
                assignment_code = import_replacements[replacement_range]
                new_lines.append(assignment_code)
            # Skip all lines in this import range
            i = replacement_range[1]
        else:
            # Keep this line
            new_lines.append(lines[i])
            i += 1

    body = "".join(new_lines)

    # Check if TYPE_CHECKING blocks and other conditional blocks are empty
    # TYPE_CHECKING blocks: remove if empty
    # Other conditionals: add 'pass' if empty (they might have side effects)
    body_lines = body.splitlines(keepends=True)
    lines_to_remove: set[int] = set()
    lines_to_insert: list[tuple[int, str]] = []  # (index, line_to_insert)

    # Find empty conditional blocks
    i = 0
    while i < len(body_lines):
        line = body_lines[i].rstrip()
        # Check if this is a conditional block start (if/try)
        # Match "if condition:" or "try:" (try can have no condition)
        if re.match(r"^\s*(if\s+.*|try)\s*:\s*$", line):
            block_start = i
            is_type_checking = bool(re.match(r"^\s*if\s+TYPE_CHECKING\s*:\s*$", line))
            # Get indentation level
            indent_match = re.match(r"^(\s*)", body_lines[i])
            indent = indent_match.group(1) if indent_match else ""
            i += 1
            # Check if block is empty (only whitespace, pass, or nothing)
            # For TYPE_CHECKING blocks, treat blocks with only pass statements as empty
            has_content = False
            block_end = i
            is_try = line.strip().startswith("try:")
            only_pass_statements = True  # Track if block only has pass statements
            while i < len(body_lines):
                next_line = body_lines[i]
                stripped = next_line.strip()
                # Empty line - continue checking
                if not stripped:
                    i += 1
                    continue
                # For try blocks, check for except/finally/else clauses
                # These are at the same indentation as try:, so they end the try body
                if is_try and stripped.startswith(("except", "finally", "else:")):
                    # We've reached the end of the try body
                    # Check if the try body (before this clause) was empty
                    block_end = i
                    break
                # Check if line is indented (part of the block)
                if re.match(r"^\s+", next_line):
                    # Indented content found
                    if stripped == "pass":
                        # For TYPE_CHECKING blocks, pass statements don't count
                        # as content. For other blocks, pass is content.
                        if not is_type_checking:
                            has_content = True
                        # else: keep only_pass_statements = True
                    else:
                        # Non-pass content found - block has real content
                        has_content = True
                        only_pass_statements = False
                    i += 1
                    continue
                # Non-indented line - end of block
                block_end = i
                break
            # For TYPE_CHECKING blocks, if only pass statements, treat as empty
            if is_type_checking and only_pass_statements and not has_content:
                # TYPE_CHECKING block with only pass statements: remove
                for j in range(block_start, block_end):
                    lines_to_remove.add(j)
            elif not has_content:
                if is_type_checking:
                    # TYPE_CHECKING block: remove if empty
                    for j in range(block_start, block_end):
                        lines_to_remove.add(j)
                else:
                    # Other conditional: add 'pass' to make it valid
                    # Insert pass after the block start line
                    pass_line = f"{indent}    pass\n"
                    lines_to_insert.append((block_start + 1, pass_line))
        i += 1

    # Apply insertions (in reverse order to maintain indices)
    for idx, line in sorted(lines_to_insert, reverse=True):
        body_lines.insert(idx, line)

    # Remove empty TYPE_CHECKING blocks
    if lines_to_remove:
        body = "".join(
            line for i, line in enumerate(body_lines) if i not in lines_to_remove
        )
    else:
        body = "".join(body_lines)

    # Group TYPE_CHECKING imports together in a single block
    if type_checking_imports_list:
        type_checking_block_text = "if TYPE_CHECKING:\n"
        for imp in type_checking_imports_list:
            # Indent the import
            type_checking_block_text += f"    {imp}"
        external_imports_list.append(type_checking_block_text)

    return external_imports_list, body


def strip_redundant_blocks(text: str) -> str:
    """Remove shebangs and __main__ guards from module code.

    Args:
        text: Python source code

    Returns:
        Source code with shebangs and __main__ blocks removed
    """
    text = re.sub(r"^#!.*\n", "", text)
    text = re.sub(
        r"(?s)\n?if\s+__name__\s*==\s*[\"']__main__[\"']\s*:\s*\n.*?$",
        "",
        text,
    )

    return text.strip()


def process_comments(text: str, mode: CommentsMode) -> str:  # noqa: C901, PLR0912, PLR0915
    """Process comments in source code according to the specified mode.

    Args:
        text: Python source code
        mode: Comments processing mode:
            - "keep": Keep all comments
            - "ignores": Only keep comments that specify ignore rules
            - "inline": Only keep inline comments (on same line as code)
            - "strip": Remove all comments

    Returns:
        Source code with comments processed according to mode
    """
    if mode == "keep":
        return text

    if mode == "strip":
        # Remove all comments, but preserve docstrings
        # Use a simple approach: split by # and check if we're in a string
        lines = text.splitlines(keepends=True)
        result: list[str] = []

        for line in lines:
            # Simple check: if line has #, check if it's in a string
            if "#" not in line:
                result.append(line)
                continue

            # Check if # is inside a string literal
            in_string = False
            string_char = None
            escape_next = False
            comment_pos = -1

            for i, char in enumerate(line):
                if escape_next:
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                    continue

                if not in_string:
                    if char in ('"', "'"):
                        in_string = True
                        string_char = char
                    elif char == "#":
                        comment_pos = i
                        break
                elif char == string_char:
                    in_string = False
                    string_char = None

            if comment_pos >= 0 and not in_string:
                # Found comment outside string - remove it
                code_part = line[:comment_pos].rstrip()
                if code_part:
                    # Has code before comment - keep code part
                    result.append(code_part + ("\n" if line.endswith("\n") else ""))
                # If no code part, this is a standalone comment - remove entirely
            else:
                # No comment found or comment is in string - keep line
                result.append(line)

        return "".join(result)

    # Pattern for ignore comments (case-insensitive)
    # Matches: noqa, type: ignore, pyright: ignore, mypy: ignore,
    # ruff noqa, serger: no-move, etc.
    # Note: This pattern matches the comment part AFTER the #
    ignore_pattern = re.compile(
        r"^\s*(noqa|type:\s*ignore|pyright:\s*ignore|mypy:\s*ignore|ruff:\s*noqa|serger:\s*no-move)",
        re.IGNORECASE,
    )

    lines = text.splitlines(keepends=True)
    output_lines: list[str] = []

    for line in lines:
        # Check if line has code before comment
        if "#" in line:
            # Split at first # to get code and comment parts
            parts = line.split("#", 1)
            code_part = parts[0].rstrip()
            comment_part = parts[1] if len(parts) > 1 else ""
            has_code = bool(code_part)
        else:
            # No comment - keep the line as-is
            output_lines.append(line)
            continue

        if mode == "inline":
            # Keep only inline comments (comments on same line as code)
            if has_code:
                # Has code, so any comment is inline - keep the whole line
                output_lines.append(line)
            # If no code, this is a standalone comment - remove entirely
        elif mode == "ignores":
            # Keep only ignore comments
            if ignore_pattern.match(comment_part):
                # This is an ignore comment - keep it
                output_lines.append(line)
            elif has_code:
                # Has code but comment is not an ignore - keep code, remove comment
                output_lines.append(code_part + ("\n" if line.endswith("\n") else ""))
            # If no code and not an ignore comment, remove entirely
        else:
            # Unknown mode - keep as-is
            output_lines.append(line)

    return "".join(output_lines)


def process_docstrings(text: str, mode: DocstringMode) -> str:  # noqa: C901, PLR0915
    """Process docstrings in source code according to the specified mode.

    Args:
        text: Python source code
        mode: Docstring processing mode:
            - "keep": Keep all docstrings (default)
            - "strip": Remove all docstrings
            - "public": Keep only public docstrings (not prefixed with underscore)
            - dict: Per-location control, e.g., {"module": "keep", "class": "strip"}
              Valid locations: "module", "class", "function", "method"
              Each location value can be "keep", "strip", or "public"
              Omitted locations default to "keep"

    Returns:
        Source code with docstrings processed according to mode
    """
    logger = getAppLogger()

    # Handle simple string modes
    if isinstance(mode, str):
        if mode == "keep":
            return text

        # Normalize to dict format for processing
        mode_dict: dict[DocstringModeLocation, DocstringModeSimple] = {
            "module": mode,
            "class": mode,
            "function": mode,
            "method": mode,
        }
    else:
        # Dict mode - fill in defaults for omitted locations
        mode_dict = {
            "module": mode.get("module", "keep"),
            "class": mode.get("class", "keep"),
            "function": mode.get("function", "keep"),
            "method": mode.get("method", "keep"),
        }

    # Parse AST to find docstrings
    try:
        tree = ast.parse(text)
    except SyntaxError:
        logger.exception("Failed to parse file for docstring processing")
        return text

    # Build parent map to distinguish methods from functions
    parent_map: dict[ast.AST, ast.AST] = {}

    def build_parent_map(parent: ast.AST) -> None:
        """Recursively build parent mapping."""
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
            build_parent_map(child)

    build_parent_map(tree)

    lines = text.splitlines(keepends=True)
    # Track line ranges to remove (start, end) inclusive
    ranges_to_remove: list[tuple[int, int]] = []

    def get_docstring_node(node: ast.AST) -> ast.Expr | None:
        """Get the docstring node if it exists as the first statement."""
        # Type guard: only nodes with body attribute can have docstrings
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            return None
        if not node.body:
            return None
        first_stmt = node.body[0]
        if (
            isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)
        ):
            return first_stmt
        return None

    def is_public(name: str) -> bool:
        """Check if a name is public (doesn't start with underscore)."""
        return not name.startswith("_")

    def get_location_type(node: ast.AST) -> DocstringModeLocation | None:
        """Determine the location type of a docstring node.

        Note: "method" covers all functions inside classes, including:
        - Regular methods
        - Properties (@property)
        - Static methods (@staticmethod)
        - Class methods (@classmethod)
        - Async methods (async def)
        """
        if isinstance(node, ast.Module):
            return "module"
        if isinstance(node, ast.ClassDef):
            return "class"
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if function is inside a class (method) or top-level (function)
            # This covers all method types: regular, @property, @staticmethod, etc.
            parent = parent_map.get(node)
            if isinstance(parent, ast.ClassDef):
                return "method"
            return "function"
        return None

    def should_remove_docstring(
        location: DocstringModeLocation,
        name: str,
    ) -> bool:
        """Determine if a docstring should be removed based on mode."""
        location_mode = mode_dict[location]

        if location_mode == "keep":
            return False
        if location_mode == "strip":
            return True
        if location_mode == "public":
            # Module docstrings are always considered public
            if location == "module":
                return False
            # Remove if not public
            return not is_public(name)
        # Unknown mode - keep it
        return False

    # Process module-level docstring
    module_docstring = get_docstring_node(tree)
    if module_docstring:
        location: DocstringModeLocation = "module"
        if should_remove_docstring(location, "__module__"):
            # Get line range for docstring
            start_line = module_docstring.lineno - 1  # 0-indexed
            end_line = (
                module_docstring.end_lineno - 1
                if module_docstring.end_lineno
                else start_line
            )
            ranges_to_remove.append((start_line, end_line))

    # Process class and function/method docstrings
    def process_node(node: ast.AST) -> None:
        """Recursively process nodes to find docstrings."""
        # Skip module docstring - it's already processed above
        if isinstance(node, ast.Module):
            # Just recurse into children, don't process module docstring again
            for child in node.body:
                process_node(child)
            return

        docstring = get_docstring_node(node)
        if docstring:
            location = get_location_type(node)
            if location:
                name = ""
                if isinstance(
                    node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                ):
                    name = node.name

                if should_remove_docstring(location, name):
                    # Get line range for docstring
                    start_line = docstring.lineno - 1  # 0-indexed
                    end_line = (
                        docstring.end_lineno - 1 if docstring.end_lineno else start_line
                    )
                    ranges_to_remove.append((start_line, end_line))

        # Recurse into child nodes
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in node.body:
                process_node(child)

    process_node(tree)

    # If no ranges to remove, return original text
    if not ranges_to_remove:
        return text

    # Sort ranges by start line (descending) so we can remove from end to start
    # This preserves line numbers while removing
    ranges_to_remove.sort(reverse=True)

    # Remove docstrings from text
    result_lines = lines[:]
    for start_line, end_line in ranges_to_remove:
        # Remove the range (inclusive)
        del result_lines[start_line : end_line + 1]

    return "".join(result_lines)


@dataclass
class ModuleSymbols:
    """Top-level symbols extracted from a Python module."""

    functions: set[str]
    classes: set[str]
    assignments: set[str]


def _extract_top_level_symbols(code: str) -> ModuleSymbols:
    """Extract top-level symbols from Python source code.

    Parses AST once and extracts functions, classes, and assignments.

    Args:
        code: Python source code to parse

    Returns:
        ModuleSymbols containing sets of function, class, and assignment names
    """
    functions: set[str] = set()
    classes: set[str] = set()
    assignments: set[str] = set()

    try:
        tree = ast.parse(code)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.add(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.add(node.name)
            elif isinstance(node, ast.Assign):
                # only consider simple names like x = ...
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                for target in targets:
                    assignments.add(target)
    except (SyntaxError, ValueError):
        # If code doesn't parse, return empty sets
        pass

    return ModuleSymbols(
        functions=functions,
        classes=classes,
        assignments=assignments,
    )


def detect_name_collisions(
    module_symbols: dict[str, ModuleSymbols],
    *,
    ignore_functions: set[str] | None = None,
) -> None:
    """Detect top-level name collisions across modules.

    Checks for functions, classes, and simple assignments that would
    conflict when stitched together.

    Args:
        module_symbols: Dict mapping module names to their extracted symbols
        ignore_functions: Optional set of function names to ignore when checking
            collisions (e.g., when auto-rename will handle them)

    Raises:
        RuntimeError: If collisions are detected
    """
    # list of harmless globals we don't mind having overwritten
    ignore = {
        "__all__",
        "__version__",
        "__author__",
        "__authors__",
        "__path__",
        "__package__",
        "__commit__",
    }

    symbols: dict[str, str] = {}  # name -> module
    collisions: list[tuple[str, str, str]] = []
    ignore_funcs = ignore_functions or set()

    # Sort module names for deterministic iteration order
    for mod, symbols_data in sorted(module_symbols.items()):
        # Check all symbol types (functions, classes, assignments)
        all_names = (
            symbols_data.functions | symbols_data.classes | symbols_data.assignments
        )

        # Sort for deterministic iteration order
        for name in sorted(all_names):
            # skip known harmless globals
            if name in ignore:
                continue

            # Skip function names that will be auto-renamed
            # (only skip if it's a function collision, not class/assignment)
            if name in ignore_funcs and name in symbols_data.functions:
                continue

            prev = symbols.get(name)
            if prev:
                collisions.append((name, prev, mod))
            else:
                symbols[name] = mod

    if collisions:
        # Sort collisions by name for deterministic error messages
        sorted_collisions = sorted(collisions, key=lambda x: x[0])
        collision_list = ", ".join(f"{name!r}" for name, _, _ in sorted_collisions)
        msg = f"Top-level name collisions detected: {collision_list}"
        raise RuntimeError(msg)


def verify_all_modules_listed(
    file_paths: list[Path], order_paths: list[Path], exclude_paths: list[Path]
) -> None:
    """Ensure all included files are listed in order or exclude paths.

    Args:
        file_paths: List of all included file paths
        order_paths: List of file paths in stitch order
        exclude_paths: List of file paths to exclude

    Raises:
        RuntimeError: If unlisted files are found
    """
    file_set = set(file_paths)
    order_set = set(order_paths)
    exclude_set = set(exclude_paths)
    known = order_set | exclude_set
    unknown = file_set - known

    if unknown:
        unknown_list = ", ".join(str(p) for p in sorted(unknown))
        msg = f"Unlisted source files detected: {unknown_list}"
        raise RuntimeError(msg)


def _resolve_relative_import(node: ast.ImportFrom, current_module: str) -> str | None:
    """Resolve relative import to absolute module name.

    Args:
        node: The ImportFrom AST node
        current_module: The current module name (e.g., "serger.actions")

    Returns:
        Resolved absolute module name, or None if relative import goes
        beyond package root
    """
    if node.level == 0:
        # Not a relative import
        return node.module or ""

    # Resolve relative import to absolute module name
    # e.g., from .constants in serger.actions -> serger.constants
    current_parts = current_module.split(".")
    # Go up 'level' levels from current module
    if node.level > len(current_parts):
        # Relative import goes beyond package root, skip
        return None
    base_parts = current_parts[: -node.level]
    if node.module:
        # Append the module name
        mod_parts = node.module.split(".")
        resolved_mod = ".".join(base_parts + mod_parts)
    else:
        # from . import something - use base only
        resolved_mod = ".".join(base_parts)
    return resolved_mod


def _is_internal_import(module_name: str, detected_packages: set[str]) -> bool:
    """Check if an import is internal (starts with detected package).

    Args:
        module_name: The module name to check
        detected_packages: Set of detected package names

    Returns:
        True if module_name equals or starts with any detected package
    """
    # Sort packages for deterministic iteration order
    for pkg in sorted(detected_packages):
        # Match only if mod equals pkg or starts with pkg + "."
        # This prevents false matches where a module name happens to
        # start with a package name (e.g., "foo_bar" matching "foo")
        if module_name == pkg or module_name.startswith(pkg + "."):
            return True
    return False


def _extract_import_module_info(  # pyright: ignore[reportUnusedFunction]
    node: ast.Import | ast.ImportFrom,
    current_module: str,
    detected_packages: set[str],
) -> tuple[str, bool] | None:
    """Extract module name and whether it's internal from import node.

    Args:
        node: The Import or ImportFrom AST node
        current_module: The current module name
        detected_packages: Set of detected package names

    Returns:
        Tuple of (module_name, is_internal), or None if not relevant
    """
    if isinstance(node, ast.ImportFrom):
        # Handle relative imports (node.level > 0)
        if node.level > 0:
            resolved_mod = _resolve_relative_import(node, current_module)
            if resolved_mod is None:
                # Relative import goes beyond package root
                return None
            mod = resolved_mod
        else:
            # Absolute import
            mod = node.module or ""

        # Check if import is internal
        is_internal = _is_internal_import(mod, detected_packages)
        return (mod, is_internal)

    if isinstance(node, ast.Import):  # pyright: ignore[reportUnnecessaryIsInstance]
        # For Import nodes, we need to check each alias
        # But this function returns a single result, so we'll handle
        # the first alias (caller can iterate if needed)
        if not node.names:
            return None
        mod = node.names[0].name
        # Check if import starts with any detected package
        # Note: Import nodes use startswith(pkg) not startswith(pkg + ".")
        # This is different from ImportFrom matching logic
        is_internal = False
        # Sort packages for deterministic iteration order
        for pkg in sorted(detected_packages):
            if mod.startswith(pkg):
                is_internal = True
                break
        return (mod, is_internal)

    return None


def _extract_internal_imports_for_deps(  # noqa: PLR0912
    source: str,
    module_name: str,
    detected_packages: set[str],
) -> set[str]:
    """Extract internal import module names for dependency graph building.

    This is a "dumb" extraction function that extracts only raw data - the
    set of internal module names that this module imports. The matching logic
    (checking against existing modules) is handled by the caller.

    Args:
        source: Source code of the module
        module_name: The current module name (e.g., "serger.actions")
        detected_packages: Set of detected package names

    Returns:
        Set of internal module names that this module imports (resolved from
        relative imports if needed). Includes relative imports that resolve to
        simple names (no dots) even if not package-prefixed, as they may match
        existing modules.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    internal_imports: set[str] = set()

    # Use ast.walk() to find ALL imports, including those inside
    # if/else blocks, functions, etc. This is necessary because
    # imports inside conditionals (like "if not __STITCHED__: from .x import y")
    # still represent dependencies that affect module ordering.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # Handle relative imports (node.level > 0)
            if node.level > 0:
                resolved_mod = _resolve_relative_import(node, module_name)
                if resolved_mod is None:
                    # Relative import goes beyond package root, skip
                    continue
                mod = resolved_mod
                # Check if relative import resolved to a simple name (no dots)
                # These may match existing modules even if not package-prefixed
                is_relative_resolved = mod and "." not in mod
            else:
                # Absolute import
                mod = node.module or ""
                is_relative_resolved = False

            # Check if import is internal (matches a detected package)
            matched_package = None
            # Sort packages for deterministic iteration order
            for pkg in sorted(detected_packages):
                # Match only if mod equals pkg or starts with pkg + "."
                # This prevents false matches where a module name happens to
                # start with a package name (e.g., "foo_bar" matching "foo")
                if mod == pkg or mod.startswith(pkg + "."):
                    matched_package = pkg
                    break

            # If relative import resolved to a simple name (no dots), include it
            # even if not package-prefixed, as it may match existing modules
            if is_relative_resolved and not matched_package:
                internal_imports.add(mod)
            elif matched_package:
                # Include the resolved module name for package-based matching
                internal_imports.add(mod)

        elif isinstance(node, ast.Import):
            # For Import nodes, check each alias
            for alias in node.names:
                mod = alias.name
                # Check if import starts with any detected package
                # Note: Import nodes use startswith(pkg) not startswith(pkg + ".")
                # This is different from ImportFrom matching logic
                # Sort packages for deterministic iteration order
                for pkg in sorted(detected_packages):
                    if mod.startswith(pkg):
                        internal_imports.add(mod)
                        break

    return internal_imports


def _deterministic_topological_sort(
    deps: dict[str, set[str]],
    module_to_file: dict[str, Path],
) -> list[str]:
    """Perform deterministic topological sort using file path as tie-breaker.

    When multiple nodes have zero in-degree, they are sorted by their file path
    to ensure deterministic ordering. This guarantees reproducible builds even
    when multiple valid topological orderings exist.

    Args:
        deps: Dependency graph mapping module names to sets of dependencies
        module_to_file: Mapping from module names to file paths

    Returns:
        Topologically sorted list of module names

    Raises:
        RuntimeError: If circular imports are detected
    """
    # Calculate in-degrees for all nodes
    # In-degree = number of dependencies this node has (how many nodes it depends on)
    in_degree: dict[str, int] = {
        node: len(node_deps) for node, node_deps in deps.items()
    }

    # Build reverse dependency graph for efficient edge removal
    # reverse_deps[dep] = set of nodes that depend on dep
    reverse_deps: dict[str, set[str]] = {node: set() for node in deps}
    for node, node_deps in deps.items():
        for dep in node_deps:
            if dep in reverse_deps:
                reverse_deps[dep].add(node)

    # Start with nodes that have zero in-degree (no dependencies)
    # Sort by file path to ensure deterministic ordering
    zero_in_degree = [node for node, degree in in_degree.items() if degree == 0]
    zero_in_degree.sort(key=lambda node: str(module_to_file.get(node, Path())))

    result: list[str] = []

    while zero_in_degree:
        # Process nodes in sorted order (by file path) for determinism
        # Sort again before processing to maintain determinism
        zero_in_degree.sort(key=lambda node: str(module_to_file.get(node, Path())))
        node = zero_in_degree.pop(0)
        result.append(node)

        # Remove edges from this node and update in-degrees of dependents
        # When we process a node, all nodes that depend on it can have their
        # in-degree decremented (since this dependency is now satisfied)
        for dependent in reverse_deps.get(node, set()):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                zero_in_degree.append(dependent)

    # Check for circular dependencies
    if len(result) != len(deps):
        # Find nodes that weren't processed (part of a cycle)
        remaining = set(deps) - set(result)
        msg = f"Circular dependency detected involving: {sorted(remaining)}"
        raise RuntimeError(msg)

    return result


def compute_module_order(  # noqa: C901, PLR0912
    file_paths: list[Path],
    package_root: Path,
    _package_name: str,
    file_to_include: dict[Path, IncludeResolved],
    *,
    detected_packages: set[str],
    source_bases: list[str] | None = None,
    user_provided_source_bases: list[str] | None = None,
) -> list[Path]:
    """Compute correct module order based on import dependencies.

    Uses topological sorting of internal imports to determine the correct
    order for stitching.

    Args:
        file_paths: List of file paths in initial order
        package_root: Common root of all included files
        _package_name: Root package name (unused, kept for API consistency)
        file_to_include: Mapping of file path to its include (for dest access)
        detected_packages: Pre-detected package names
        source_bases: Optional list of module base directories for external files
        user_provided_source_bases: Optional list of user-provided module bases
            (from config, excludes auto-discovered package directories)

    Returns:
        Topologically sorted list of file paths

    Raises:
        RuntimeError: If circular imports are detected
    """
    logger = getAppLogger()
    # Map file paths to derived module names
    file_to_module: dict[Path, str] = {}
    module_to_file: dict[str, Path] = {}
    for file_path in file_paths:
        include = file_to_include.get(file_path)
        module_name = derive_module_name(
            file_path,
            package_root,
            include,
            source_bases=source_bases,
            user_provided_source_bases=user_provided_source_bases,
            detected_packages=detected_packages,
        )
        file_to_module[file_path] = module_name
        module_to_file[module_name] = file_path

    # Build dependency graph using derived module names
    # file_paths is already sorted from collect_included_files, so dict insertion
    # order is deterministic
    deps: dict[str, set[str]] = {file_to_module[fp]: set() for fp in file_paths}

    for file_path in file_paths:
        module_name = file_to_module[file_path]
        if not file_path.exists():
            continue

        try:
            source = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Extract internal imports using the extraction function
        # This parses the AST once and extracts all internal module names
        internal_imports = _extract_internal_imports_for_deps(
            source, module_name, detected_packages
        )

        # Build dependency graph from extracted imports
        # The matching logic (checking against existing modules) stays here
        for mod in sorted(internal_imports):
            # Check if this is a relative import that resolved to a simple name
            # (no dots) - these may match existing modules directly
            is_relative_resolved = "." not in mod

            # Check if import matches a detected package
            matched_package = None
            # Sort packages for deterministic iteration order
            for pkg in sorted(detected_packages):
                # Match only if mod equals pkg or starts with pkg + "."
                # This prevents false matches where a module name happens to
                # start with a package name (e.g., "foo_bar" matching "foo")
                if mod == pkg or mod.startswith(pkg + "."):
                    matched_package = pkg
                    break

            logger.trace(
                "[DEPS] %s imports %s: matched_package=%s, is_relative_resolved=%s",
                module_name,
                mod,
                matched_package,
                is_relative_resolved,
            )

            # If relative import resolved to a simple name (no dots), check if it
            # matches any module name directly (for same-package imports)
            if not matched_package and is_relative_resolved:
                # Check if the resolved module name matches any module directly
                logger.trace(
                    "[DEPS] Relative import in %s: resolved_mod=%s, checking deps",
                    module_name,
                    mod,
                )
                # Sort for deterministic iteration order
                for dep_module in sorted(deps.keys()):
                    # Match if dep_module equals mod or starts with mod.
                    if (
                        dep_module == mod or dep_module.startswith(mod + ".")
                    ) and dep_module != module_name:
                        logger.trace(
                            "[DEPS] Found dependency: %s -> %s (from %s)",
                            module_name,
                            dep_module,
                            mod,
                        )
                        deps[module_name].add(dep_module)
                continue  # Skip the package-based matching below

            if matched_package:
                # Handle nested imports: package.core.base -> core.base
                # Remove package prefix and check if it matches any module
                mod_suffix = (
                    mod[len(matched_package) + 1 :]
                    if mod.startswith(matched_package + ".")
                    else mod[len(matched_package) :]
                    if mod == matched_package
                    else ""
                )
                if mod_suffix:
                    # Check if this matches any derived module name
                    # Match both the suffix (for same-package imports)
                    # and full module name (for cross-package imports)
                    # Sort for deterministic iteration order
                    for dep_module in sorted(deps.keys()):
                        # Match if: dep_module equals mod_suffix or mod
                        # or dep_module starts with mod_suffix or mod
                        prefix_tuple = (mod_suffix + ".", mod + ".")
                        matches = dep_module in (
                            mod_suffix,
                            mod,
                        ) or dep_module.startswith(prefix_tuple)
                        if matches and dep_module != module_name:
                            deps[module_name].add(dep_module)
                else:
                    # mod == matched_package
                    # (e.g., "from apathetic_logging import Logger")
                    # This is a package-level import, so depend on package.__init__
                    # (package-level imports need package.__init__ loaded first)
                    # Sort for deterministic iteration order
                    for dep_module in sorted(deps.keys()):
                        # Match if dep_module equals the package or starts with
                        # package + "." This ensures package-level imports depend
                        # on package.__init__
                        if (
                            dep_module == matched_package
                            or dep_module.startswith(matched_package + ".")
                        ) and dep_module != module_name:
                            logger.trace(
                                "[DEPS] Package-level import: %s -> %s (from %s)",
                                module_name,
                                dep_module,
                                mod,
                            )
                            deps[module_name].add(dep_module)

    # Perform deterministic topological sort using file path as tie-breaker
    # This ensures reproducible builds even when multiple valid orderings exist
    topo_modules = _deterministic_topological_sort(deps, module_to_file)

    # Convert back to file paths
    topo_paths = [module_to_file[mod] for mod in topo_modules if mod in module_to_file]
    return topo_paths


def suggest_order_mismatch(
    order_paths: list[Path],
    package_root: Path,
    _package_name: str,
    file_to_include: dict[Path, IncludeResolved],
    *,
    detected_packages: set[str],
    topo_paths: list[Path] | None = None,
    source_bases: list[str] | None = None,
    user_provided_source_bases: list[str] | None = None,
) -> None:
    """Warn if module order violates dependencies.

    Args:
        order_paths: List of file paths in intended order
        package_root: Common root of all included files
        _package_name: Root package name (unused, kept for API consistency)
        file_to_include: Mapping of file path to its include (for dest access)
        detected_packages: Pre-detected package names
        topo_paths: Optional pre-computed topological order. If provided,
                    skips recomputing the order. If None, computes it via
                    compute_module_order.
        source_bases: Optional list of module base directories for external files
        user_provided_source_bases: Optional list of user-provided module bases
            (from config, excludes auto-discovered package directories)
    """
    logger = getAppLogger()
    if topo_paths is None:
        topo_paths = compute_module_order(
            order_paths,
            package_root,
            _package_name,
            file_to_include,
            detected_packages=detected_packages,
            source_bases=source_bases,
        )

    # compare order_paths to topological sort
    mismatched = [
        p
        for p in order_paths
        if p in topo_paths and topo_paths.index(p) != order_paths.index(p)
    ]
    if mismatched:
        logger.warning("Possible module misordering detected:")

        for p in mismatched:
            include = file_to_include.get(p)
            module_name = derive_module_name(
                p,
                package_root,
                include,
                source_bases=source_bases,
                user_provided_source_bases=user_provided_source_bases,
                detected_packages=detected_packages,
            )
            logger.warning("  - %s appears before one of its dependencies", module_name)
        topo_modules = [
            derive_module_name(
                p,
                package_root,
                file_to_include.get(p),
                source_bases=source_bases,
                user_provided_source_bases=user_provided_source_bases,
                detected_packages=detected_packages,
            )
            for p in topo_paths
        ]
        logger.warning("Suggested order: %s", ", ".join(topo_modules))


def _is_inside_string_literal(text: str, pos: int) -> bool:
    """Check if a position in text is inside a string literal.

    Args:
        text: Source text to check
        pos: Position to check

    Returns:
        True if position is inside a string literal, False otherwise
    """
    # Track string state by scanning from start
    in_string = False
    string_char = None
    escape_next = False
    triple_quote = False
    i = 0

    while i < pos:
        char = text[i]

        if escape_next:
            escape_next = False
            i += 1
            continue

        if char == "\\":
            escape_next = True
            i += 1
            continue

        if not in_string:
            # Check for triple quotes first
            if i < len(text) - 2:
                triple_start = text[i : i + 3]
                if triple_start in ('"""', "'''"):
                    in_string = True
                    string_char = triple_start[0]
                    triple_quote = True
                    # Skip next two chars
                    i += 3
                    continue
            # Check for single quotes
            if char in ('"', "'"):
                in_string = True
                string_char = char
                triple_quote = False
        # Inside string - check for end
        elif triple_quote:
            if i < len(text) - 2 and string_char is not None:
                triple_end = text[i : i + 3]
                if triple_end == string_char * 3:
                    in_string = False
                    string_char = None
                    triple_quote = False
                    # Skip next two chars
                    i += 3
                    continue
        elif char == string_char:
            in_string = False
            string_char = None

        i += 1

    return in_string


def verify_no_broken_imports(  # noqa: C901, PLR0912
    final_text: str,
    package_names: list[str],
    internal_imports: "InternalImportMode | None" = None,
) -> None:
    """Verify all internal imports have been resolved in stitched script.

    Args:
        final_text: Final stitched script text
        package_names: List of all package names to check
            (e.g., ["serger", "apathetic_logs"])
        internal_imports: How internal imports are handled. If "keep", validation
            is skipped for kept imports since they are intentionally preserved.

    Raises:
        RuntimeError: If unresolved imports remain
    """
    # When internal_imports is "keep", skip validation for kept imports
    # since they are intentionally preserved and will work at runtime
    if internal_imports == "keep":
        return

    broken: set[str] = set()

    for package_name in package_names:
        # Pattern for nested imports: package.core.base or package.core
        # Matches: import package.module or import package.sub.module
        import_pattern = re.compile(rf"\bimport {re.escape(package_name)}\.([\w.]+)")
        # Pattern for top-level package import: import package
        # Matches: import package (without "from" and without a dot)
        import_package_pattern = re.compile(
            rf"\bimport {re.escape(package_name)}\b(?!\s*\.)"
        )
        # Pattern for from imports: from package.core import base or
        # from package.core.base import something
        from_pattern = re.compile(
            rf"\bfrom {re.escape(package_name)}\.([\w.]+)\s+import"
        )
        # Pattern for top-level package imports: from package import ...
        top_level_pattern = re.compile(rf"\bfrom {re.escape(package_name)}\s+import")

        # Helper to check if a module exists (header or shim)
        def module_exists(full_module_name: str, mod_suffix: str | None = None) -> bool:
            """Check if a module exists via header or shim."""
            # Check for header
            header_pattern_full = re.compile(
                rf"# === {re.escape(full_module_name)} ==="
            )
            if header_pattern_full.search(final_text):
                return True

            # Check for suffix header (backward compat)
            if mod_suffix:
                header_pattern_suffix = re.compile(
                    rf"# === {re.escape(mod_suffix)} ==="
                )
                if header_pattern_suffix.search(final_text):
                    return True

            # Check for shim
            escaped_name = re.escape(full_module_name)
            shim_pattern_old = re.compile(
                rf"_pkg\s*=\s*(?:['\"]){escaped_name}(?:['\"]).*?"
                rf"sys\.modules\[_pkg\]\s*=\s*_mod",
                re.DOTALL,
            )
            shim_pattern_new = re.compile(
                rf"_create_pkg_module\s*\(\s*(?:['\"]){escaped_name}(?:['\"])"
            )
            return (
                shim_pattern_old.search(final_text) is not None
                or shim_pattern_new.search(final_text) is not None
            )

        # Check import statements (nested: import package.module)
        for m in import_pattern.finditer(final_text):
            # Skip if inside string literal (docstring/comment)
            if _is_inside_string_literal(final_text, m.start()):
                continue

            mod_suffix = m.group(1)
            full_module_name = f"{package_name}.{mod_suffix}"
            if not module_exists(full_module_name, mod_suffix):
                broken.add(full_module_name)

        # Check top-level package import: import package
        for m in import_package_pattern.finditer(final_text):
            # Skip if inside string literal (docstring/comment)
            if _is_inside_string_literal(final_text, m.start()):
                continue

            # For top-level package imports, check if the package itself exists
            # This would be in a header like # === package === or
            # # === package.__init__ ===
            # OR it could be created via shims (when __init__.py is excluded)
            header_pattern = re.compile(
                rf"# === {re.escape(package_name)}(?:\.__init__)? ==="
            )
            # Check for shim-created package:
            # Old pattern: _pkg = 'package_name' followed by sys.modules[_pkg] = _mod
            # New pattern: _create_pkg_module('package_name')
            # Handle both single and double quotes (formatter may change them)
            escaped_name = re.escape(package_name)
            shim_pattern_old = re.compile(
                rf"_pkg\s*=\s*(?:['\"]){escaped_name}(?:['\"]).*?"
                rf"sys\.modules\[_pkg\]\s*=\s*_mod",
                re.DOTALL,
            )
            shim_pattern_new = re.compile(
                rf"_create_pkg_module\s*\(\s*(?:['\"]){escaped_name}(?:['\"])"
            )
            if (
                not header_pattern.search(final_text)
                and not shim_pattern_old.search(final_text)
                and not shim_pattern_new.search(final_text)
            ):
                broken.add(package_name)

        # Check from ... import statements
        for m in from_pattern.finditer(final_text):
            # Skip if inside string literal (docstring/comment)
            if _is_inside_string_literal(final_text, m.start()):
                continue

            mod_suffix = m.group(1)
            full_module_name = f"{package_name}.{mod_suffix}"
            if not module_exists(full_module_name, mod_suffix):
                broken.add(full_module_name)

        # Check top-level package imports: from package import ...
        for m in top_level_pattern.finditer(final_text):
            # Skip if inside string literal (docstring/comment)
            if _is_inside_string_literal(final_text, m.start()):
                continue

            # For top-level imports, check if the package itself exists
            # This would be in a header like # === package === or
            # # === package.__init__ ===
            # OR it could be created via shims (when __init__.py is excluded)
            header_pattern = re.compile(
                rf"# === {re.escape(package_name)}(?:\.__init__)? ==="
            )
            # Check for shim-created package:
            # Old pattern: _pkg = 'package_name' followed by sys.modules[_pkg] = _mod
            # New pattern: _create_pkg_module('package_name')
            # Handle both single and double quotes (formatter may change them)
            escaped_name = re.escape(package_name)
            shim_pattern_old = re.compile(
                rf"_pkg\s*=\s*(?:['\"]){escaped_name}(?:['\"]).*?"
                rf"sys\.modules\[_pkg\]\s*=\s*_mod",
                re.DOTALL,
            )
            shim_pattern_new = re.compile(
                rf"_create_pkg_module\s*\(\s*(?:['\"]){escaped_name}(?:['\"])"
            )
            if (
                not header_pattern.search(final_text)
                and not shim_pattern_old.search(final_text)
                and not shim_pattern_new.search(final_text)
            ):
                broken.add(package_name)

    if broken:
        broken_list = ", ".join(sorted(broken))
        msg = f"Unresolved internal imports: {broken_list}"
        raise RuntimeError(msg)


def force_mtime_advance(path: Path, seconds: float = 1.0, max_tries: int = 50) -> None:
    """Reliably bump a file's mtime, preserving atime and nanosecond precision.

    Ensures the change is visible before returning, even on lazy filesystems.
    We often can't use os.sleep or time.sleep because we monkeypatch it.

    Args:
        path: Path to file whose mtime to advance
        seconds: How many seconds to advance mtime
        max_tries: Maximum number of attempts

    Raises:
        AssertionError: If mtime could not be advanced after max_tries
    """
    real_time = importlib.import_module("time")  # immune to monkeypatch
    old_m = path.stat().st_mtime_ns
    ns_bump = int(seconds * 1_000_000_000)
    new_m: int = old_m

    for _attempt in range(max_tries):
        st = path.stat()
        os.utime(path, ns=(int(st.st_atime_ns), int(st.st_mtime_ns + ns_bump)))
        os.sync()  # flush kernel metadata

        new_m = path.stat().st_mtime_ns
        if new_m > old_m:
            return  # ✅ success
        real_time.sleep(0.00001)  # 10 µs pause before recheck

    xmsg = (
        f"bump_mtime({path}) failed to advance mtime after {max_tries} attempts "
        f"(old={old_m}, new={new_m})",
    )
    raise AssertionError(xmsg)


def _collect_modules(  # noqa: PLR0912, PLR0915, C901
    file_paths: list[Path],
    package_root: Path,
    _package_name: str,
    file_to_include: dict[Path, IncludeResolved],
    detected_packages: set[str],
    external_imports: ExternalImportMode = "top",
    internal_imports: InternalImportMode = "force_strip",
    comments_mode: CommentsMode = "keep",
    docstring_mode: DocstringMode = "keep",
    source_bases: list[str] | None = None,
    user_provided_source_bases: list[str] | None = None,
) -> tuple[dict[str, str], OrderedDict[str, None], list[str], list[str]]:
    """Collect and process module sources from file paths.

    Args:
        file_paths: List of file paths to stitch (in order)
        package_root: Common root of all included files
        _package_name: Root package name (unused, kept for API consistency)
        file_to_include: Mapping of file path to its include (for dest access)
        detected_packages: Pre-detected package names
        external_imports: How to handle external imports
        internal_imports: How to handle internal imports
        comments_mode: How to handle comments in stitched output
        docstring_mode: How to handle docstrings in stitched output
        source_bases: Optional list of module base directories for external files
        user_provided_source_bases: Optional list of user-provided module bases
            (from config, excludes auto-discovered package directories)

    Returns:
        Tuple of (module_sources, all_imports, parts, derived_module_names)
    """
    logger = getAppLogger()
    all_imports: OrderedDict[str, None] = OrderedDict()
    module_sources: dict[str, str] = {}
    parts: list[str] = []
    derived_module_names: list[str] = []

    # Reserve imports for shim system and main entry point
    all_imports.setdefault("import sys\n", None)  # For shim system and main()
    all_imports.setdefault("import types\n", None)  # For shim system (ModuleType)

    # Convert to sorted list for consistent behavior
    package_names_list = sorted(detected_packages)

    # Check if package_root is a package directory itself
    # (when all files are in a single package, package_root is that package)
    is_package_dir = (package_root / "__init__.py").exists()
    package_name_from_root: str | None = None
    if is_package_dir:
        package_name_from_root = package_root.name
    # Also treat as package directory if package_root.name matches package
    # (even without __init__.py, files in package_root are submodules of package)
    elif package_root.name == _package_name:
        package_name_from_root = package_root.name
        is_package_dir = True  # Treat as package directory for module naming

    # Check if any files have imports that reference the package name
    # (indicates files are part of that package structure)
    has_package_imports = False
    if package_root.name != _package_name and package_root.name in (
        "src",
        "lib",
        "app",
        "package",
        "packages",
    ):
        # Quick check: see if any file imports from the package
        for file_path in file_paths:
            if not file_path.exists():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
                # Check for imports that reference the package name
                if (
                    f"from {_package_name}" in content
                    or f"import {_package_name}" in content
                ):
                    has_package_imports = True
                    break
            except Exception:  # noqa: BLE001, S110
                # If we can't read the file, skip the check
                pass

    # ===== FIRST PASS: Derive all module names from file paths =====
    # This ensures all module names are available when processing imports,
    # providing consistent module name derivation regardless of file order.
    first_pass_module_names: dict[Path, str] = {}
    for file_path in file_paths:
        if not file_path.exists():
            file_display = shorten_path_for_display(file_path)
            logger.warning("Skipping missing file: %s", file_display)
            continue

        # Derive module name from file path
        include = file_to_include.get(file_path)
        module_name = derive_module_name(
            file_path,
            package_root,
            include,
            source_bases=source_bases,
            user_provided_source_bases=user_provided_source_bases,
            detected_packages=detected_packages,
        )

        # Apply same package name prepending logic as main loop
        # For files from installed package locations, check if module name already
        # matches a detected package (not the main package). If so, don't prepend.
        file_path_str = str(file_path)
        is_installed_package = (
            "site-packages" in file_path_str or "dist-packages" in file_path_str
        )
        should_prepend = True
        if is_installed_package:
            # Check if module name already starts with a detected package that's
            # not the main package (indicates it's already correctly structured)
            for pkg in sorted(detected_packages):
                if pkg != _package_name and (
                    module_name == pkg or module_name.startswith(f"{pkg}.")
                ):
                    should_prepend = False
                    logger.trace(
                        f"[COLLECT] First pass: skipping package name prepending "
                        f"for installed package: module={module_name}, "
                        f"detected_pkg={pkg}, main_pkg={_package_name}",
                    )
                    break

        if should_prepend:
            # If package_root is a package directory, preserve package structure
            if is_package_dir and package_name_from_root:
                # Handle __init__.py special case: represents the package itself
                if file_path.name == "__init__.py" and file_path.parent == package_root:
                    # Use package name as the module name (represents the package)
                    module_name = package_name_from_root
                else:
                    # Prepend package name to preserve structure
                    # e.g., "core" -> "oldpkg.core"
                    module_name = f"{package_name_from_root}.{module_name}"
            # If package name is provided but package_root.name doesn't match,
            # still prepend package name to ensure correct module structure
            # (e.g., files in src/ but package is testpkg -> testpkg.utils)
            # Only do this if package_root is a common project subdirectory
            # (like src, lib, app) AND files have imports that reference the package
            elif (
                package_root.name != _package_name
                and not module_name.startswith(f"{_package_name}.")
                and has_package_imports
                and module_name != _package_name
            ):
                # Prepend package name to module name
                module_name = f"{_package_name}.{module_name}"

        first_pass_module_names[file_path] = module_name

    # ===== SECOND PASS: Process files and imports using pre-derived names =====
    for file_path in file_paths:
        if not file_path.exists():
            # Missing files were already warned in first pass, skip here
            continue

        # Use pre-derived module name from first pass
        module_name = first_pass_module_names[file_path]
        derived_module_names.append(module_name)

        module_text = file_path.read_text(encoding="utf-8")
        module_text = strip_redundant_blocks(module_text)

        # Process comments according to mode
        # IMPORTANT: This must happen BEFORE split_imports, as split_imports
        # works with the text directly and will preserve any comments that
        # are still in the text at that point
        logger.trace(
            "Processing comments: mode=%s, file=%s, text_length=%d",
            comments_mode,
            file_path,
            len(module_text),
        )
        has_comment_before = "# This comment should be removed" in module_text
        module_text = process_comments(module_text, comments_mode)
        has_comment_after = "# This comment should be removed" in module_text
        logger.trace(
            "After process_comments: text_length=%d, had_comment_before=%s, "
            "has_comment_after=%s",
            len(module_text),
            has_comment_before,
            has_comment_after,
        )

        # Process docstrings according to mode
        # IMPORTANT: This must happen BEFORE split_imports, similar to comments
        logger.trace(
            "Processing docstrings: mode=%s, file=%s, text_length=%d",
            docstring_mode,
            file_path,
            len(module_text),
        )
        module_text = process_docstrings(module_text, docstring_mode)
        logger.trace(
            "After process_docstrings: text_length=%d",
            len(module_text),
        )

        # Extract imports - pass all detected package names and modes
        external_imports_list, module_body = split_imports(
            module_text, package_names_list, external_imports, internal_imports
        )
        # Store transformed body for symbol extraction (collision detection)
        # This ensures assign mode assignments are included in collision checks
        module_sources[f"{module_name}.py"] = module_body
        for imp in external_imports_list:
            all_imports.setdefault(imp, None)

        # Create module section - use derived module name in header
        # Note: serger-generated comments (like headers) are added here and should
        # remain even in strip mode, as they're part of serger's output, not user code
        header = f"# === {module_name} ==="
        parts.append(f"\n{header}\n{module_body.strip()}\n\n")

        file_display = shorten_path_for_display(file_path)
        logger.trace("Processed module: %s (from %s)", module_name, file_display)

    return module_sources, all_imports, parts, derived_module_names


def _extract_module_names_from_imports(
    all_imports: OrderedDict[str, None],
) -> set[str]:
    """Extract module names from external import statements.

    Args:
        all_imports: OrderedDict of import statement strings

    Returns:
        Set of module names extracted from imports
    """
    module_names: set[str] = set()
    for import_stmt_raw in all_imports:
        import_stmt = import_stmt_raw.strip()
        if not import_stmt:
            continue

        # Parse import statement using AST
        try:
            tree = ast.parse(import_stmt)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    # import module
                    # import module as alias
                    for alias in node.names:
                        module_names.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    # from module import ...
                    module_names.add(node.module)
        except SyntaxError:
            # If we can't parse it, try regex fallback
            # Match: import module
            import_match = re.match(r"^import\s+(\S+)", import_stmt)
            if import_match:
                module_name = import_match.group(1).split(" as ")[0].strip()
                module_names.add(module_name)
            # Match: from module import ...
            elif from_match := re.match(r"^from\s+(\S+)\s+import", import_stmt):
                module_name = from_match.group(1).strip()
                module_names.add(module_name)

    return module_names


def _check_external_import_shim_conflicts(
    all_imports: OrderedDict[str, None],
    shim_module_names: set[str],
) -> None:
    """Check for conflicts between external imports and shim module names.

    Args:
        all_imports: OrderedDict of external import statement strings
        shim_module_names: Set of shim module names that will be created

    Raises:
        ValueError: If any external import conflicts with a shim module name
    """
    external_modules = _extract_module_names_from_imports(all_imports)
    if not external_modules:
        return

    # Exclude serger-generated imports (types, sys) from conflict checking
    # These are required for shim generation and shouldn't conflict with user modules
    serger_required_imports = {"types", "sys"}
    external_modules = external_modules - serger_required_imports
    if not external_modules:
        return

    # Check for conflicts
    conflicts: list[tuple[str, str]] = []
    for ext_mod in sorted(external_modules):
        # Check if external module name matches any shim module name exactly
        if ext_mod in shim_module_names:
            conflicts.append((ext_mod, ext_mod))
        else:
            # Check if external module is a parent/child of any shim module
            # e.g., external "os" conflicts with shim "os.path"
            # e.g., external "os.path" conflicts with shim "os"
            # Also check if external name matches the last component of shim
            # (e.g., ext="subprocess" vs shim="testpkg.subprocess" is a conflict)
            for shim_mod in shim_module_names:
                if ext_mod == shim_mod:
                    conflicts.append((ext_mod, shim_mod))
                elif ext_mod.startswith(f"{shim_mod}."):
                    # External is a submodule of shim (e.g., ext="os.path", shim="os")
                    conflicts.append((ext_mod, shim_mod))
                elif shim_mod.startswith(f"{ext_mod}."):
                    # Shim is a submodule of external (e.g., ext="os", shim="os.path")
                    conflicts.append((ext_mod, shim_mod))
                elif shim_mod.split(".")[-1] == ext_mod:
                    # External module name matches the last component of shim
                    # (e.g., ext="subprocess", shim="testpkg.subprocess")
                    conflicts.append((ext_mod, shim_mod))

    if conflicts:
        # Sort conflicts for deterministic error messages
        sorted_conflicts = sorted(set(conflicts))
        conflict_list = [
            f"external import '{ext}' conflicts with shim module '{shim}'"
            for ext, shim in sorted_conflicts
        ]
        msg = (
            "External import conflicts with module shim:\n  "
            + "\n  ".join(conflict_list)
            + "\n\n"
            "Module shims cannot have the same name as external imports "
            "(from stdlib or third-party packages). "
            "Consider renaming the conflicting module using module_actions."
        )
        raise ValueError(msg)


def _format_header_line(
    *,
    display_name: str,
    description: str,
    package_name: str,
) -> str:
    """Format the header text based on config values.

    Rules:
    - Both provided: "DisplayName — Description"
    - Only name: "DisplayName"
    - Nothing: "package_name"
    - Only description: "package_name — Description"

    Args:
        display_name: Optional display name from config
        description: Optional description from config
        package_name: Package name (fallback)

    Returns:
        Formatted header text (without "# " prefix or trailing newline)
    """
    # Use display_name if provided, otherwise fall back to package_name
    name = display_name.strip() if display_name else package_name
    desc = description.strip() if description else ""

    if name and desc:
        return f"{name} — {desc}"
    if name:
        return f"{name}"
    # default to package_name
    return f"{package_name}"


def _format_license(license_text: str) -> str:
    """Format license text for inclusion in generated script.

    Rules:
    - Single line (no linebreaks): Format as "License: <license text>"
    - Multi-line (has linebreaks): Use block format with ====LICENSE==== header

    Args:
        license_text: License text to format

    Returns:
        Formatted license text with "# " prefix on each line, or empty string
    """
    if not license_text:
        return ""

    stripped = license_text.strip()
    if not stripped:
        return ""

    # Check if license text has linebreaks
    has_linebreaks = "\n" in stripped

    if has_linebreaks:
        # Multi-line format: Use block format
        lines = stripped.split("\n")
        prefixed_lines = [f"# {line}" for line in lines]
        return (
            "# ============LICENSE=============\n"
            + "\n".join(prefixed_lines)
            + "\n# ================================\n"
        )
    # Single line format: "License: <license text>"
    return f"# License: {stripped}\n"


def _build_final_script(  # noqa: C901, PLR0912, PLR0913, PLR0915
    *,
    package_name: str,
    all_imports: OrderedDict[str, None],
    parts: list[str],
    order_names: list[str],
    all_function_names: set[str],  # noqa: ARG001
    detected_packages: set[str],
    module_mode: str,
    module_actions: list[ModuleActionFull],
    shim: ShimSetting,
    order_paths: list[Path] | None = None,  # noqa: ARG001
    package_root: Path | None = None,  # noqa: ARG001
    file_to_include: dict[Path, IncludeResolved] | None = None,  # noqa: ARG001
    _original_order_names_for_shims: list[str] | None = None,
    license_text: str,
    version: str,
    commit: str,
    build_date: str,
    display_name: str = "",
    description: str = "",
    authors: str = "",
    repo: str = "",
    config: "RootConfigResolved | None" = None,
    selected_main_block: MainBlock | None = None,
    main_function_result: tuple[str, Path, str] | None = None,
    module_sources: dict[str, str] | None = None,
    source_bases: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Build the final stitched script.

    Args:
        package_name: Root package name
        all_imports: Collected external imports
        parts: Module code sections
        order_names: List of module names (for shim generation)
        all_function_names: Set of all function names from all modules
            (unused, kept for API consistency)
        config: Resolved configuration with main_mode and main_name
        selected_main_block: Selected __main__ block to use (if any)
        main_function_result: Result from find_main_function() if found
        module_sources: Mapping of module name to source code
        detected_packages: Pre-detected package names
        module_mode: How to generate import shims ("none", "multi", "force")
        module_actions: List of module actions (already normalized)
        shim: Shim setting ("all", "public", "none")
        order_paths: Optional list of file paths (unused, kept for API consistency)
        package_root: Optional common root (unused, kept for API consistency)
        file_to_include: Optional mapping (unused, kept for API consistency)
        license_text: License text (will be formatted automatically)
        version: Version string
        commit: Commit hash
        build_date: Build timestamp
        display_name: Optional display name for header
        description: Optional description for header
        authors: Optional authors for header
        repo: Optional repository URL for header
        source_bases: Optional list of source base directories for module name
            derivation and package detection

    Returns:
        Final script text
    """
    logger = getAppLogger()
    logger.debug("Building final script...")

    # Separate __future__ imports
    future_imports: OrderedDict[str, None] = OrderedDict()
    for imp in list(all_imports.keys()):
        if imp.strip().startswith("from __future__"):
            future_imports.setdefault(imp, None)
            del all_imports[imp]

    future_block = "".join(future_imports.keys())
    import_block = "".join(all_imports.keys())

    # Update module section headers in parts to use transformed names
    # This must happen BEFORE shim generation, as headers are part of the stitched code
    # Headers should be updated even when shims aren't generated (module_mode == "none")
    # Process user-specified module_actions to update headers
    # When scope: "original" is set, it affects original module names in stitched code
    # (including headers), regardless of affects value
    transformed_order_names: list[str] | None = None
    if module_actions:
        # Filter for actions with scope: "original"
        # (headers are part of original code structure, so scope: "original" applies)
        original_scope_actions_for_headers = [
            a for a in module_actions if a.get("scope") == "original"
        ]
        if original_scope_actions_for_headers:
            # Apply actions to order_names to get transformed names for headers
            transformed_order_names = apply_module_actions(
                list(order_names), original_scope_actions_for_headers, detected_packages
            )
            logger.debug(
                "Header update: order_names=%s, transformed_order_names=%s",
                order_names,
                transformed_order_names,
            )
            # Build mapping from order_names to transformed_order_names
            # (for updating headers)
            if len(transformed_order_names) != len(order_names):
                logger.warning(
                    "transformed_order_names length (%d) != order_names length (%d). "
                    "Header update may be incomplete.",
                    len(transformed_order_names),
                    len(order_names),
                )
            for i, original_name in enumerate(order_names):
                if i < len(transformed_order_names):
                    transformed_name = transformed_order_names[i]
                    if transformed_name != original_name:
                        # Update header - search and replace in parts
                        # Headers are created as "\n# === {module_name} ===\n"
                        # "{module_body}\n\n"
                        # Use simple string replacement (headers are on their own lines)
                        header_pattern = f"# === {original_name} ==="
                        new_header = f"# === {transformed_name} ==="
                        logger.debug(
                            "Header update: searching for pattern '%s' "
                            "to replace with '%s'",
                            header_pattern,
                            new_header,
                        )
                        # Update all parts that contain this header
                        # Replace all occurrences in each part
                        replaced = False
                        for j, part in enumerate(parts):
                            if header_pattern in part:
                                logger.debug(
                                    "Found header pattern in part %d: %s",
                                    j,
                                    repr(part[:100]),
                                )
                                # Replace the header pattern with new header
                                parts[j] = part.replace(header_pattern, new_header)
                                logger.debug(
                                    "Replaced header in part %d: %s",
                                    j,
                                    repr(parts[j][:100]),
                                )
                                replaced = True
                        if not replaced:
                            logger.debug(
                                "Header pattern '%s' not found in parts for "
                                "transformation to '%s'. Parts sample: %s",
                                header_pattern,
                                new_header,
                                [repr(p[:50]) for p in parts[:5]],
                            )

    # Build name mapping for module structure setup
    # Maps transformed full names -> original full names
    # This is used by _setup_pkg_modules() to find modules by original name
    # when they're registered with transformed names
    name_mapping: dict[str, str] = {}
    if transformed_order_names is not None:
        logger.trace(
            "Building name mapping: transformed_order_names=%s, order_names=%s",
            transformed_order_names,
            order_names,
        )
        # Build mapping from transformed to original names (both as full paths)
        for i, original_name in enumerate(order_names):
            if i < len(transformed_order_names):
                transformed_name = transformed_order_names[i]
                if transformed_name != original_name:
                    # Convert both to full paths for name mapping
                    # Always use full paths with package_name prefix for name mapping
                    # Original name -> full path
                    if original_name == package_name:
                        original_full = package_name
                    elif original_name.startswith(f"{package_name}."):
                        original_full = original_name
                    else:
                        # Always prepend package_name for name mapping
                        # (we need consistent full paths in the mapping)
                        original_full = f"{package_name}.{original_name}"

                    # Transformed name -> full path
                    # Always use full paths with package_name prefix for name mapping
                    if transformed_name == package_name:
                        transformed_full = package_name
                    elif transformed_name.startswith(f"{package_name}."):
                        transformed_full = transformed_name
                    else:
                        # Always prepend package_name for name mapping
                        transformed_full = f"{package_name}.{transformed_name}"

                    # Map transformed -> original
                    name_mapping[transformed_full] = original_full
                    logger.trace(
                        "Name mapping entry: %s -> %s (original: %s, transformed: %s)",
                        transformed_full,
                        original_full,
                        original_name,
                        transformed_name,
                    )

    # Generate import shims based on module_actions and shim setting
    # If shim == "none" or module_mode == "none", skip shim generation
    if shim == "none" or module_mode == "none":
        # No shims generated
        shim_text = ""
    else:
        # IMPORTANT: Module names in order_names are relative to package_root
        # (e.g., "utils.utils_text"), but shims need full paths
        # (e.g., "serger.utils.utils_text").
        # Note: If specific modules should be excluded, use the 'exclude' config option
        # When files are filtered by affects: "stitching", use original module names
        # for shim generation (shims should still be generated even if files are
        # filtered from stitching)
        if _original_order_names_for_shims is not None:
            shim_names_raw = list(_original_order_names_for_shims)
        else:
            shim_names_raw = list(order_names)

        # Generate actions from module_mode if specified (and not "none"/"multi")
        # Actions should be applied to original module names BEFORE prepending
        # package_name
        all_actions: list[ModuleActionFull] = []
        if module_mode and module_mode not in ("none", "multi"):
            logger.trace(
                "[SHIM_GEN] Generating actions: module_mode=%s, "
                "shim_names_raw=%s, order_names=%s",
                module_mode,
                shim_names_raw[:5] if shim_names_raw else None,
                order_names[:5] if order_names else None,
            )
            auto_actions = generate_actions_from_mode(
                module_mode,
                detected_packages,
                package_name,
                module_names=shim_names_raw,
                source_bases=source_bases,
            )
            # Apply defaults to mode-generated actions (scope: "original" set here)
            normalized_actions = [
                set_mode_generated_action_defaults(action) for action in auto_actions
            ]
            logger.trace(
                "[SHIM_GEN] Generated %d actions: %s",
                len(normalized_actions),
                [f"{a.get('source')} -> {a.get('dest')}" for a in normalized_actions],
            )
            all_actions.extend(normalized_actions)

        # Add user-specified module_actions from RootConfigResolved
        # These are already fully normalized with scope: "shim" set (iteration 04)
        if module_actions:  # Already list[ModuleActionFull] with all defaults applied
            all_actions.extend(module_actions)

        # Separate actions by affects value
        (
            shims_only_actions,
            _stitching_only_actions,
            both_actions,
        ) = separate_actions_by_affects(all_actions)

        # Separate shim actions by scope
        # Note: Actions with scope: "original" must be applied BEFORE prepending
        # package_name (they operate on original module names), so we include them
        # from both shims_only_actions and both_actions
        # Actions with scope: "shim" and affects: "shims" are applied after
        # prepending (they operate on full module paths)
        original_scope_actions = [
            a for a in shims_only_actions + both_actions if a.get("scope") == "original"
        ]
        shim_scope_actions = [a for a in both_actions if a.get("scope") == "shim"]

        # Apply scope: "original" actions to original module names (before prepending)
        transformed_names = shim_names_raw
        if original_scope_actions:
            logger.trace(
                "[SHIM_GEN] Applying %d original-scope actions to: %s",
                len(original_scope_actions),
                shim_names_raw[:5] if shim_names_raw else None,
            )
            # Build available_modules set for validation
            available_modules_for_validation = set(shim_names_raw)
            # Add all action sources to available_modules since mode-generated
            # actions only reference root packages that should exist
            for action in original_scope_actions:
                source = action.get("source")
                if source:
                    available_modules_for_validation.add(source)
            # Also add package names from detected_packages that appear anywhere
            # in module names (as a fallback for edge cases)
            for pkg in detected_packages:
                if pkg != package_name and pkg not in available_modules_for_validation:
                    # Check if this package appears anywhere in module names
                    for mod_name in shim_names_raw:
                        if (
                            f".{pkg}." in mod_name
                            or mod_name.startswith(f"{pkg}.")
                            or mod_name == pkg
                            or mod_name.endswith(f".{pkg}")
                        ):
                            available_modules_for_validation.add(pkg)
                            break
            # Validate other constraints (dest conflicts, circular moves, etc.)
            validate_module_actions(
                original_scope_actions,
                available_modules_for_validation,
                detected_packages,
                scope="original",
            )
            transformed_names = apply_module_actions(
                transformed_names, original_scope_actions, detected_packages
            )
            # Note: Header updates are now handled outside the shim generation block
            # (before this conditional) so they work even when module_mode == "none"

        # Now prepend package_name to create full module paths
        # Module names are relative to package_root, so we need to prepend package_name
        # to get the full import path
        # (e.g., "utils.utils_text" -> "serger.utils.utils_text")
        # Note: flat mode has special handling for loose files (keeps them top-level)
        shim_names: list[str] = []
        for name in transformed_names:
            # Flat mode: treat loose files as top-level modules (not under package)
            # Packages still get shims as usual
            if module_mode == "flat":
                if name == package_name:
                    full_name = package_name
                elif name.startswith(f"{package_name}."):
                    full_name = name
                elif "." in name:
                    # Has dots: treat as package structure, use multi mode logic
                    first_part = name.split(".", 1)[0]
                    if first_part in detected_packages and first_part != package_name:
                        full_name = name
                    else:
                        full_name = f"{package_name}.{name}"
                else:
                    # Loose file: keep as top-level module (no package prefix)
                    full_name = name
            # Multi mode logic: use detected packages (default behavior)
            # If name already equals package_name, it's the root module itself
            elif name == package_name:
                full_name = package_name
            # If name already starts with package_name, use it as-is
            elif name.startswith(f"{package_name}."):
                full_name = name
            # If name contains dots and starts with a different detected package,
            # it's from another package (multi-package scenario) - use as-is
            elif "." in name:
                first_part = name.split(".", 1)[0]
                # If first part is a detected package different from package_name,
                # check if it's actually a subpackage of package_name
                # (i.e., if it appears as a top-level module in transformed_names)
                if (
                    first_part in detected_packages
                    and first_part != package_name
                    and first_part not in transformed_names
                ):
                    # First part is a separate package (not in our module list)
                    # - use as-is
                    full_name = name
                else:
                    # Likely a subpackage of package_name - prepend package_name
                    full_name = f"{package_name}.{name}"
            else:
                # Top-level module under package: prepend package_name
                full_name = f"{package_name}.{name}"
            shim_names.append(full_name)

        # Validate and apply scope: "shim" actions (incremental validation)
        if shim_scope_actions:
            for action in shim_scope_actions:
                # Skip source validation for delete actions (they match flexibly)
                action_type = action.get("action", "move")
                if action_type != "delete":
                    # For move/copy actions, validate source exists
                    # After mode transformations, source might need component matching
                    # (e.g., "mypkg.module" might need to match "mypkg.pkg1.module")
                    source = action.get("source")
                    if source:
                        if source not in shim_names:
                            # Check if source matches any component in shim_names
                            # For "mypkg.module", check if it matches
                            # "mypkg.pkg1.module" by checking if all components
                            # of source appear in module name
                            source_parts = source.split(".")
                            matching_modules = [
                                name
                                for name in shim_names
                                if (
                                    name == source
                                    or name.startswith(f"{source}.")
                                    or all(
                                        part in name.split(".") for part in source_parts
                                    )
                                )
                            ]
                            if not matching_modules:
                                available = sorted(shim_names)
                                msg = (
                                    f"Module action source '{source}' "
                                    f"does not exist in available modules "
                                    f"(scope: 'shim'). Available: {available}"
                                )
                                raise ValueError(msg)
                            # Component matching found - skip exact validation
                            # The action handler will use component matching
                        else:
                            # Exact match found - use standard validation
                            validate_action_source_exists(
                                action, set(shim_names), scope="shim"
                            )
                shim_names = apply_single_action(shim_names, action, detected_packages)

        # Apply shims_only_actions after prepending package_name
        # These actions only affect shim generation, so they're applied to
        # the final shim_names list (after prepending package_name)
        # This allows delete actions to match against full module paths like
        # "mypkg.pkg1"
        # Note: Exclude scope: "original" actions from shims_only_actions since
        # they've already been applied in original_scope_actions (before prepending)
        shims_only_actions_filtered = [
            a for a in shims_only_actions if a.get("scope") != "original"
        ]
        if shims_only_actions_filtered:
            for action in shims_only_actions_filtered:
                # Skip source validation for delete actions (they match flexibly)
                action_type = action.get("action", "move")
                if action_type != "delete":
                    # For non-delete actions, validate source exists
                    # Note: source might be relative (scope: "original") or absolute
                    # (scope: "shim"), so we need to handle both cases
                    action_scope = action.get("scope", "shim")
                    if action_scope == "shim":
                        source = action.get("source")
                        if source:
                            if source not in shim_names:
                                # Check if source matches any component in shim_names
                                # For "mypkg.module", check if it matches
                                # "mypkg.pkg1.module" by checking if all components
                                # of source appear in the module name
                                source_parts = source.split(".")
                                matching_modules = [
                                    name
                                    for name in shim_names
                                    if (
                                        name == source
                                        or name.startswith(f"{source}.")
                                        or all(
                                            part in name.split(".")
                                            for part in source_parts
                                        )
                                    )
                                ]
                                if not matching_modules:
                                    available = sorted(shim_names)
                                    msg = (
                                        f"Module action source '{source}' "
                                        f"does not exist in available modules "
                                        f"(scope: 'shim', affects: 'shims'). "
                                        f"Available: {available}"
                                    )
                                    raise ValueError(msg)
                                # Component matching found - skip exact validation
                            else:
                                # Exact match found - use standard validation
                                validate_action_source_exists(
                                    action, set(shim_names), scope="shim"
                                )
                    # For scope: "original", the source is relative, so we need to
                    # check if it matches any component in shim_names
                    # (e.g., source "pkg1" should match "mypkg.pkg1")
                    elif action_scope == "original":
                        source = action.get("source")
                        if source:
                            # Check if source appears as a component in any shim_name
                            source_found = False
                            for shim_name in shim_names:
                                if (
                                    shim_name == source
                                    or shim_name.startswith(f"{source}.")
                                    or source in shim_name.split(".")
                                ):
                                    source_found = True
                                    break
                            if not source_found:
                                available = sorted(shim_names)
                                msg = (
                                    f"Module action source '{source}' does not exist "
                                    f"in available modules (scope: 'original', "
                                    f"affects: 'shims'). Available: {available}"
                                )
                                raise ValueError(msg)
                shim_names = apply_single_action(shim_names, action, detected_packages)

        # Check for shim-stitching mismatches and apply cleanup
        # Build set of modules that are in stitched code
        # (from order_names after filtering)
        # order_names contains the module names that were actually stitched
        # Convert to full module paths (with package_name prefix) for comparison
        # This matches the format of shim_names
        stitched_modules_full: set[str] = set()
        for name in order_names:
            # Apply same logic as shim name generation to get full path
            if module_mode == "flat":
                if name == package_name:
                    full_name = package_name
                elif name.startswith(f"{package_name}."):
                    full_name = name
                elif "." in name:
                    first_part = name.split(".", 1)[0]
                    if first_part in detected_packages and first_part != package_name:
                        full_name = name
                    else:
                        full_name = f"{package_name}.{name}"
                else:
                    full_name = name
            elif name == package_name:
                full_name = package_name
            elif name.startswith(f"{package_name}."):
                full_name = name
            elif "." in name:
                first_part = name.split(".", 1)[0]
                if first_part in detected_packages and first_part != package_name:
                    full_name = name
                else:
                    full_name = f"{package_name}.{name}"
            else:
                full_name = f"{package_name}.{name}"
            stitched_modules_full.add(full_name)

        # Check for mismatches
        shim_modules_set = set(shim_names)
        mismatches = check_shim_stitching_mismatches(
            shim_modules_set, stitched_modules_full, all_actions
        )

        # Apply cleanup behavior
        if mismatches:
            updated_shims, _warnings = apply_cleanup_behavior(
                mismatches, shim_modules_set
            )
            # Update shim_names to reflect cleanup
            shim_names = sorted(updated_shims)

        # Check for conflicts between external imports and shim module names
        # We're already in the shim generation block, so shims are enabled
        # Only check shims that are in the package being stitched (not dependencies)
        package_shim_names = {
            name
            for name in shim_names
            if name == package_name or name.startswith(f"{package_name}.")
        }
        _check_external_import_shim_conflicts(all_imports, package_shim_names)

        # Group modules by their parent package
        # parent_package -> list of (module_name, is_direct_child)
        # is_direct_child means the module is directly under this package
        # (not nested deeper)
        packages: dict[str, list[tuple[str, bool]]] = {}
        # parent_pkg -> [(module_name, is_direct)]
        # Track top-level modules for flat mode
        top_level_modules: list[str] = []

        # Use transformed_order_names for module structure if available
        # (for actions with scope: "original", the module structure should use
        # transformed names, not original names)
        # However, if shim transformations have been applied, use final shim_names
        # instead (which includes all transformations)
        # shim_names is used for shim generation, but module structure should
        # use transformed names when scope: "original" actions are applied
        # transformed_order_names is initialized above (line 1829) and set if
        # original_scope_actions_for_headers is not empty
        module_names_for_structure = shim_names
        logger.trace(
            "Module structure setup: shim_names=%s, transformed_order_names=%s",
            shim_names,
            transformed_order_names,
        )
        # Only use transformed_order_names if no shim transformations were applied
        # (shim_names already includes all transformations if shim actions exist)
        has_shim_transformations = any(
            a.get("scope") == "shim"
            for a in (module_actions or [])
            if a.get("affects", "shims") in ("shims", "both")
        )
        if transformed_order_names is not None and not has_shim_transformations:  # pyright: ignore[reportPossiblyUnboundVariable]
            # transformed_order_names contains transformed module names
            # (relative to package_root)
            # We need to convert them to full module paths (with package_name prefix)
            # to match the format of shim_names
            transformed_full_names: list[str] = []
            for name in transformed_order_names:  # pyright: ignore[reportPossiblyUnboundVariable]
                # Apply same logic as shim name generation to get full path
                if module_mode == "flat":
                    if name == package_name:
                        full_name = package_name
                    elif name.startswith(f"{package_name}."):
                        full_name = name
                    elif "." in name:
                        first_part = name.split(".", 1)[0]
                        if (
                            first_part in detected_packages
                            and first_part != package_name
                        ):
                            full_name = name
                        else:
                            full_name = f"{package_name}.{name}"
                    else:
                        full_name = name
                elif name == package_name:
                    full_name = package_name
                elif name.startswith(f"{package_name}."):
                    full_name = name
                elif "." in name:
                    first_part = name.split(".", 1)[0]
                    if first_part in detected_packages and first_part != package_name:
                        full_name = name
                    else:
                        full_name = f"{package_name}.{name}"
                else:
                    full_name = f"{package_name}.{name}"
                transformed_full_names.append(full_name)
            module_names_for_structure = transformed_full_names
            logger.trace(
                "Using transformed names for structure: %s (package_name=%s)",
                transformed_full_names,
                package_name,
            )

        for module_name in module_names_for_structure:
            logger.trace(
                "Processing module for structure: %s (package_name=%s)",
                module_name,
                package_name,
            )
            if "." not in module_name:
                # Top-level module
                if module_mode == "flat":
                    # In flat mode, top-level modules are not under any package
                    top_level_modules.append(module_name)
                else:
                    # In other modes, parent is the root package
                    parent = package_name
                    is_direct = True
                    if parent not in packages:
                        packages[parent] = []
                    packages[parent].append((module_name, is_direct))
                    logger.trace(
                        "Added module %s to package %s (is_direct=%s)",
                        module_name,
                        parent,
                        is_direct,
                    )
            else:
                # Find the parent package (everything except the last component)
                name_parts = module_name.split(".")
                parent = ".".join(name_parts[:-1])
                is_direct = True  # This module is directly under its parent

                if parent not in packages:
                    packages[parent] = []
                packages[parent].append((module_name, is_direct))
                logger.trace(
                    "Added module %s to package %s (is_direct=%s)",
                    module_name,
                    parent,
                    is_direct,
                )

        # Rebuild name mapping using final shim_names (after all transformations)
        # This ensures the mapping reflects the final state after both original and
        # shim transformations
        if transformed_order_names is not None:
            logger.trace(
                "Rebuilding name mapping from final shim_names: shim_names=%s, "
                "order_names=%s",
                shim_names,
                order_names,
            )
            # Build mapping from final transformed names to original names
            # We need to match shim_names (final) back to order_names (original)
            name_mapping.clear()
            # Convert order_names to full paths for matching
            original_full_paths: list[str] = []
            for original_name in order_names:
                if original_name == package_name:
                    original_full = package_name
                elif original_name.startswith(f"{package_name}."):
                    original_full = original_name
                else:
                    original_full = f"{package_name}.{original_name}"
                original_full_paths.append(original_full)

            # Match shim_names to original_full_paths by position
            # (assuming they're in the same order)
            for i, final_name in enumerate(shim_names):
                if i < len(original_full_paths):
                    original_full = original_full_paths[i]
                    if final_name != original_full:
                        name_mapping[final_name] = original_full
                        logger.trace(
                            "Rebuilt name mapping: %s -> %s",
                            final_name,
                            original_full,
                        )

        # Collect all package names (both intermediate and top-level)
        # Use module_names_for_structure to include packages from transformed names
        all_packages: set[str] = set()
        logger.trace(
            "Collecting packages from shim_names=%s and module_names_for_structure=%s",
            shim_names,
            module_names_for_structure,
        )
        # Collect from both shim_names (for shim generation) and
        # module_names_for_structure (for transformed structure)
        for module_name in shim_names:
            # Skip top-level modules in flat mode (they're not in packages)
            if module_mode == "flat" and "." not in module_name:
                continue
            name_parts = module_name.split(".")
            # Add all package prefixes
            # (e.g., for "serger.utils.utils_text" add "serger" and "serger.utils")
            for i in range(1, len(name_parts)):
                pkg = ".".join(name_parts[:i])
                all_packages.add(pkg)
            # Also add the top-level package if module has dots
            if "." in module_name:
                all_packages.add(name_parts[0])
        # Also collect packages from transformed structure
        for module_name in module_names_for_structure:
            # Skip top-level modules in flat mode (they're not in packages)
            if module_mode == "flat" and "." not in module_name:
                continue
            name_parts = module_name.split(".")
            # Add all package prefixes
            for i in range(1, len(name_parts)):
                pkg = ".".join(name_parts[:i])
                all_packages.add(pkg)
            # Also add the top-level package if module has dots
            if "." in module_name:
                all_packages.add(name_parts[0])
        # Add root package if not already present (unless flat mode with no packages)
        if module_mode != "flat" or all_packages:
            all_packages.add(package_name)

        # Add detected packages that have modules in the final output
        # This is important when files from outside the config directory are included
        # and packages are detected via source_bases but not directly referenced
        # in module names (e.g., when __init__.py is excluded)
        # Only add packages that actually have modules (not deleted by actions)
        all_module_names = set(shim_names) | set(module_names_for_structure)
        for detected_pkg in detected_packages:
            # Check if any module belongs to this package
            # Module must start with package name (exact match or package.module)
            # to ensure we only add packages that are actually used as packages,
            # not just components of other package names
            has_modules = any(
                mod == detected_pkg or mod.startswith(f"{detected_pkg}.")
                for mod in all_module_names
            )
            if has_modules:
                all_packages.add(detected_pkg)

        logger.trace(
            "Collected packages: %s (package_name=%s, detected_packages=%s)",
            sorted(all_packages),
            package_name,
            sorted(detected_packages),
        )

        # Sort packages by depth (shallowest first) to create parents before children
        # Use package name as secondary sort key to ensure deterministic ordering
        # when multiple packages have the same depth
        sorted_packages = sorted(all_packages, key=lambda p: (p.count("."), p))
        logger.trace("Sorted packages (by depth, then name): %s", sorted_packages)

        # Generate shims for each package
        # Each package gets its own module object to maintain proper isolation
        shim_blocks: list[str] = []
        shim_blocks.append("# --- import shims for stitched runtime ---")
        # Note: types and sys are imported at the top level (see all_imports)

        # Helper function to create/register package modules
        shim_blocks.append("def _create_pkg_module(pkg_name: str) -> types.ModuleType:")
        shim_blocks.append(
            '    """Create a package module and set up parent relationships."""'
        )
        shim_blocks.append("    # Always create a new module object for packages")
        shim_blocks.append("    # Don't reuse existing modules - they might be the")
        shim_blocks.append("    # stitched module itself or have wrong attributes")
        shim_blocks.append("    _mod = types.ModuleType(pkg_name)")
        shim_blocks.append("    _mod.__package__ = pkg_name")
        shim_blocks.append("    sys.modules[pkg_name] = _mod")
        shim_blocks.append(
            "    # Set up parent-child relationships for nested packages"
        )
        shim_blocks.append("    if '.' in pkg_name:")
        shim_blocks.append("        _parent_pkg = '.'.join(pkg_name.split('.')[:-1])")
        shim_blocks.append("        _child_name = pkg_name.split('.')[-1]")
        shim_blocks.append("        _parent = sys.modules.get(_parent_pkg)")
        shim_blocks.append("        if _parent:")
        shim_blocks.append("            setattr(_parent, _child_name, _mod)")
        shim_blocks.append("    return _mod")
        shim_blocks.append("")

        # ignores must be on their own line
        # or they may get reformated to the wrong place
        shim_blocks.append("def _setup_pkg_modules(  # noqa: C901, PLR0912")
        shim_blocks.append(
            "pkg_name: str, module_names: list[str], "
            "name_mapping: dict[str, str] | None = None"
        )
        shim_blocks.append(") -> None:")
        shim_blocks.append(
            '    """Set up package module attributes and register submodules."""'
        )
        shim_blocks.append("    _mod = sys.modules.get(pkg_name)")
        shim_blocks.append("    if not _mod:")
        shim_blocks.append("        return")
        shim_blocks.append("    # Copy attributes from all modules under this package")
        shim_blocks.append("    _globals = globals()")
        shim_blocks.append("    # Debug: log what's in globals for this package")
        shim_blocks.append("    # Note: This copies all globals to the package module")
        shim_blocks.append("    for _key, _value in _globals.items():")
        shim_blocks.append("        setattr(_mod, _key, _value)")
        shim_blocks.append(
            "    # Set up package attributes for nested packages BEFORE registering"
        )
        shim_blocks.append(
            "    # modules (so packages are available when modules are registered)"
        )
        shim_blocks.append("    _seen_packages: set[str] = set()")
        shim_blocks.append("    for _name in module_names:")
        shim_blocks.append(
            "        if _name != pkg_name and _name.startswith(pkg_name + '.'):"
        )
        shim_blocks.append(
            "            # Extract parent package (e.g., mypkg.public from"
        )
        shim_blocks.append("            # mypkg.public.utils)")
        shim_blocks.append("            _name_parts = _name.split('.')")
        shim_blocks.append("            if len(_name_parts) > 2:  # noqa: PLR2004")
        shim_blocks.append("                # Has at least one intermediate package")
        shim_blocks.append("                _parent_pkg = '.'.join(_name_parts[:-1])")
        shim_blocks.append(
            "                if _parent_pkg.startswith(pkg_name + '.') and "
            "_parent_pkg not in _seen_packages:"
        )
        shim_blocks.append("                    _seen_packages.add(_parent_pkg)")
        shim_blocks.append(
            "                    _pkg_obj = sys.modules.get(_parent_pkg)"
        )
        shim_blocks.append("                    if _pkg_obj and _pkg_obj != _mod:")
        shim_blocks.append("                        # Set parent package as attribute")
        shim_blocks.append("                        _pkg_attr_name = _name_parts[1]")
        shim_blocks.append(
            "                        if not hasattr(_mod, _pkg_attr_name):"
        )
        shim_blocks.append(
            "                            setattr(_mod, _pkg_attr_name, _pkg_obj)"
        )
        shim_blocks.append("    # Register all modules under this package")
        shim_blocks.append("    for _name in module_names:")
        shim_blocks.append("        # Try to find module by transformed name first")
        shim_blocks.append("        _module_obj = sys.modules.get(_name)")
        shim_blocks.append("        if not _module_obj and name_mapping:")
        shim_blocks.append("            # If not found, try to find by original name")
        shim_blocks.append("            _original_name = name_mapping.get(_name)")
        shim_blocks.append("            if _original_name:")
        shim_blocks.append(
            "                _module_obj = sys.modules.get(_original_name)"
        )
        shim_blocks.append("                if _module_obj:")
        shim_blocks.append("                    # Register with transformed name")
        shim_blocks.append("                    sys.modules[_name] = _module_obj")
        shim_blocks.append("        # If still not found, use package module")
        shim_blocks.append("        if not _module_obj:")
        shim_blocks.append("            sys.modules[_name] = _mod")
        shim_blocks.append("    # Set submodules as attributes on parent package")
        shim_blocks.append("    for _name in module_names:")
        shim_blocks.append(
            "        if _name != pkg_name and _name.startswith(pkg_name + '.'):"
        )
        shim_blocks.append("            _submodule_name = _name.split('.')[-1]")
        shim_blocks.append("            # Try to get actual module object")
        shim_blocks.append("            _module_obj = sys.modules.get(_name)")
        shim_blocks.append("            if not _module_obj and name_mapping:")
        shim_blocks.append("                _original_name = name_mapping.get(_name)")
        shim_blocks.append("                if _original_name:")
        shim_blocks.append(
            "                    _module_obj = sys.modules.get(_original_name)"
        )
        shim_blocks.append(
            "            # Use actual module object if found, otherwise package"
        )
        shim_blocks.append("            _target = _module_obj if _module_obj else _mod")
        shim_blocks.append("            if not hasattr(_mod, _submodule_name):")
        shim_blocks.append("                setattr(_mod, _submodule_name, _target)")
        shim_blocks.append(
            "            elif isinstance(getattr(_mod, _submodule_name, None), "
            "types.ModuleType):"
        )
        shim_blocks.append("                setattr(_mod, _submodule_name, _target)")
        shim_blocks.append("")

        # First pass: Create all package modules and set up parent-child relationships
        shim_blocks.extend(
            f"_create_pkg_module({pkg_name!r})" for pkg_name in sorted_packages
        )

        shim_blocks.append("")

        # Build name mapping dict as string for shim code
        # Maps transformed full names -> original full names
        name_mapping_str = (
            "{"
            + ", ".join(f"{k!r}: {v!r}" for k, v in sorted(name_mapping.items()))
            + "}"
            if name_mapping
            else "None"
        )
        _max_name_mapping_log_length = 200
        logger.trace(
            "Name mapping for shim code: %s (dict size: %d)",
            (
                name_mapping_str[:_max_name_mapping_log_length]
                if len(name_mapping_str) > _max_name_mapping_log_length
                else name_mapping_str
            ),
            len(name_mapping),
        )

        # Second pass: Copy attributes and register modules
        # Process in any order since all modules are now created
        logger.trace("Packages dict: %s", packages)
        for pkg_name in sorted_packages:
            logger.trace(
                "Processing package %s (in packages dict: %s)",
                pkg_name,
                pkg_name in packages,
            )
            if pkg_name not in packages:
                # Package has no direct modules, but might have subpackages
                # We still need to set it up so it's accessible
                logger.trace(
                    "Package %s has no direct modules, but setting up anyway",
                    pkg_name,
                )
                # Set up empty package - just register it
                shim_blocks.append(
                    f"_setup_pkg_modules({pkg_name!r}, [], {name_mapping_str})"
                )
                continue

            # Sort module names for deterministic output
            module_names_for_pkg = sorted([name for name, _ in packages[pkg_name]])
            logger.trace(
                "Setting up package %s with modules: %s",
                pkg_name,
                module_names_for_pkg,
            )
            # Module names already have full paths (with package_name prefix),
            # but ensure they're correctly formatted for registration
            # If name equals pkg_name, it's the root module itself
            full_module_names = [
                (
                    name
                    if (name == pkg_name or name.startswith(f"{pkg_name}."))
                    else f"{pkg_name}.{name}"
                )
                for name in module_names_for_pkg
            ]
            module_names_str = ", ".join(repr(name) for name in full_module_names)
            logger.trace(
                "Calling _setup_pkg_modules for %s with modules: %s",
                pkg_name,
                full_module_names,
            )
            shim_blocks.append(
                f"_setup_pkg_modules({pkg_name!r}, [{module_names_str}], "
                f"{name_mapping_str})"
            )

        # Handle top-level modules for flat mode
        if module_mode == "flat" and top_level_modules:
            # Register top-level modules directly in sys.modules
            shim_blocks.extend(
                f"sys.modules[{module_name!r}] = globals()"
                for module_name in sorted(top_level_modules)
            )

        # Set up root module to have access to top-level packages
        # When transformed packages like mypkg.public exist, make public accessible
        # at root level for convenience (module.public works, not just
        # module.mypkg.public)
        if transformed_order_names is not None and package_name:
            logger.trace(
                "Setting up root module access for transformed packages: "
                "transformed_order_names=%s, package_name=%s, "
                "all_packages=%s",
                transformed_order_names,
                package_name,
                sorted(all_packages),
            )
            # Find top-level transformed packages (e.g., "public" from "mypkg.public")
            for transformed_name in transformed_order_names:
                if "." in transformed_name:
                    # Extract first part (e.g., "public" from "public.utils")
                    first_part = transformed_name.split(".", 1)[0]
                    # Check if this is a package (has submodules)
                    full_pkg_name = f"{package_name}.{first_part}"
                    logger.trace(
                        "Checking transformed package: first_part=%s, "
                        "full_pkg_name=%s, in all_packages=%s",
                        first_part,
                        full_pkg_name,
                        full_pkg_name in all_packages,
                    )
                    if full_pkg_name in all_packages:
                        logger.trace(
                            "Making transformed package %s accessible at root level",
                            first_part,
                        )
                        logger.trace(
                            "Adding shim blocks for root module access (current "
                            "shim_blocks length: %d)",
                            len(shim_blocks),
                        )
                        shim_blocks.append(
                            f"# Make {first_part} accessible at root level"
                        )
                        logger.trace(
                            "After adding comment (shim_blocks length: %d)",
                            len(shim_blocks),
                        )
                        shim_blocks.append(
                            f"_transformed_pkg = sys.modules.get({full_pkg_name!r})"
                        )
                        shim_blocks.append("if _transformed_pkg:")
                        # Set on root package if it exists
                        shim_blocks.append(
                            f"    _root_pkg = sys.modules.get({package_name!r})"
                        )
                        shim_blocks.append(
                            f"    if _root_pkg and not hasattr(_root_pkg, "
                            f"{first_part!r}):"
                        )
                        shim_blocks.append(
                            f"        setattr(_root_pkg, {first_part!r}, "
                            f"_transformed_pkg)"
                        )
                        # Set in globals() for script execution
                        shim_blocks.append(
                            f"    globals()[{first_part!r}] = _transformed_pkg"
                        )
                        # Also set on current module for importlib compatibility
                        # This ensures module.public works when imported via importlib
                        shim_blocks.append("    try:")
                        shim_blocks.append(
                            "        _current_mod = sys.modules.get(__name__)"
                        )
                        shim_blocks.append("        if _current_mod:")
                        shim_blocks.append(
                            f"            setattr(_current_mod, {first_part!r}, "
                            f"_transformed_pkg)"
                        )
                        shim_blocks.append("    except NameError:")
                        shim_blocks.append("        # __name__ not set yet, skip")
                        shim_blocks.append("        pass")

        shim_text = "\n".join(shim_blocks)

    # Auto-rename collision handling (raw mode only)
    # After applying module_mode transformations and user's module_actions,
    # check if multiple functions exist with the same name as the main function.
    # If yes, and in raw mode, auto-rename others to main_1, main_2, etc.
    stitch_mode = config.get("stitch_mode", "raw") if config else "raw"
    if (
        stitch_mode == "raw"
        and main_function_result is not None
        and module_sources is not None
    ):
        # Extract module names from module_sources keys (remove .py suffix)
        # This ensures we use the actual module names after any transformations
        module_names_from_sources = [
            key[:-3] for key in sorted(module_sources.keys()) if key.endswith(".py")
        ]

        # Detect collisions
        collisions = detect_collisions(
            main_function_result=main_function_result,
            module_sources=module_sources,
            module_names=module_names_from_sources,
        )

        # Generate auto-rename mappings (filters out main function automatically)
        renames = generate_auto_renames(
            collisions=collisions,
            main_function_result=main_function_result,
        )

        # If we have renames to apply
        if renames:
            main_function_name, _main_file_path, _main_module_path = (
                main_function_result
            )

            # Apply renames to module_sources and parts
            for module_name, new_function_name in sorted(renames.items()):
                module_key = f"{module_name}.py"
                if module_key in module_sources:
                    old_source = module_sources[module_key]
                    new_source = rename_function_in_source(
                        old_source, main_function_name, new_function_name
                    )
                    module_sources[module_key] = new_source

                    # Update corresponding part in parts list
                    # Find the part that contains this module
                    for i, part in enumerate(parts):
                        # Check if this part contains the module header
                        header_pattern = f"# === {module_name} ==="
                        if header_pattern in part:
                            # Replace the old function definition with new one
                            # Use regex to find and replace function definition
                            pattern = (
                                rf"^(\s*)(async\s+)?def\s+"
                                rf"{re.escape(main_function_name)}\s*\("
                            )
                            replacement = rf"\1\2def {new_function_name}("
                            parts[i] = re.sub(
                                pattern, replacement, part, flags=re.MULTILINE
                            )
                            break

                    # Log the rename
                    logger.info(
                        "Auto-renamed...........%s.%s() → %s()",
                        module_name,
                        main_function_name,
                        new_function_name,
                    )

    # Generate formatted header line
    # Use custom_header if provided, otherwise use formatted header
    if config and config.get("custom_header"):
        header_line = config.get("custom_header", "")
    else:
        header_line = _format_header_line(
            display_name=display_name,
            description=description,
            package_name=package_name,
        )

    # Build license/header section
    # Format license text (single line or multi-line block format)
    license_section = _format_license(license_text)
    repo_line = f"# Repo: {repo}\n" if repo else ""
    authors_line = f"# Authors: {authors}\n" if authors else ""
    build_tool_line = (
        f"# Build Tool: {PROGRAM_PACKAGE} — {version} — {commit} — {build_date}\n"
    )

    # Determine __main__ block to use
    main_block = ""
    main_mode = config.get("main_mode", "auto") if config else "auto"
    main_name = config.get("main_name") if config else None

    if main_mode == "auto":
        # If we have a selected __main__ block, use it
        if selected_main_block is not None:
            logger.info(
                "__main__ block...........selected from %s",
                selected_main_block.file_path,
            )
            # Use the selected block content
            main_block = f"\n{selected_main_block.content}\n"
        elif main_function_result is not None:
            # No existing block found, but we have a main function
            # Generate our own __main__ block
            function_name, _file_path, _module_path = main_function_result

            # Get the function node to detect parameters
            # We need to find it in module_sources
            has_params = True  # Default to True (safe)
            if module_sources is not None:
                # Find the module that contains the function
                module_key = f"{_module_path}.py"
                if module_key in module_sources:
                    source = module_sources[module_key]
                    # Parse and find the function
                    # Note: This is a minor redundant parse (only for one module,
                    # only when main_mode == "auto" and main_function_result is not
                    # None). The complexity of caching ASTs here is not worth it for
                    # this single-use case that only affects one module.
                    try:
                        tree = ast.parse(source)
                        for node in tree.body:
                            if (
                                isinstance(
                                    node, (ast.FunctionDef, ast.AsyncFunctionDef)
                                )
                                and node.name == function_name
                            ):
                                has_params = detect_function_parameters(node)
                                break
                    except (SyntaxError, ValueError):
                        pass

            # Generate block based on parameters
            if has_params:
                main_block = (
                    f"\nif __name__ == '__main__':\n"
                    f"    sys.exit({function_name}(sys.argv[1:]))\n"
                )
            else:
                main_block = (
                    f"\nif __name__ == '__main__':\n    sys.exit({function_name}())\n"
                )
            logger.info("__main__ block...........inserted")
        elif main_name is not None:
            # main_name was specified but not found - this is an error
            msg = (
                f"main_name '{main_name}' was specified but the function "
                "was not found in the stitched code"
            )
            raise ValueError(msg)
        # If no main function found and main_name not specified,
        # this is a non-main build (acceptable)
        # Note: We already logged this in stitch_modules, so we don't log again here
    # If main_mode == "none", don't add any __main__ block

    # Log commit value being written to script (for CI debugging)
    logger = getAppLogger()
    logger.info(
        "_build_final_script: Writing commit to script: %s (version=%s, build_date=%s)",
        commit,
        version,
        build_date,
    )
    logger.trace(
        "_build_final_script: Writing commit=%s, version=%s, build_date=%s",
        commit,
        version,
        build_date,
    )
    if is_ci():
        logger.info("Writing commit to script: %s", commit)
        logger.trace("_build_final_script: CI mode: commit=%s", commit)

    script_text = (
        "#!/usr/bin/env python3\n"
        '"""\n'
        + (
            config.get("file_docstring", "")
            if config and config.get("file_docstring")
            else (
                f"{header_line}\n"
                "This stitched version is auto-generated from modular sources.\n"
                f"Version: {version}\n"
                f"Commit: {commit}\n"
                f"Built: {build_date}\n" + (f"Authors: {authors}\n" if authors else "")
            )
        )
        + '"""\n'
        f"# {header_line}\n"
        f"{license_section}"
        f"# Version: {version}\n"
        f"# Commit: {commit}\n"
        + f"# Build Date: {build_date}\n"
        + f"{authors_line}"
        + f"{repo_line}"
        + f"{build_tool_line}"
        + "\n# noqa: E402\n"
        "\n"
        f"{future_block}\n"
        f"{import_block}\n"
        "\n"
        # constants come *after* imports to avoid breaking __future__ rules
        f"__version__ = {json.dumps(version)}\n"
        f"__commit__ = {json.dumps(commit)}\n"
        f"__build_date__ = {json.dumps(build_date)}\n"
        + (f"__AUTHORS__ = {json.dumps(authors)}\n" if authors else "")
        + f"__STITCHED__ = True\n"
        f"__STITCH_SOURCE__ = {json.dumps(PROGRAM_PACKAGE)}\n"
        f"__package__ = {json.dumps(package_name)}\n"
        "\n"
        "\n"
        + "\n".join(parts)
        + "\n"
        + (f"{shim_text}\n" if shim_text else "")
        + f"{main_block}"
    )

    # Return script text and detected packages (sorted for consistency)
    return script_text, sorted(detected_packages)


def stitch_modules(  # noqa: PLR0915, PLR0912, PLR0913, C901
    *,
    config: dict[str, object],
    file_paths: list[Path],
    package_root: Path,
    file_to_include: dict[Path, IncludeResolved],
    out_path: Path,
    license_text: str = "",
    version: str = "unknown",
    commit: str = "unknown",
    build_date: str = "unknown",
    post_processing: PostProcessingConfigResolved | None = None,
    is_serger_build: bool,
) -> None:
    """Orchestrate stitching of multiple Python modules into a single file.

    This is the main entry point for the stitching process. It coordinates all
    stitching utilities to produce a single, self-contained Python script from
    modular sources.

    The function:
    1. Validates configuration completeness
    2. Verifies all modules are listed and dependencies are consistent
    3. Collects and deduplicates external imports
    4. Assembles modules in correct order
    5. Detects name collisions
    6. Generates final script with metadata
    7. Verifies the output compiles
    8. Optionally runs post-processing tools (static checker, formatter, import sorter)

    Args:
        config: RootConfigResolved with stitching fields (package, order).
                Must include 'package' field for stitching. 'order' is optional
                and will be auto-discovered via topological sort if not provided.
        file_paths: List of file paths to stitch (in order)
        package_root: Common root of all included files
        file_to_include: Mapping of file path to its include (for dest access)
        out_path: Path where final stitched script should be written
        license_text: Optional license text for generated script
            (will be formatted automatically)
        version: Version string to embed in script metadata
        commit: Commit hash to embed in script metadata
        build_date: Build timestamp to embed in script metadata
        post_processing: Post-processing configuration (if None, skips post-processing)
        is_serger_build: Whether the output file is safe to overwrite.
                True if file doesn't exist or is a serger build, False otherwise.
                Pre-computed in run_build() to avoid recomputation.

    Raises:
        RuntimeError: If any validation or stitching step fails, or if attempting
                to overwrite a non-serger file (is_serger_build=False)
        AssertionError: If mtime advancing fails
    """
    logger = getAppLogger()

    # Bail out early if attempting to overwrite a non-serger file
    # (primary check is in run_build, this is defensive for direct calls)
    if out_path.exists() and not is_serger_build:
        xmsg = (
            f"Refusing to overwrite {out_path} because it does not appear "
            "to be a serger-generated build. If you want to overwrite this "
            "file, please delete it first or rename it."
        )
        raise RuntimeError(xmsg)

    # package is required for stitching
    validate_required_keys(config, {"package"}, "config")
    package_name_raw = config.get("package", "unknown")
    order_paths_raw = config.get("order", [])
    exclude_paths_raw = config.get("exclude_names", [])
    stitch_mode_raw = config.get("stitch_mode", DEFAULT_STITCH_MODE)
    module_mode_raw = config.get("module_mode", DEFAULT_MODULE_MODE)

    # Type guards for mypy/pyright
    if not isinstance(package_name_raw, str):
        msg = "Config 'package' must be a string"
        raise TypeError(msg)
    if not isinstance(order_paths_raw, list):
        msg = "Config 'order' must be a list"
        raise TypeError(msg)
    if not isinstance(exclude_paths_raw, list):
        msg = "Config 'exclude_names' must be a list"
        raise TypeError(msg)
    if not isinstance(stitch_mode_raw, str):
        msg = "Config 'stitch_mode' must be a string"
        raise TypeError(msg)
    if not isinstance(module_mode_raw, str):
        msg = "Config 'module_mode' must be a string"
        raise TypeError(msg)

    # Cast to known types after type guards
    package_name = package_name_raw
    # order and exclude_names are already resolved to Path objects in run_build()
    # Convert to Path objects explicitly

    order_paths: list[Path] = []
    for item in order_paths_raw:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, str):
            order_paths.append(Path(item))
        elif isinstance(item, Path):
            order_paths.append(item)

    exclude_paths: list[Path] = []
    for item in exclude_paths_raw:  # pyright: ignore[reportUnknownVariableType]
        if isinstance(item, str):
            exclude_paths.append(Path(item))
        elif isinstance(item, Path):
            exclude_paths.append(item)

    if not package_name or package_name == "unknown":
        msg = "Config must specify 'package' for stitching"
        raise RuntimeError(msg)

    if not order_paths:
        msg = (
            "No modules found for stitching. "
            "Either specify 'order' in config or ensure 'include' patterns match files."
        )
        raise RuntimeError(msg)

    # Validate stitch_mode
    valid_modes = literal_to_set(StitchMode)
    stitch_mode = stitch_mode_raw
    if stitch_mode not in valid_modes:
        msg = (
            f"Invalid stitch_mode: {stitch_mode!r}. "
            f"Must be one of: {', '.join(sorted(valid_modes))}"
        )
        raise ValueError(msg)

    # Validate module_mode
    valid_module_modes = literal_to_set(ModuleMode)
    module_mode = module_mode_raw
    if module_mode not in valid_module_modes:
        msg = (
            f"Invalid module_mode: {module_mode!r}. "
            f"Must be one of: {', '.join(sorted(valid_module_modes))}"
        )
        raise ValueError(msg)

    # Extract shim setting from config
    shim_raw = config.get("shim", DEFAULT_SHIM)
    if not isinstance(shim_raw, str):
        msg = "Config 'shim' must be a string"
        raise TypeError(msg)
    valid_shim_settings = literal_to_set(ShimSetting)
    shim = cast("ShimSetting", shim_raw)
    if shim not in valid_shim_settings:
        msg = (
            f"Invalid shim setting: {shim!r}. "
            f"Must be one of: {', '.join(sorted(valid_shim_settings))}"
        )
        raise ValueError(msg)

    # Extract module_actions from config (already normalized in RootConfigResolved)
    module_actions_raw = config.get("module_actions", [])
    if not isinstance(module_actions_raw, list):
        msg = "Config 'module_actions' must be a list"
        raise TypeError(msg)
    # module_actions is already list[ModuleActionFull] with all defaults applied
    module_actions = cast("list[ModuleActionFull]", module_actions_raw)

    # Check if non-raw modes are implemented
    if stitch_mode != "raw":
        msg = (
            f"stitch_mode '{stitch_mode}' is not yet implemented. "
            "Only 'raw' mode is currently supported."
        )
        raise NotImplementedError(msg)

    logger.debug("Starting stitch process for package: %s", package_name)

    # Extract source_bases from config
    # (needed for package detection and module derivation)
    # source_bases is validated and normalized to list[str] in config resolution
    # It's always present in resolved config, but .get() returns object | None
    source_bases_raw = config.get("source_bases")
    user_provided_source_bases_raw = config.get("_user_provided_source_bases")
    source_bases: list[str] | None = None
    if source_bases_raw is not None:  # pyright: ignore[reportUnnecessaryComparison]
        # Type narrowing: source_bases is list[str] after config resolution
        # Cast is safe because source_bases is validated in config resolution
        source_bases = [str(mb) for mb in cast("list[str]", source_bases_raw)]  # pyright: ignore[reportUnnecessaryCast]
    user_provided_source_bases: list[str] | None = None
    if user_provided_source_bases_raw is not None:  # pyright: ignore[reportUnnecessaryComparison]
        # Type narrowing: _user_provided_source_bases is list[str] after build
        user_provided_source_bases = [
            str(mb) for mb in cast("list[str]", user_provided_source_bases_raw)
        ]  # pyright: ignore[reportUnnecessaryCast]

    # --- Package Detection (once, at the start) ---
    # Use pre-detected packages from run_build (already excludes exclude_paths)
    detected_packages_raw = config.get("detected_packages")
    if detected_packages_raw is not None and isinstance(detected_packages_raw, set):
        # Type narrowing: cast to set[str] after isinstance check
        detected_packages = cast("set[str]", detected_packages_raw)
        logger.debug("Using pre-detected packages: %s", sorted(detected_packages))
    else:
        # Fallback: detect from order_paths (shouldn't happen in normal flow)
        logger.debug("Detecting packages from order_paths (fallback)...")
        detected_packages, _discovered_parent_dirs = detect_packages_from_files(
            order_paths,
            package_name,
            source_bases=source_bases,
        )

    # --- Validation Phase ---
    logger.debug("Validating module listing...")
    verify_all_modules_listed(file_paths, order_paths, exclude_paths)

    logger.debug("Checking module order consistency...")
    # Use pre-computed topological order if available (from auto-discovery)
    topo_paths_raw = config.get("topo_paths")
    topo_paths: list[Path] | None = None
    if topo_paths_raw is not None and isinstance(topo_paths_raw, list):
        topo_paths = []
        # Type narrowing: after isinstance check, cast to help type inference
        for item in cast("list[str | Path]", topo_paths_raw):
            if isinstance(item, str):
                topo_paths.append(Path(item))
            elif isinstance(item, Path):  # pyright: ignore[reportUnnecessaryIsInstance]
                topo_paths.append(item)
    suggest_order_mismatch(
        order_paths,
        package_root,
        package_name,
        file_to_include,
        detected_packages=detected_packages,
        topo_paths=topo_paths,
        source_bases=source_bases,
        user_provided_source_bases=user_provided_source_bases,
    )

    # --- Apply affects: "stitching" actions to filter files ---
    # Before collecting modules, apply actions that affect stitching
    # to determine which files should be excluded
    # IMPORTANT: We need to preserve original module names for shim generation
    # even when files are filtered from stitching
    original_order_names_for_shims: list[str] | None = None
    if module_actions:
        # Build module-to-file mapping from order_paths
        # Check if package_root is a package directory itself
        # (when all files are in a single package, package_root is that package)
        is_package_dir = (package_root / "__init__.py").exists()
        package_name_from_root: str | None = None
        if is_package_dir:
            package_name_from_root = package_root.name

        module_to_file_for_filtering: dict[str, Path] = {}
        for file_path in order_paths:
            include = file_to_include.get(file_path)
            module_name = derive_module_name(
                file_path,
                package_root,
                include,
                source_bases=source_bases,
                user_provided_source_bases=user_provided_source_bases,
                detected_packages=detected_packages,
            )

            # If package_root is a package directory, preserve package structure
            if is_package_dir and package_name_from_root:
                # Handle __init__.py special case: represents the package itself
                if file_path.name == "__init__.py" and file_path.parent == package_root:
                    # Use package name as the module name (represents the package)
                    module_name = package_name_from_root
                else:
                    # Prepend package name to preserve structure
                    # e.g., "core" -> "oldpkg.core"
                    module_name = f"{package_name_from_root}.{module_name}"

            module_to_file_for_filtering[module_name] = file_path

        # Preserve original module names for shim generation
        # (before filtering affects shim generation)
        original_order_names_for_shims = sorted(module_to_file_for_filtering.keys())

        # Separate actions by affects value
        (
            _shims_only_actions,
            stitching_only_actions,
            both_actions,
        ) = separate_actions_by_affects(module_actions)

        # Combine stitching-only and both actions
        stitching_actions = stitching_only_actions + both_actions

        if stitching_actions:
            # Extract deleted package/module names from stitching actions
            # Actions reference package names (e.g., "pkg1"), but we need to
            # check file paths to see if they belong to deleted packages
            deleted_sources: set[str] = set()
            for action in stitching_actions:
                action_type = action.get("action", "move")
                if action_type == "delete":
                    source = action["source"]  # pyright: ignore[reportTypedDictNotRequiredAccess]
                    deleted_sources.add(source)

            # Filter order_paths to exclude files belonging to deleted packages
            if deleted_sources:
                logger.debug(
                    "Filtering files: excluding modules deleted by "
                    "stitching actions: %s",
                    sorted(deleted_sources),
                )
                filtered_order_paths: list[Path] = []
                for file_path in order_paths:
                    # Check if file belongs to a deleted package
                    # package_root might be the package directory itself
                    # (e.g., tmp_path/pkg1), so we need to check if the
                    # package_root's name matches a deleted source, or if
                    # the file path contains the deleted source
                    should_exclude = False
                    excluded_by = None

                    # Check if package_root's name matches deleted_source
                    # (package_root is the package directory, e.g., tmp_path/pkg1)
                    package_root_name = package_root.name
                    for deleted_source in deleted_sources:
                        if package_root_name == deleted_source:
                            # All files under this package_root belong to deleted
                            # package
                            should_exclude = True
                            excluded_by = deleted_source
                            break

                    # Also check file path structure for nested packages
                    # (e.g., if package_root is tmp_path but file is
                    # tmp_path/pkg1/module.py)
                    if not should_exclude:
                        try:
                            file_relative = file_path.relative_to(package_root.parent)
                        except (ValueError, AttributeError):
                            # Fallback: check absolute path
                            file_str = str(file_path).replace("\\", "/")
                            for deleted_source in deleted_sources:
                                if f"/{deleted_source}/" in file_str:
                                    should_exclude = True
                                    excluded_by = deleted_source
                                    break
                        else:
                            file_str = str(file_relative).replace("\\", "/")
                            for deleted_source in deleted_sources:
                                # Check if file path starts with deleted_source/
                                if file_str.startswith(f"{deleted_source}/"):
                                    should_exclude = True
                                    excluded_by = deleted_source
                                    break
                                # Check if file path contains deleted_source as
                                # directory
                                if f"/{deleted_source}/" in file_str:
                                    should_exclude = True
                                    excluded_by = deleted_source
                                    break

                    if not should_exclude:
                        filtered_order_paths.append(file_path)
                    else:
                        logger.debug(
                            "Excluding file %s (deleted by stitching action: %s)",
                            file_path,
                            excluded_by,
                        )
                logger.debug(
                    "File filtering: %d files before, %d files after",
                    len(order_paths),
                    len(filtered_order_paths),
                )
                order_paths = filtered_order_paths

                # Also update derived_module_names if we're tracking it
                # (derived_module_names will be recalculated in _collect_modules)

    # --- Collection Phase ---
    logger.debug("Collecting module sources...")
    # Extract external_imports from config
    external_imports_raw = config.get(
        "external_imports", DEFAULT_EXTERNAL_IMPORTS[stitch_mode]
    )
    if not isinstance(external_imports_raw, str):
        msg = "Config 'external_imports' must be a string"
        raise TypeError(msg)
    external_imports = cast("ExternalImportMode", external_imports_raw)

    # Extract internal_imports from config
    internal_imports_raw = config.get(
        "internal_imports", DEFAULT_INTERNAL_IMPORTS[stitch_mode]
    )
    if not isinstance(internal_imports_raw, str):
        msg = "Config 'internal_imports' must be a string"
        raise TypeError(msg)
    internal_imports = cast("InternalImportMode", internal_imports_raw)

    # Extract comments_mode from config
    comments_mode_raw = config.get("comments_mode", DEFAULT_COMMENTS_MODE)
    if not isinstance(comments_mode_raw, str):
        msg = "Config 'comments_mode' must be a string"
        raise TypeError(msg)
    comments_mode = cast("CommentsMode", comments_mode_raw)

    # Extract docstring_mode from config
    docstring_mode_raw = config.get("docstring_mode", DEFAULT_DOCSTRING_MODE)
    # docstring_mode can be a string or dict
    if not isinstance(docstring_mode_raw, (str, dict)):
        msg = "Config 'docstring_mode' must be a string or dict"
        raise TypeError(msg)
    docstring_mode = cast("DocstringMode", docstring_mode_raw)

    # source_bases already extracted above (before package detection)
    module_sources, all_imports, parts, derived_module_names = _collect_modules(
        order_paths,
        package_root,
        package_name,
        file_to_include,
        detected_packages,
        external_imports,
        internal_imports,
        comments_mode,
        docstring_mode,
        source_bases=source_bases,
        user_provided_source_bases=user_provided_source_bases,
    )

    # --- Parse AST once for all modules ---
    # Extract symbols (functions, classes, assignments) from all modules
    # This avoids parsing AST multiple times
    logger.debug("Extracting symbols from modules...")
    module_symbols: dict[str, ModuleSymbols] = {}
    all_function_names: set[str] = set()
    # Sort for deterministic iteration order
    for mod_name, source in sorted(module_sources.items()):
        symbols = _extract_top_level_symbols(source)
        module_symbols[mod_name] = symbols
        all_function_names.update(symbols.functions)

    # --- Main Function Detection (before collision detection) ---
    # Find main function first, so we can ignore main function collisions
    # in raw mode when auto-rename will handle them
    logger.debug("Finding main function...")
    main_function_result = find_main_function(
        config=cast("RootConfigResolved", config),
        file_paths=order_paths,
        module_sources=module_sources,
        module_names=derived_module_names,
        package_root=package_root,
        file_to_include=file_to_include,
        detected_packages=detected_packages,
    )

    # Determine if we should ignore main function collisions
    # (auto-rename will handle them in raw mode)
    ignore_functions: set[str] = set()
    stitch_mode_raw = config.get("stitch_mode", "raw")
    if stitch_mode_raw == "raw" and main_function_result is not None:
        main_function_name, _main_file_path, _main_module_path = main_function_result
        # Check if there are multiple functions with this name
        module_names_from_sources = [
            key[:-3] for key in sorted(module_sources.keys()) if key.endswith(".py")
        ]
        collisions = detect_collisions(
            main_function_result=main_function_result,
            module_sources=module_sources,
            module_names=module_names_from_sources,
        )
        # If there are collisions, auto-rename will handle them
        if len(collisions) > 1:
            ignore_functions.add(main_function_name)

    # --- Collision Detection ---
    logger.debug("Detecting name collisions...")
    detect_name_collisions(module_symbols, ignore_functions=ignore_functions)

    # --- __main__ Block Detection ---
    # Detect all __main__ blocks from original file paths (before stripping)
    logger.debug("Detecting __main__ blocks...")
    all_main_blocks = detect_main_blocks(
        file_paths=order_paths,
        package_root=package_root,
        file_to_include=file_to_include,
        detected_packages=detected_packages,
    )

    # Log main function status
    if main_function_result is not None:
        function_name, _file_path, module_path = main_function_result
        logger.info("Main function...........%s.%s()", module_path, function_name)
    else:
        # Check if main_mode is "auto" to determine if this is a non-main build
        main_mode = config.get("main_mode", "auto")
        if main_mode == "auto":
            logger.info("Main function...........not found (non-main build)")

    # Select which __main__ block to keep
    selected_main_block = select_main_block(
        main_blocks=all_main_blocks,
        main_function_result=main_function_result,
        file_paths=order_paths,
        module_names=derived_module_names,
    )

    # Log discarded blocks
    if len(all_main_blocks) > 1:
        discarded = [block for block in all_main_blocks if block != selected_main_block]
        for block in discarded:
            logger.info(
                "__main__ block...........discarded from %s",
                block.file_path,
            )

    # --- Final Assembly ---
    # Extract display configuration
    display_name_raw = config.get("display_name", "")
    description_raw = config.get("description", "")
    authors_raw = config.get("authors", "")
    repo_raw = config.get("repo", "")

    # Type guards
    if not isinstance(display_name_raw, str):
        display_name_raw = ""
    if not isinstance(description_raw, str):
        description_raw = ""
    if not isinstance(authors_raw, str):
        authors_raw = ""
    if not isinstance(repo_raw, str):
        repo_raw = ""

    final_script, _detected_packages_returned = _build_final_script(
        package_name=package_name,
        all_imports=all_imports,
        parts=parts,
        order_names=derived_module_names,
        all_function_names=all_function_names,
        detected_packages=detected_packages,
        module_mode=module_mode,
        module_actions=module_actions,
        shim=shim,
        order_paths=order_paths,
        package_root=package_root,
        file_to_include=file_to_include,
        _original_order_names_for_shims=original_order_names_for_shims,
        license_text=license_text,
        version=version,
        commit=commit,
        build_date=build_date,
        display_name=display_name_raw,
        description=description_raw,
        authors=authors_raw,
        repo=repo_raw,
        config=cast("RootConfigResolved", config),
        selected_main_block=selected_main_block,
        main_function_result=main_function_result,
        module_sources=module_sources,
        source_bases=source_bases,
    )

    # --- Verification ---
    logger.debug("Verifying assembled script...")
    verify_no_broken_imports(
        final_script, sorted(detected_packages), internal_imports=internal_imports
    )

    # --- Compile in-memory before writing ---
    logger.debug("Compiling stitched code in-memory...")
    try:
        verify_compiles_string(final_script, filename=str(out_path))
    except SyntaxError as e:
        # Compilation failed - write error file and raise
        logger.exception("Stitched code does not compile")
        error_path = _write_error_file(out_path, final_script, e)
        lineno = e.lineno or "unknown"
        error_msg = e.msg or "unknown error"
        xmsg = (
            f"Stitched code has syntax errors at line {lineno}: {error_msg}. "
            f"Error file written to: {error_path}"
        )
        raise RuntimeError(xmsg) from e

    # --- Output (compilation succeeded) ---
    out_display = shorten_path_for_display(out_path)
    logger.debug("Writing output file: %s", out_display)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_script, encoding="utf-8")
    out_path.chmod(0o755)

    # Clean up any existing error files (build succeeded)
    _cleanup_error_files(out_path)

    # Advance mtime to ensure visibility across filesystems
    logger.debug("Advancing mtime...")
    force_mtime_advance(out_path)

    # Post-processing: tools, compilation checks, and verification
    # Note: post_stitch_processing may warn but won't raise on post-processing
    # failures - it will revert and continue
    post_stitch_processing(out_path, post_processing=post_processing)

    logger.info(
        "Successfully stitched %d modules into %s",
        len(parts),
        out_path,
    )
