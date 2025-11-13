# src/serger/utils/utils_types.py


from types import UnionType
from typing import (
    Any,
    Literal,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from typing_extensions import NotRequired


T = TypeVar("T")


def cast_hint(_typ: type[T], value: Any) -> T:
    """Explicit cast that documents intent but is purely for type hinting.

    A drop-in replacement for `typing.cast`, meant for places where:
      - You want to silence mypy's redundant-cast warnings.
      - You want to signal "this narrowing is intentional."
      - You need IDEs (like Pylance) to retain strong inference on a value.

    Does not handle Union, Optional, or nested generics: stick to cast(),
      because unions almost always represent a meaningful type narrowing.

    This function performs *no runtime checks*.
    """
    return cast("T", value)


def schema_from_typeddict(td: type[Any]) -> dict[str, Any]:
    """Extract field names and their annotated types from a TypedDict."""
    return get_type_hints(td, include_extras=True)


def _isinstance_generics(  # noqa: PLR0911
    value: Any,
    origin: Any,
    args: tuple[Any, ...],
) -> bool:
    # Outer container check
    if not isinstance(value, origin):
        return False

    # Recursively check elements for known homogeneous containers
    if not args:
        return True

    # list[str]
    if origin is list and isinstance(value, list):
        subtype = args[0]
        items = cast_hint(list[Any], value)
        return all(safe_isinstance(v, subtype) for v in items)

    # dict[str, int]
    if origin is dict and isinstance(value, dict):
        key_t, val_t = args if len(args) == 2 else (Any, Any)  # noqa: PLR2004
        dct = cast_hint(dict[Any, Any], value)
        return all(
            safe_isinstance(k, key_t) and safe_isinstance(v, val_t)
            for k, v in dct.items()
        )

    # Tuple[str, int] etc.
    if origin is tuple and isinstance(value, tuple):
        subtypes = args
        tup = cast_hint(tuple[Any, ...], value)
        if len(subtypes) == len(tup):
            return all(
                safe_isinstance(v, t) for v, t in zip(tup, subtypes, strict=False)
            )
        if len(subtypes) == 2 and subtypes[1] is Ellipsis:  # noqa: PLR2004
            return all(safe_isinstance(v, subtypes[0]) for v in tup)
        return False

    return True  # e.g., other typing origins like set[], Iterable[]


def safe_isinstance(value: Any, expected_type: Any) -> bool:  # noqa: PLR0911
    """Like isinstance(), but safe for TypedDicts and typing generics.

    Handles:
      - typing.Union, Optional, Any
      - typing.NotRequired
      - TypedDict subclasses
      - list[...] with inner types
      - Defensive fallback for exotic typing constructs
    """
    # --- Always allow Any ---
    if expected_type is Any:
        return True

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    # --- Handle NotRequired (extract inner type) ---
    if origin is NotRequired:
        # NotRequired[str] → validate as str
        if args:
            return safe_isinstance(value, args[0])
        return True

    # --- Handle Literals explicitly ---
    if origin is Literal:
        # Literal["x", "y"] → True if value equals any of the allowed literals
        return value in args

    # --- Handle Unions (includes Optional) ---
    if origin in {Union, UnionType}:
        # e.g. Union[str, int]
        return any(safe_isinstance(value, t) for t in args)

    # --- Handle special case: TypedDicts ---
    try:
        if (
            isinstance(expected_type, type)
            and hasattr(expected_type, "__annotations__")
            and hasattr(expected_type, "__total__")
        ):
            # Treat TypedDict-like as dict
            return isinstance(value, dict)
    except TypeError:
        # Not a class — skip
        pass

    # --- Handle generics like list[str], dict[str, int] ---
    if origin:
        return _isinstance_generics(value, origin, args)

    # --- Fallback for simple types ---
    try:
        return isinstance(value, expected_type)
    except TypeError:
        # Non-type or strange typing construct
        return False
