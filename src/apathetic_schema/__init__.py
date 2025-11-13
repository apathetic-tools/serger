"""Apathetic schema package."""

from apathetic_schema.schema import (
    SchemaErrorAggregator,
    ValidationSummary,
    check_schema_conformance,
    collect_msg,
    flush_schema_aggregators,
    warn_keys_once,
)


__all__ = [
    # schema
    "SchemaErrorAggregator",
    "ValidationSummary",
    "check_schema_conformance",
    "collect_msg",
    "flush_schema_aggregators",
    "warn_keys_once",
]
