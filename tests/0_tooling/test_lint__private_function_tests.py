# tests/0_tooling/test_lint__private_function_naming.py
"""Custom lint rules: Enforce naming and documentation for private function tests.

This test file acts as a "poor person's linter" since we can't create custom ruff
rules yet. It enforces two critical rules for test files that are PRIMARILY
testing private functions.

IMPORTANT: These rules apply ONLY to test files that are primarily a test suite
for a private function. If your test file calls a private function as a helper
but is primarily testing something else, use inline ignore comments instead.

Rule 1: Naming Convention
  Test files that are primarily testing a private function (e.g., the test suite
  is primarily asserting against `mod_x._private_function()`) and have top-level
  ignore comments must be named
  `test_priv__<function name without leading underscore>.py`.

Example:
    - Function: `_compile_glob_recursive`
    - Filename: `test_priv__compile_glob_recursive.py`

  This naming convention makes it immediately clear which private function a test
  file is primarily testing, improving code discoverability and maintainability.

Rule 2: Required Ignore Comments
  All test files named `test_priv__*.py` MUST include these ignore comments at the top:
    - `# we import '_' private for testing purposes only`
    - `# ruff: noqa: SLF001`
    - `# pyright: reportPrivateUsage=false`

  These comments:
    - Document that private access is intentional for testing
    - Suppress linter warnings about accessing private members
    - Suppress type checker warnings about private usage

  Without these comments, linters and type checkers will flag private function
  access as violations, making it impossible to test private implementation details.

When to use inline ignores instead:
  If your test file is NOT primarily testing a private function (e.g., it tests
  public APIs but happens to call a private helper function), you should use
  inline ignore comments on those specific calls instead of top-level ignores
  and the `test_priv__*.py` naming convention.

Example:
    ```python
    # test_some_feature.py (not test_priv__*.py)
    def test_feature():
        result = mod_utils.public_function()
        # Private helper called but not the primary thing under test
        helper_result = mod_utils._private_helper()  # noqa: SLF001
        assert result == expected
    ```

Why these rules matter:
  - Discoverability: Clear naming makes it easy to find test suites for specific
    private functions
  - Documentation: Required comments make it explicit that private access is
    intentional
  - Consistency: Enforces a uniform pattern across all private function test
    suites
  - Tool compatibility: Ensures linters and type checkers don't flag
    intentional private access
"""

import ast
from pathlib import Path


def _has_ignore_comments(content: str) -> bool:
    """Check if file has ignore comments for private function usage."""
    content_lower = content.lower()
    return (
        "# ruff: noqa: SLF001".lower() in content_lower
        and "# pyright: reportPrivateUsage=false".lower() in content_lower
    )


def _has_inline_ignore(line: str) -> bool:
    """Check if a line has an inline ignore comment."""
    line_lower = line.lower()
    return (
        "# noqa: SLF001".lower() in line_lower
        or "# pyright: ignore".lower() in line_lower
        or "# pyright: reportPrivateUsage=false".lower() in line_lower
    )


def _check_call_has_inline_ignore(node: ast.Call, lines: list[str]) -> bool:
    """Check if a call node has an inline ignore comment."""
    call_start_line = node.lineno - 1  # AST line numbers are 1-based
    call_end_line = node.end_lineno - 1 if node.end_lineno else call_start_line

    # Check the start line of the call
    if call_start_line < len(lines) and _has_inline_ignore(lines[call_start_line]):
        return True

    # Check the end line of the call (for multi-line calls)
    if (
        call_end_line < len(lines)
        and call_end_line != call_start_line
        and _has_inline_ignore(lines[call_end_line])
    ):
        return True

    # Check the line before (for comments before the call)
    return call_start_line > 0 and _has_inline_ignore(lines[call_start_line - 1])


def _find_private_function_calls(tree: ast.AST, lines: list[str]) -> set[str]:
    """Find all private function calls without inline ignores."""
    functions_without_inline_ignore: set[str] = set()

    class PrivateFunctionVisitor(ast.NodeVisitor):
        def __init__(self, file_lines: list[str]) -> None:
            self.file_lines = file_lines

        def visit_Call(self, node: ast.Call) -> None:
            # Check if the function being called is an Attribute with private name
            # e.g., mod_x._private_function()
            if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("_"):
                func_name = node.func.attr
                if not _check_call_has_inline_ignore(node, self.file_lines):
                    functions_without_inline_ignore.add(func_name)
            self.generic_visit(node)

    visitor = PrivateFunctionVisitor(lines)
    visitor.visit(tree)
    return functions_without_inline_ignore


def _check_filename_matches(
    test_file: Path, functions_without_inline_ignore: set[str]
) -> tuple[bool, str, str] | None:
    """Check if filename matches any private function without inline ignore.

    Returns:
        None if filename matches (case-insensitive),
        or (False, func_name, expected_name) if not.
    """
    actual_name = test_file.name.lower()  # Case-insensitive comparison
    for func_name in functions_without_inline_ignore:
        expected_name = f"test_priv__{func_name[1:]}.py"  # Remove leading underscore
        if actual_name == expected_name.lower():
            return None  # Matches

    # No match found
    first_func = sorted(functions_without_inline_ignore)[0]
    expected_name = f"test_priv__{first_func[1:]}.py"
    return (False, first_func, expected_name)


