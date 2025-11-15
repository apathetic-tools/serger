# tests/5_core/test_process_docstrings.py

"""Tests for docstring processing functionality."""

import serger.stitch as mod_stitch


def test_process_docstrings_keep() -> None:
    """Test that 'keep' mode preserves all docstrings."""
    code = '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    result = mod_stitch.process_docstrings(code, "keep")
    assert result == code


def test_process_docstrings_strip() -> None:
    """Test that 'strip' mode removes all docstrings."""
    code = '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_strip_module() -> None:
    """Test that dict mode can strip only module docstrings."""
    code = '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    expected = '''def func():
    """Function docstring."""
    return 42
'''
    result = mod_stitch.process_docstrings(code, {"module": "strip"})
    assert result == expected


def test_process_docstrings_strip_function() -> None:
    """Test that dict mode can strip only function docstrings."""
    code = '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    expected = '''"""Module docstring."""
def func():
    return 42
'''
    result = mod_stitch.process_docstrings(code, {"function": "strip"})
    assert result == expected


def test_process_docstrings_public() -> None:
    """Test that 'public' mode keeps only public docstrings."""
    code = '''"""Module docstring."""
def public_func():
    """Public function docstring."""
    return 42

def _private_func():
    """Private function docstring."""
    return 43
'''
    expected = '''"""Module docstring."""
def public_func():
    """Public function docstring."""
    return 42

def _private_func():
    return 43
'''
    result = mod_stitch.process_docstrings(code, "public")
    assert result == expected


def test_process_docstrings_class() -> None:
    """Test that class docstrings are handled correctly."""
    code = '''class MyClass:
    """Class docstring."""
    def method(self):
        """Method docstring."""
        return 42
'''
    expected = """class MyClass:
    def method(self):
        return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_method_vs_function() -> None:
    """Test that methods and functions are distinguished."""
    code = '''def top_level_func():
    """Top-level function docstring."""
    return 42

class MyClass:
    def method(self):
        """Method docstring."""
        return 43
'''
    # Strip only methods, keep functions
    expected = '''def top_level_func():
    """Top-level function docstring."""
    return 42

class MyClass:
    def method(self):
        return 43
'''
    result = mod_stitch.process_docstrings(code, {"method": "strip"})
    assert result == expected


def test_process_docstrings_triple_single_quotes() -> None:
    """Test that single-quote docstrings are handled."""
    code = '''"""Module docstring."""
def func():
    \'\'\'Function docstring with single quotes.\'\'\'
    return 42
'''
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_multiline() -> None:
    """Test that multiline docstrings are handled."""
    code = '''def func():
    """This is a
    multiline docstring
    that spans multiple lines."""
    return 42
'''
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_dict_defaults() -> None:
    """Test that omitted dict keys default to 'keep'."""
    code = '''"""Module docstring."""
def func():
    """Function docstring."""
    return 42
'''
    # Only specify module, function should default to keep
    result = mod_stitch.process_docstrings(code, {"module": "strip"})
    expected = '''def func():
    """Function docstring."""
    return 42
'''
    assert result == expected


def test_process_docstrings_no_docstrings() -> None:
    """Test that code without docstrings is unchanged."""
    code = """def func():
    return 42

class MyClass:
    def method(self):
        return 43
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == code


def test_process_docstrings_only_module() -> None:
    """Test code with only module docstring."""
    code = '''"""Module docstring."""
def func():
    return 42
'''
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_only_function() -> None:
    """Test code with only function docstring."""
    code = """def func():
    \"\"\"Function docstring.\"\"\"
    return 42
"""
    expected = """def func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_nested_classes() -> None:
    """Test nested classes with docstrings."""
    code = '''class Outer:
    """Outer class docstring."""
    class Inner:
        """Inner class docstring."""
        def method(self):
            """Method docstring."""
            return 42
'''
    expected = """class Outer:
    class Inner:
        def method(self):
            return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_property() -> None:
    """Test that property docstrings are treated as methods."""
    code = '''class MyClass:
    @property
    def prop(self):
        """Property docstring."""
        return 42
'''
    expected = """class MyClass:
    @property
    def prop(self):
        return 42
"""
    result = mod_stitch.process_docstrings(code, {"method": "strip"})
    assert result == expected


def test_process_docstrings_staticmethod() -> None:
    """Test that staticmethod docstrings are treated as methods."""
    code = '''class MyClass:
    @staticmethod
    def static_method():
        """Static method docstring."""
        return 42
