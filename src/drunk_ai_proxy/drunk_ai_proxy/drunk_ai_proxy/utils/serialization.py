"""Serialization helpers."""

from __future__ import annotations

from typing import cast


def to_dict(value: object) -> dict[str, object]:
    """Convert a model-like object into a plain dict.

    Args:
        value: Object to convert.

    Returns:
        Dictionary representation of the object.
    """
    if isinstance(value, dict):
        return cast(dict[str, object], value)

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return cast(dict[str, object], dumped)

    obj_dict = getattr(value, "__dict__", None)
    if isinstance(obj_dict, dict):
        return cast(dict[str, object], obj_dict)

    return {}
