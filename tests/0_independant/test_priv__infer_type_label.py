# tests/_30_utils_tests/schema/private/test_infer_type_label.py
"""Smoke tests for serger.config_validate internal validator helpers."""

# we import `_` private for testing purposes only
# ruff: noqa: SLF001
# pyright: reportPrivateUsage=false

from typing import Any, TypedDict

from typing_extensions import NotRequired

import serger.utils_schema as mod_utils_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- Fixtures / Sample TypedDicts -------------------------------------------


class MiniBuild(TypedDict):
    include: list[str]
    out: str


def test_infer_type_label_basic_types() -> None:
    # --- execute and verify ---
    assert "str" in mod_utils_schema._infer_type_label(str)
    assert "list" in mod_utils_schema._infer_type_label(list[str])
    assert "MiniBuild" in mod_utils_schema._infer_type_label(MiniBuild)


def test_infer_type_label_handles_unusual_types() -> None:
    """Covers edge cases like custom classes and typing.Any."""

    # --- setup ---
    class Custom: ...

    # --- execute, verify ---
    assert "Custom" in mod_utils_schema._infer_type_label(Custom)
    assert "Any" in mod_utils_schema._infer_type_label(list[Any])
    # Should fall back gracefully on unknown types
    assert isinstance(mod_utils_schema._infer_type_label(Any), str)


class TestNotRequiredTypeLabels:
    """Test _infer_type_label with NotRequired types."""

    def test_notrequired_string_unwraps_to_str(self) -> None:
        """NotRequired[str] should unwrap to 'str' label."""
        nr = NotRequired[str]
        label = mod_utils_schema._infer_type_label(nr)

        # --- verify ---
        assert "str" in label
        assert "NotRequired" not in label

    def test_notrequired_int_unwraps_to_int(self) -> None:
        """NotRequired[int] should unwrap to 'int' label."""
        nr = NotRequired[int]
        label = mod_utils_schema._infer_type_label(nr)

        # --- verify ---
        assert "int" in label
        assert "NotRequired" not in label

    def test_notrequired_list_of_str(self) -> None:
        """NotRequired[list[str]] should unwrap to list[str]."""
        nr = NotRequired[list[str]]
        label = mod_utils_schema._infer_type_label(nr)

        # --- verify ---
        assert "list" in label
        assert "NotRequired" not in label

    def test_notrequired_typeddict(self) -> None:
        """NotRequired[TypedDict] should unwrap to TypedDict name."""
        nr = NotRequired[MiniBuild]
        label = mod_utils_schema._infer_type_label(nr)

        # --- verify ---
        assert "MiniBuild" in label
        assert "NotRequired" not in label

    def test_notrequired_union(self) -> None:
        """NotRequired[str | int] should unwrap properly."""
        nr = NotRequired[str | int]
        label = mod_utils_schema._infer_type_label(nr)

        # --- verify ---
        # Should be some representation of the union
        assert isinstance(label, str)
        assert "NotRequired" not in label