def _process_test_file(test_file: Path) -> tuple[Path, str, str] | None:
    """Process a single test file and return violation if any.

    Returns:
        None if no violation, or (file, func_name, expected_name) if violation.
    """
    # Read file content
    try:
        content = test_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None

    # Check if file has ignore comments
    if not _has_ignore_comments(content):
        return None

    # Parse the file to find calls to private functions
    try:
        tree = ast.parse(content, filename=str(test_file))
    except SyntaxError:
        return None

    # Find private function calls without inline ignores
    lines = content.splitlines()
    functions_without_inline_ignore = _find_private_function_calls(tree, lines)

    # Check filename if there are calls without inline ignores
    if functions_without_inline_ignore:
        result = _check_filename_matches(test_file, functions_without_inline_ignore)
        if result is not None:
            _, func_name, expected_name = result
            return (test_file, func_name, expected_name)

    return None


def test_private_function_naming_convention() -> None:
    """Enforce naming convention for test files primarily testing private functions.

    This is a custom lint rule implemented as a pytest test because we can't
    create custom ruff rules yet. It ensures test files that are PRIMARILY test
    suites for private functions follow a clear, discoverable naming pattern.

    IMPORTANT: This rule applies ONLY to test files that are primarily testing
    a private function. If your test file calls a private function as a helper
    but is primarily testing something else, use inline ignore comments instead.

    Rule: If a test file is primarily a test suite for a private function
    (e.g., `mod_x._private_function()`) and has top-level ignore comments, it
    MUST be named: `test_priv__<function name without leading underscore>.py`

    Examples:
      ✅ Test suite primarily for `_compile_glob_recursive` →
        `test_priv__compile_glob_recursive.py`
      ✅ Test suite primarily for `_strip_jsonc_comments` →
        `test_priv__strip_jsonc_comments.py`
      ❌ Test suite primarily for `_private_func` in file `test_utils.py` →
        Should be `test_priv__private_func.py`

    When to use inline ignores instead:
      If the private function is NOT the primary thing under test (e.g., it's
      called as a helper while testing public APIs), use inline ignore comments
      on those specific calls instead of top-level ignores and this naming
      convention.
    """
    tests_dir = Path(__file__).parent.parent
    violations: list[tuple[Path, str, str]] = []
    min_subdir_parts = 2

    # Find all test_*.py files in tests/*/ directories, excluding tests/utils
    for test_file in tests_dir.rglob("test_*.py"):
        # Skip files in tests/utils
        if "tests/utils" in str(test_file):
            continue

        # Skip files that are not in a subdirectory of tests (e.g., conftest.py)
        relative_path = test_file.relative_to(tests_dir)
        if len(relative_path.parts) < min_subdir_parts:
            continue

        # Process the file
        violation = _process_test_file(test_file)
        if violation is not None:
            violations.append(violation)

    if violations:
        print(
            "\n❌ Test files that are primarily test suites for private functions"
            " must follow naming convention:"
        )
        print(
            "\nRule: Test files that are PRIMARILY test suites for a private"
            " function and have top-level ignore comments must be named:"
            "\n  `test_priv__<function name without leading underscore>.py`"
        )
        print(
            "\nExamples:"
            "\n  ✅ Test suite primarily for `_compile_glob_recursive` →"
            "\n    `test_priv__compile_glob_recursive.py`"
            "\n  ✅ Test suite primarily for `_strip_jsonc_comments` →"
            "\n    `test_priv__strip_jsonc_comments.py`"
            "\n  ❌ Test suite primarily for `_private_func` in `test_utils.py` →"
            "\n    Should rename to `test_priv__private_func.py`"
        )
        print(
            "\nWhen to use inline ignores instead:"
            "\n  If the private function is NOT the primary thing under test"
            " (e.g., it's called as a helper while testing public APIs), use"
            " inline ignore comments on those specific calls instead:"
            "\n    mod_utils._private_helper()  # noqa: SLF001"
            "\n  This avoids needing top-level ignore comments and the"
            " `test_priv__*.py` naming convention."
        )
        print("\nViolations found:")
        for test_file, func_name, expected_name in violations:
            print(f"\n  - {test_file}")
            print(f"    Calls private function: `{func_name}`")
            print(f"    Expected filename: `{expected_name}`")
            print(f"    Actual filename: `{test_file.name}`")
            print(
                f"    Fix options:"
                f"\n      1. If this file is primarily a test suite for `{func_name}`:"
                f"\n         Rename to `{expected_name}`"
                f"\n      2. If `{func_name}` is just a helper (not primary under"
                f" test):"
                f"\n         Add inline ignore comments to `{func_name}` calls:"
                f"\n         mod_utils.{func_name}()  # noqa: SLF001"
                f"\n         And remove top-level ignore comments from this file."
            )
        xmsg = (
            f"{len(violations)} test file(s) violate private function naming"
            " convention. Test files that are primarily test suites for a"
            " private function must be named `test_priv__<function_name>.py`."
            " If the private function is not the primary thing under test, use"
            " inline ignore comments instead."
        )
        raise AssertionError(xmsg)


