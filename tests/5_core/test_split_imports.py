"""Tests for split_imports function."""

import serger.stitch as mod_stitch


def test_split_imports_external_only() -> None:
    """Should extract external imports."""
    code = """import sys
import json

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, "serger")
    expected_count = 2
    assert len(imports) == expected_count
    assert "import sys" in "".join(imports)
    assert "import json" in "".join(imports)
    assert "def foo():" in body


def test_split_imports_internal_removed() -> None:
    """Should remove internal imports from body."""
    code = """import sys
from serger.config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, "serger")
    assert "import sys" in "".join(imports)
    assert "from serger.config" not in "".join(imports)
    assert "from serger.config" not in body
    assert "def foo():" in body


def test_split_imports_relative_imports() -> None:
    """Should handle relative imports."""
    code = """from .config import Config

def foo():
    pass
"""
    imports, body = mod_stitch.split_imports(code, "serger")
    assert "from .config" not in "".join(imports)
    assert "from .config" not in body
    assert "def foo():" in body


def test_split_imports_invalid_syntax() -> None:
    """Should handle syntax errors gracefully."""
    code = "this is not valid python }"
    imports, body = mod_stitch.split_imports(code, "serger")
    assert imports == []
    assert body == code
