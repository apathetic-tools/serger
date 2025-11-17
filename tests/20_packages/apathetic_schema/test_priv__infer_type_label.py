# tests/0_independant/test_priv__infer_type_label.py
"""Smoke tests for serger.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

from typing_extensions import NotRequired

import apathetic_schema.schema as amod_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


def test_infer_type_label_basic_types() -> None:
    # --- execute and verify ---
    assert "str" in amod_schema._infer_type_label(str)
    assert "list" in amod_schema._infer_type_label(list[str])
    assert "MiniBuild" in amod_schema._infer_type_label(MiniBuild)


def test_infer_type_label_handles_unusual_types() -> None:
    """Covers edge cases like custom classes and typing.Any."""

    # --- setup ---
    class Custom: ...

    # --- execute, verify ---
    assert "Custom" in amod_schema._infer_type_label(Custom)
    assert "Any" in amod_schema._infer_type_label(list[Any])
    # Should fall back gracefully on unknown types
    assert isinstance(amod_schema._infer_type_label(Any), str)


class TestNotRequiredTypeLabels:
    """Test _infer_type_label with NotRequired types."""

    def test_notrequired_string_unwraps_to_str(self) -> None:
        """NotRequired[str] should unwrap to 'str' label."""
        nr = NotRequired[str]
        label = amod_schema._infer_type_label(nr)

        # --- verify ---
        assert "str" in label
        assert "NotRequired" not in label

    def test_notrequired_int_unwraps_to_int(self) -> None:
        """NotRequired[int] should unwrap to 'int' label."""
        nr = NotRequired[int]
        label = amod_schema._infer_type_label(nr)

        # --- verify ---
        assert "int" in label
        assert "NotRequired" not in label

    def test_notrequired_list_of_str(self) -> None:
        """NotRequired[list[str]] should unwrap to list[str]."""
        nr = NotRequired[list[str]]
        label = amod_schema._infer_type_label(nr)

        # --- verify ---
        assert "list" in label
        assert "NotRequired" not in label

    def test_notrequired_typeddict(self) -> None:
        """NotRequired[TypedDict] should unwrap to TypedDict name."""
        nr = NotRequired[MiniBuild]
        label = amod_schema._infer_type_label(nr)

        # --- verify ---
        assert "MiniBuild" in label
        assert "NotRequired" not in label

    def test_notrequired_union(self) -> None:
        """NotRequired[str | int] should unwrap properly."""
        nr = NotRequired[str | int]
        label = amod_schema._infer_type_label(nr)

        # --- verify ---
        # Should be some representation of the union
        assert isinstance(label, str)
        assert "NotRequired" not in label
