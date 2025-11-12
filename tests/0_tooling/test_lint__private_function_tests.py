# tests/0_tooling/test_lint__private_function_naming.py
"""Ensures test files that call private functions follow naming convention.

If a test file calls a private function (like `mod_x._private_function()`) and has
the ignore comments at the top, the file should be named
`test_priv__<function name without leading underscore>.py`.
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
    """Checks that test files calling private functions follow naming convention."""
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
            "\n❌ Test files that call private functions must follow naming convention:"
        )
        print(
            "   Files should be named "
            "`test_priv__<function name without leading underscore>.py`"
        )
        print()
        for test_file, func_name, expected_name in violations:
            print(f"  - {test_file}")
            print(f"    Calls private function: `{func_name}`")
            print(f"    Expected filename: `{expected_name}`")
            print(f"    Actual filename: `{test_file.name}`")
            print()
        xmsg = (
            f"{len(violations)} test file(s) violate "
            "private function naming convention."
        )
        raise AssertionError(xmsg)


def test_priv_files_have_ignore_comments() -> None:
    """Checks that test_priv__* files have required ignore comments."""
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
        print("\n❌ Test files named `test_priv__*.py` must have ignore comments:")
        print()
        for comment in required_comments:
            print(f"   {comment}")
        print()
        for test_file in violations:
            print(f"  - {test_file}")
            # Check which comments are missing (case-insensitive)
            try:
                content = test_file.read_text(encoding="utf-8")
                lines = content.splitlines()[:50]
                content_start_lower = "\n".join(lines).lower()
                missing = [
                    c for c in required_comments if c.lower() not in content_start_lower
                ]
                if missing:
                    print(f"    Missing: {', '.join(missing)}")
            except (UnicodeDecodeError, OSError):
                print("    (Could not read file)")
            print()
        xmsg = (
            f"{len(violations)} test_priv__*.py file(s) missing "
            "required ignore comments."
        )
        raise AssertionError(xmsg)
