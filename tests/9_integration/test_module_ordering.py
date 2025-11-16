# tests/9_integration/test_module_ordering.py
"""Integration tests for serger module ordering in stitched files.

Tests that modules are ordered correctly in the stitched output, particularly
when __init__.py files import from other modules in the same package. These
modules should be ordered AFTER the modules they import from to prevent runtime
errors.
"""

import sys
from pathlib import Path

import pytest

import serger.meta as mod_meta
from tests.utils import run_with_output


@pytest.fixture
def test_package_structure(tmp_path: Path) -> Path:
    """Create a test package structure that reproduces the ordering issue.

    Structure:
        test_pkg/
            __init__.py  (imports from .module_b)
            module_a.py  (no dependencies)
            module_b.py  (defines ClassB that __init__.py needs)
    """
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir()

    # module_b.py - defines a class that __init__.py will import
    (pkg_dir / "module_b.py").write_text(
        """# module_b.py
\"\"\"Module B that defines ClassB.\"\"\"

class ClassB:
    \"\"\"A class that __init__.py imports.\"\"\"

    VALUE = "from_module_b"

    @staticmethod
    def get_value() -> str:
        return ClassB.VALUE
"""
    )

    # module_a.py - independent module (no dependencies)
    (pkg_dir / "module_a.py").write_text(
        """# module_a.py
\"\"\"Module A with no dependencies.\"\"\"

CONSTANT_A = "module_a_value"
"""
    )

    # __init__.py - imports from module_b and tries to use it immediately
    (pkg_dir / "__init__.py").write_text(
        """# __init__.py
\"\"\"Package init that imports from module_b.\"\"\"

# This import should cause module_b to be ordered BEFORE __init__.py
from .module_b import ClassB

# Try to use ClassB immediately (will fail if module_b hasn't been defined yet)
if globals().get("__STANDALONE__"):
    # In stitched mode, ClassB should already be in globals
    # If __init__.py runs before module_b, this will raise KeyError
    _class_b = globals()["ClassB"]
else:
    _class_b = ClassB

# Export ClassB and its value
ExportedClass = _class_b
EXPORTED_VALUE = _class_b.get_value()
"""
    )

    return pkg_dir


@pytest.fixture
def serger_config(tmp_path: Path, test_package_structure: Path) -> Path:
    """Create a serger config file for the test package."""
    config_file = tmp_path / ".serger.jsonc"
    pkg_name = test_package_structure.name
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(exist_ok=True)

    config_content = f"""{{
  "package": "{pkg_name}",
      "include": [
        "{test_package_structure}/**/*.py"
      ],
      "exclude": [
        "__pycache__/**",
        "*.pyc"
      ],
      "out": "{dist_dir / f"{pkg_name}.py"}"
}}
"""
    config_file.write_text(config_content)
    return config_file


