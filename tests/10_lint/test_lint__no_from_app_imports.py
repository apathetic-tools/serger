# tests/0_independant/test_no_from_app_imports.py
"""Custom lint rule: Enforce `import <mod> as mod_<mod>` pattern in tests.

This test acts as a "poor person's linter" since we can't create custom ruff rules yet.
It enforces that ALL test files use `import serger.module as mod_module` format
instead of `from serger.module import ...` when importing from our project.

CRITICAL: This rule applies to ALL imports from our project, including private
functions (those starting with _). There are NO exceptions.

Why this matters:
- runtime_swap: Tests can run against either package or stitched
  stitched script. The `import ... as mod_*` pattern ensures the module object
  is available for runtime swapping.
- patch_everywhere: Predictive patching requires module objects to be available
  at the module level. Using `from ... import` breaks this because the imported
  function is no longer associated with its module object.

If you need to test private functions, import the module and access the function
via the module object: `mod_utils._private_function()` instead of importing
the function directly.
"""

import ast
from pathlib import Path

import serger.meta as mod_meta


# Package names that are disallowed from `from ... import` statements in tests
# All imports from these packages must use
# `import <package>.<module> as mod_<module>` format
DISALLOWED_PACKAGES = [
    mod_meta.PROGRAM_PACKAGE,
    "apathetic_utils",
    "apathetic_schema",
    "apathetic_logs",
]


def test_no_app_from_imports() -> None:
    """Enforce `import <mod> as mod_<mod>` pattern for all project imports in tests.

    This is a custom lint rule implemented as a pytest test because we can't
    create custom ruff rules yet. It ensures all test files use the module-level
    import pattern required for runtime_swap and patch_everywhere to work correctly.
    """
    tests_dir = Path(__file__).parents[1]  # tests/ directory (not project root)
    bad_files: list[Path] = []

    for path in tests_dir.rglob("test_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and any(node.module.startswith(pkg) for pkg in DISALLOWED_PACKAGES)
            ):
                # NO EXCEPTIONS: All imports from our project must use
                # module-level imports. This includes private functions -
                # use mod_module._private_function() instead
                bad_files.append(path)
                break  # only need one hit per file

    if bad_files:
        packages_str = ", ".join(DISALLOWED_PACKAGES)
        print(
            "\n❌ Disallowed `from <package>.<module> import ...`"
            " imports found in test files:",
        )
        print(f"   Disallowed packages: {packages_str}")
        for path in bad_files:
            print(f"  - {path}")
        print(
            "\nAll test files MUST use module-level imports:"
            f"\n  ❌ from {DISALLOWED_PACKAGES[0]}.module import function"
            f"\n  ✅ import {DISALLOWED_PACKAGES[0]}.module as mod_module"
            "\n"
            "\nThis pattern is required for:"
            "\n  - runtime_swap: Module objects needed for runtime mode switching"
            "\n  - patch_everywhere: Predictive patching requires module-level access"
            "\n"
            "\nFor private functions, access via module object:"
            "\n  ✅ mod_module._private_function()"
            "\n  ❌ from module import _private_function"
        )
        xmsg = (
            f"{len(bad_files)} test file(s) use disallowed"
            f" `from {packages_str}.*` imports."
            " All test imports from these packages must use"
            f" `import <package>.<module> as mod_<module>` format."
        )
        raise AssertionError(xmsg)
