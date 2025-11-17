# tests/0_independant/test_safe_isinstance.py
"""Focused tests for serger.utils_core.safe_isinstance."""

from typing import Any, Literal, TypedDict, TypeVar

from typing_extensions import NotRequired

import apathetic_utils.types as amod_utils_types


def test_plain_types_work_normally() -> None:
    # --- execute, and verify ---
    assert amod_utils_types.safe_isinstance("x", str)
    assert not amod_utils_types.safe_isinstance(123, str)
    assert amod_utils_types.safe_isinstance(123, int)


def test_union_types() -> None:
    # --- setup ---
    u = str | int

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance("abc", u)
    assert amod_utils_types.safe_isinstance(42, u)
    assert not amod_utils_types.safe_isinstance(3.14, u)


def test_optional_types() -> None:
    # --- setup ---
    opt = int | None

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance(5, opt)
    assert amod_utils_types.safe_isinstance(None, opt)
    assert not amod_utils_types.safe_isinstance("nope", opt)


def test_any_type_always_true() -> None:
    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance("anything", Any)
    assert amod_utils_types.safe_isinstance(None, Any)
    assert amod_utils_types.safe_isinstance(42, Any)


def test_list_type_accepts_lists() -> None:
    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance([], list)
    assert not amod_utils_types.safe_isinstance({}, list)


def test_list_of_str_type_accepts_strings_inside() -> None:
    # --- setup ---
    list_str = list[str]

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance(["a", "b"], list_str)
    assert not amod_utils_types.safe_isinstance(["a", 2], list_str)


def test_typed_dict_like_accepts_dicts() -> None:
    # --- setup ---
    class DummyDict(TypedDict):
        foo: str
        bar: int

    # --- execute and verify ---
    # should treat dicts as valid, not crash
    assert amod_utils_types.safe_isinstance({"foo": "x", "bar": 1}, DummyDict)
    assert not amod_utils_types.safe_isinstance("not a dict", DummyDict)


def test_union_with_list_and_dict() -> None:
    # --- setup ---
    u = list[str] | dict[str, int]

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance(["a", "b"], u)
    assert amod_utils_types.safe_isinstance({"a": 1}, u)
    assert not amod_utils_types.safe_isinstance(42, u)


def test_does_not_raise_on_weird_types() -> None:
    """Exotic typing constructs should not raise exceptions."""

    # --- setup ---
    class A: ...

    T = TypeVar("T", bound=A)

    # --- execute ---
    # just ensure it returns a boolean, not crash
    result = amod_utils_types.safe_isinstance(A(), T)

    # --- verify ---
    assert isinstance(result, bool)


def test_nested_generics_work() -> None:
    # --- setup ---
    l2 = list[list[int]]

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance([[1, 2], [3, 4]], l2)
    assert not amod_utils_types.safe_isinstance([[1, "a"]], l2)


def test_literal_values_match() -> None:
    # --- setup ---
    lit = Literal["x", "y"]

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance("x", lit)
    assert not amod_utils_types.safe_isinstance("z", lit)


def test_tuple_generic_support() -> None:
    # --- setup ---
    tup = tuple[int, str]

    # --- execute and verify ---
    assert amod_utils_types.safe_isinstance((1, "a"), tup)
    assert not amod_utils_types.safe_isinstance(("a", 1), tup)


class TestNotRequired:
    """Tests for NotRequired type handling."""

    def test_notrequired_string_accepts_string(self) -> None:
        """NotRequired[str] should accept strings."""
        nr = NotRequired[str]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance("hello", nr)

    def test_notrequired_string_rejects_int(self) -> None:
        """NotRequired[str] should reject integers."""
        nr = NotRequired[str]

        # --- execute and verify ---
        assert not amod_utils_types.safe_isinstance(42, nr)

    def test_notrequired_int(self) -> None:
        """NotRequired[int] should validate int types."""
        nr = NotRequired[int]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance(123, nr)
        assert not amod_utils_types.safe_isinstance("not int", nr)

    def test_notrequired_list_of_str(self) -> None:
        """NotRequired[list[str]] should work with list generics."""
        nr = NotRequired[list[str]]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance(["a", "b"], nr)
        assert not amod_utils_types.safe_isinstance(["a", 2], nr)
        assert not amod_utils_types.safe_isinstance("not a list", nr)

    def test_notrequired_union(self) -> None:
        """NotRequired can wrap Union types."""
        nr = NotRequired[str | int]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance("hello", nr)
        assert amod_utils_types.safe_isinstance(42, nr)
        assert not amod_utils_types.safe_isinstance(3.14, nr)

    def test_notrequired_dict(self) -> None:
        """NotRequired can wrap dict types."""
        nr = NotRequired[dict[str, int]]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance({"a": 1, "b": 2}, nr)
        assert not amod_utils_types.safe_isinstance({"a": "not int"}, nr)
        assert not amod_utils_types.safe_isinstance("not a dict", nr)

    def test_notrequired_typeddict(self) -> None:
        """NotRequired can wrap TypedDict types."""

        class Config(TypedDict):
            name: str
            value: int

        nr = NotRequired[Config]

        # --- execute and verify ---
        assert amod_utils_types.safe_isinstance({"name": "test", "value": 1}, nr)
        assert amod_utils_types.safe_isinstance({}, nr)  # TypedDicts treat dicts
        assert not amod_utils_types.safe_isinstance("not a dict", nr)
