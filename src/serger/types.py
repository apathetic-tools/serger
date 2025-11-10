# src/serger/types.py

from __future__ import annotations

from typing import TypedDict

from typing_extensions import NotRequired


class IncludeEntry(TypedDict, total=False):
    src: str
    dest: NotRequired[str]


class MetaBuildConfig(TypedDict, total=False):
    include_base: str
    exclude_base: str
    out_base: str
    origin: str


class BuildConfig(TypedDict, total=False):
    include: list[str | IncludeEntry]
    exclude: list[str]
    out: str
    __meta__: MetaBuildConfig


class RootConfig(TypedDict, total=False):
    builds: list[BuildConfig]