'''
    expected = """class MyClass:
    @staticmethod
    def static_method():
        return 42
"""
    result = mod_stitch.process_docstrings(code, {"method": "strip"})
    assert result == expected


def test_process_docstrings_classmethod() -> None:
    """Test that classmethod docstrings are treated as methods."""
    code = '''class MyClass:
    @classmethod
    def class_method(cls):
        """Class method docstring."""
        return 42
'''
    expected = """class MyClass:
    @classmethod
    def class_method(cls):
        return 42
"""
    result = mod_stitch.process_docstrings(code, {"method": "strip"})
    assert result == expected


def test_process_docstrings_async_function() -> None:
    """Test that async function docstrings are handled."""
    code = '''async def async_func():
    """Async function docstring."""
    return 42
'''
    expected = """async def async_func():
    return 42
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_async_method() -> None:
    """Test that async method docstrings are treated as methods."""
    code = '''class MyClass:
    async def async_method(self):
        """Async method docstring."""
        return 42
'''
    expected = """class MyClass:
    async def async_method(self):
        return 42
"""
    result = mod_stitch.process_docstrings(code, {"method": "strip"})
    assert result == expected


def test_process_docstrings_public_class() -> None:
    """Test public mode with classes."""
    code = '''class PublicClass:
    """Public class docstring."""
    pass

class _PrivateClass:
    """Private class docstring."""
    pass
'''
    expected = '''class PublicClass:
    """Public class docstring."""
    pass

class _PrivateClass:
    pass
'''
    result = mod_stitch.process_docstrings(code, "public")
    assert result == expected


def test_process_docstrings_public_method() -> None:
    """Test public mode with methods."""
    code = '''class MyClass:
    def public_method(self):
        """Public method docstring."""
        return 42

    def _private_method(self):
        """Private method docstring."""
        return 43
'''
    expected = '''class MyClass:
    def public_method(self):
        """Public method docstring."""
        return 42

    def _private_method(self):
        return 43
'''
    result = mod_stitch.process_docstrings(code, "public")
    assert result == expected


def test_process_docstrings_dict_all_locations() -> None:
    """Test dict mode with all locations specified."""
    code = '''"""Module docstring."""
class MyClass:
    """Class docstring."""
    def method(self):
        """Method docstring."""
        return 42

def func():
    """Function docstring."""
    return 43
'''
    expected = """class MyClass:
    def method(self):
        return 42

def func():
    return 43
"""
    result = mod_stitch.process_docstrings(
        code,
        {
            "module": "strip",
            "class": "strip",
            "function": "strip",
            "method": "strip",
        },
    )
    assert result == expected


def test_process_docstrings_dict_public_specific() -> None:
    """Test dict mode with public mode for specific locations."""
    code = '''"""Module docstring."""
class PublicClass:
    """Public class docstring."""
    pass

class _PrivateClass:
    """Private class docstring."""
    pass

def public_func():
    """Public function docstring."""
    return 42

def _private_func():
    """Private function docstring."""
    return 43
'''
    expected = '''"""Module docstring."""
class PublicClass:
    """Public class docstring."""
    pass

class _PrivateClass:
    pass

def public_func():
    """Public function docstring."""
    return 42

def _private_func():
    return 43
'''
    result = mod_stitch.process_docstrings(
        code, {"class": "public", "function": "public"}
    )
    assert result == expected


def test_process_docstrings_complex_nested() -> None:
    """Test complex nested structure with various docstrings."""
    code = '''"""Module docstring."""
class Outer:
    """Outer class docstring."""
    def outer_method(self):
        """Outer method docstring."""
        class Inner:
            """Inner class docstring."""
            def inner_method(self):
                """Inner method docstring."""
                def nested_func():
                    """Nested function docstring."""
                    return 42
                return nested_func
        return Inner()
'''
    expected = """class Outer:
    def outer_method(self):
        class Inner:
            def inner_method(self):
                def nested_func():
                    return 42
                return nested_func
        return Inner()
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected


def test_process_docstrings_preserves_code_structure() -> None:
    """Test that code structure is preserved when removing docstrings."""
    code = '''"""Module docstring."""
import os

def func():
    """Function docstring."""
    x = 1
    y = 2
    return x + y
'''
    expected = """import os

def func():
    x = 1
    y = 2
    return x + y
"""
    result = mod_stitch.process_docstrings(code, "strip")
    assert result == expected