def test_init_ordering_stitched_file_compiles(
    tmp_path: Path,
    test_package_structure: Path,
    serger_config: Path,  # noqa: ARG001
) -> None:
    """Test that stitched file compiles without syntax errors."""
    # Run serger
    result = run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        cwd=tmp_path,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Serger failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    # Find the output file
    pkg_name = test_package_structure.name
    output_file = tmp_path / "dist" / f"{pkg_name}.py"

    assert output_file.exists(), f"Output file not created: {output_file}"

    # Try to compile the stitched file
    result = run_with_output(
        [sys.executable, "-m", "py_compile", str(output_file)],
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(f"Stitched file does not compile:\nSTDERR:\n{result.stderr}")


def test_init_ordering_module_order_correct(
    tmp_path: Path,
    test_package_structure: Path,
    serger_config: Path,  # noqa: ARG001
) -> None:
    """Test that module_b appears before __init__.py in stitched output."""
    # Run serger
    result = run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, f"Serger failed: {result.stderr}"

    # Read the stitched file
    pkg_name = test_package_structure.name
    output_file = tmp_path / "dist" / f"{pkg_name}.py"
    content = output_file.read_text()

    # Find line numbers for module markers
    lines = content.split("\n")
    module_b_line = None
    init_line = None

    for i, line in enumerate(lines, 1):
        if "# === module_b ===" in line or "# module_b.py" in line:
            module_b_line = i
        if "# === __init__ ===" in line or "# __init__.py" in line:
            init_line = i

    assert module_b_line is not None, "module_b.py marker not found in stitched file"
    assert init_line is not None, "__init__.py marker not found in stitched file"

    # module_b should come before __init__
    assert module_b_line < init_line, (
        f"module_b.py (line {module_b_line}) should come before "
        f"__init__.py (line {init_line}) in stitched output"
    )


def test_init_ordering_runtime_works(
    tmp_path: Path,
    test_package_structure: Path,
    serger_config: Path,  # noqa: ARG001
) -> None:
    """Test that the stitched file can be imported and used without errors."""
    # Run serger
    result = run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, f"Serger failed: {result.stderr}"

    # Try to import and use the stitched module
    pkg_name = test_package_structure.name
    output_file = tmp_path / "dist" / f"{pkg_name}.py"

    # Create a test script that imports the stitched module
    test_script = tmp_path / "test_import.py"
    test_script.write_text(
        f"""import sys
sys.path.insert(0, str({str(output_file.parent)!r}))

import {pkg_name}

# Test that ExportedClass is available
assert hasattr({pkg_name}, "ExportedClass"), "ExportedClass not found"
assert hasattr({pkg_name}, "EXPORTED_VALUE"), "EXPORTED_VALUE not found"

# Test that it works
value = {pkg_name}.EXPORTED_VALUE
assert value == "from_module_b", f"Expected 'from_module_b', got {{value}}"

print("✓ Import and usage successful")
"""
    )

    # Run the test script
    result = run_with_output(
        [sys.executable, str(test_script)],
        cwd=tmp_path,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Runtime test failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def test_init_ordering_with_standalone_marker(
    tmp_path: Path,
    test_package_structure: Path,
    serger_config: Path,  # noqa: ARG001
) -> None:
    """Test that __init__.py can detect stitched mode and handle it correctly.

    This test verifies that when __init__.py checks for __STANDALONE__,
    it can access globals()["ClassB"] without KeyError.
    """
    # Run serger
    result = run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, f"Serger failed: {result.stderr}"

    # Read the stitched file to verify __STANDALONE__ is set
    pkg_name = test_package_structure.name
    output_file = tmp_path / "dist" / f"{pkg_name}.py"
    content = output_file.read_text()

    assert "__STANDALONE__" in content, (
        "__STANDALONE__ marker should be set in stitched file"
    )

    # Verify the conditional logic in __init__.py is preserved
    assert (
        'if globals().get("__STANDALONE__")' in content
        or "if globals().get('__STANDALONE__')" in content
    ), "Conditional check for __STANDALONE__ should be in stitched file"

    # Try to import - this will fail if ClassB isn't in globals when __init__ runs
    test_script = tmp_path / "test_standalone.py"
    test_script.write_text(
        f"""import sys
sys.path.insert(0, str({str(output_file.parent)!r}))

try:
    import {pkg_name}
    print("✓ Import successful")
    print(f"EXPORTED_VALUE = {{getattr({pkg_name}, 'EXPORTED_VALUE', 'NOT_FOUND')}}")
except KeyError as e:
    import traceback
    print(f"✗ KeyError during import: {{e}}")
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    import traceback
    print(f"✗ Unexpected error: {{e}}")
    traceback.print_exc()
    sys.exit(1)
"""
    )

    result = run_with_output(
        [sys.executable, str(test_script)],
        cwd=tmp_path,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Standalone mode test failed:\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def test_init_ordering_apathetic_logging_scenario(
    tmp_path: Path,
) -> None:
    """Test that reproduces the exact apathetic_logging scenario.

    This test matches the actual structure where:
    - namespace.py defines a class `apathetic_logging`
    - __init__.py imports from .namespace and tries to use it in stitched mode
    - The import uses relative import: `from .namespace import apathetic_logging`
    """
    pkg_dir = tmp_path / "test_pkg"
    pkg_dir.mkdir()

    # Create namespace.py (like apathetic_logging/namespace.py)
    (pkg_dir / "namespace.py").write_text(
        """# namespace.py
\"\"\"Namespace module.\"\"\"

class apathetic_logging:  # noqa: N801
    \"\"\"Namespace class.\"\"\"

    VALUE = "from_namespace"

    @staticmethod
    def get_value() -> str:
        return apathetic_logging.VALUE
"""
    )

    # Create __init__.py (like apathetic_logging/__init__.py)
    (pkg_dir / "__init__.py").write_text(
        """# __init__.py
\"\"\"Package init.\"\"\"

# This relative import should cause namespace.py to be ordered BEFORE __init__.py
from .namespace import apathetic_logging as _apathetic_logging_ns

# In stitched mode, try to access from globals (will fail if namespace.py hasn't run)
if globals().get("__STANDALONE__"):
    _apathetic_logging_ns = globals()["apathetic_logging"]
else:
    pass  # Import already happened above

# Export
ExportedClass = _apathetic_logging_ns
EXPORTED_VALUE = _apathetic_logging_ns.get_value()
"""
    )

    # Create serger config
    config_file = tmp_path / ".serger.jsonc"
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(exist_ok=True)
    config_content = f"""{{
  "package": "test_pkg",
      "include": [
        "{pkg_dir}/**/*.py"
      ],
      "exclude": [
        "__pycache__/**",
        "*.pyc"
      ],
      "out": "{dist_dir / "test_pkg.py"}"
}}
"""
    config_file.write_text(config_content)

    # Run serger
    result = run_with_output(
        [sys.executable, "-m", mod_meta.PROGRAM_PACKAGE],
        cwd=tmp_path,
        check=False,
    )

    assert result.returncode == 0, (
        f"Serger failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # Check ordering
    output_file = tmp_path / "dist" / "test_pkg.py"
    content = output_file.read_text()
    lines = content.split("\n")

    namespace_line = None
    init_line = None

    for i, line in enumerate(lines, 1):
        if "# === namespace ===" in line or "# namespace.py" in line:
            namespace_line = i
        if "# === __init__ ===" in line or "# __init__.py" in line:
            init_line = i

    assert namespace_line is not None, "namespace.py marker not found"
    assert init_line is not None, "__init__.py marker not found"

    # This is the key assertion - namespace should come before __init__
    # If this fails, it reproduces the bug
    assert namespace_line < init_line, (
        f"BUG REPRODUCED: namespace.py (line {namespace_line}) comes AFTER "
        f"__init__.py (line {init_line}). This causes KeyError when __init__.py "
        f"tries to access globals()['apathetic_logging']"
    )

    # Also verify it can be imported without KeyError
    test_script = tmp_path / "test_import.py"
    test_script.write_text(
        f"""import sys
sys.path.insert(0, str({str(output_file.parent)!r}))

try:
    import test_pkg
    print(f"✓ Import successful, EXPORTED_VALUE = {{test_pkg.EXPORTED_VALUE}}")
except KeyError as e:
    print(f"✗ KeyError: {{e}}")
    print("This indicates namespace.py was not executed before __init__.py")
    sys.exit(1)
"""
    )

    result = run_with_output(
        [sys.executable, str(test_script)],
        cwd=tmp_path,
        check=False,
    )

    if result.returncode != 0:
        pytest.fail(
            f"Import test failed (likely due to ordering issue):\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