def test_priv_files_have_ignore_comments() -> None:
    """Enforce required ignore comments in test_priv__*.py files.

    This is a custom lint rule implemented as a pytest test because we can't
    create custom ruff rules yet. It ensures all test files that are primarily
    test suites for private functions have the necessary ignore comments to
    suppress linter and type checker warnings.

    IMPORTANT: This rule applies ONLY to test files named `test_priv__*.py`,
    which are test suites primarily for a private function. If your test file
    calls a private function as a helper but is primarily testing something
    else, use inline ignore comments instead.

    Rule: All test files named `test_priv__*.py` MUST include these comments
    at the top of the file (within the first 50 lines):

    1. `# we import '_' private for testing purposes only`
       - Documents that private access is intentional

    2. `# ruff: noqa: SLF001`
       - Suppresses Ruff's "private member accessed" warning

    3. `# pyright: reportPrivateUsage=false`
       - Suppresses Pyright's "private member accessed" warning

    These comments are required because:
    - Private functions are implementation details that linters flag by default
    - Testing private functions is intentional and should be documented
    - Without these comments, CI will fail due to linter/type checker errors

    When to use inline ignores instead:
      If your test file is NOT primarily testing a private function, use inline
      ignore comments on specific private function calls instead of top-level
      ignores and the `test_priv__*.py` naming convention.
    """
    tests_dir = Path(__file__).parent.parent
    violations: list[Path] = []
    min_subdir_parts = 2

    # Required ignore comments (all checks are case-insensitive)
    required_comments = [
        "# we import `_` private for testing purposes only",
        "# ruff: noqa: SLF001",
        "# pyright: reportPrivateUsage=false",
    ]

    # Find all test_priv__*.py files in tests/*/ directories, excluding tests/utils
    for test_file in tests_dir.rglob("test_priv__*.py"):
        # Skip files in tests/utils
        if "tests/utils" in str(test_file):
            continue

        # Skip files that are not in a subdirectory of tests
        relative_path = test_file.relative_to(tests_dir)
        if len(relative_path.parts) < min_subdir_parts:
            continue

        # Read file content
        try:
            content = test_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # Check if all required comments are present (case-insensitive)
        # Check first 50 lines (comments should be near the top)
        lines = content.splitlines()[:50]
        content_start_lower = "\n".join(lines).lower()

        # Check case-insensitively - convert both to lowercase for comparison
        missing_comments = [
            comment
            for comment in required_comments
            if comment.lower() not in content_start_lower
        ]

        if missing_comments:
            violations.append(test_file)

    if violations:
        print(
            "\n❌ Test files named `test_priv__*.py` must have required ignore"
            " comments:"
        )
        print(
            "\nAll test files that are primarily test suites for private functions"
            " MUST include these comments at the top of the file (within the first"
            " 50 lines):"
        )
        print()
        for i, comment in enumerate(required_comments, 1):
            print(f"  {i}. {comment}")
        print(
            "\nWhy these comments are required:"
            "\n  - Private functions are implementation details that linters"
            " flag by default"
            "\n  - Testing private functions is intentional and must be"
            " documented"
            "\n  - Without these comments, CI will fail due to linter/type"
            " checker errors"
        )
        print(
            "\nNote: These rules apply ONLY to test files that are primarily test"
            " suites for a private function. If your test file calls a private"
            " function as a helper but is primarily testing something else, use"
            " inline ignore comments instead:"
            "\n    mod_utils._private_helper()  # noqa: SLF001"
        )
        print("\nViolations found:")
        for test_file in violations:
            print(f"\n  - {test_file}")
            # Check which comments are missing (case-insensitive)
            try:
                content = test_file.read_text(encoding="utf-8")
                lines = content.splitlines()[:50]
                content_start_lower = "\n".join(lines).lower()
                missing = [
                    c for c in required_comments if c.lower() not in content_start_lower
                ]
                if missing:
                    print("    Missing comments:")
                    for comment in missing:
                        print(f"      - {comment}")
                    print(
                        "    Fix: Add the missing comments at the top of the file"
                        " (within the first 50 lines)"
                    )
                else:
                    print(
                        "    Note: Comments may be present but in wrong case or"
                        " location"
                    )
            except (UnicodeDecodeError, OSError):
                print("    (Could not read file to check specific missing comments)")
        xmsg = (
            f"{len(violations)} test_priv__*.py file(s) missing required ignore"
            " comments. All test files that test private functions must include"
            " these comments at the top:"
            " '# we import `_` private for testing purposes only',"
            " '# ruff: noqa: SLF001', and"
            " '# pyright: reportPrivateUsage=false'."
        )
        raise AssertionError(xmsg)
