from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass, asdict
from typing import Any

JS_SAFE_INTEGER_MAX = 9007199254740991
DEFAULT_MAX_DEPTH = 100
_BIGINT_RE = re.compile(r"^-?\d+n$")
_ISO_DATE_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
)


def serialize_value(
    value: Any,
    *,
    safe_enabled: bool = False,
    max_depth: int = DEFAULT_MAX_DEPTH,
    _depth: int = 0,
    _seen: set[int] | None = None,
) -> Any:
    """Recursively encode values using RPC Toolkit Safe Mode conventions."""

    if _depth > max_depth:
        raise ValueError("Serialization depth limit exceeded")

    seen = _seen if _seen is not None else set()

    if isinstance(value, _dt.datetime):
        text = value.isoformat()
        return f"D:{text}" if safe_enabled else text

    if isinstance(value, _dt.date):
        text = _dt.datetime.combine(value, _dt.time()).isoformat()
        return f"D:{text}" if safe_enabled else text

    if isinstance(value, bool) or value is None:
        return value

    if isinstance(value, int):
        if abs(value) > JS_SAFE_INTEGER_MAX:
            return f"{value}n"
        return value

    if isinstance(value, str):
        return f"S:{value}" if safe_enabled else value

    if isinstance(value, Mapping):
        return _serialize_mapping(value, safe_enabled, max_depth, _depth, seen)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _serialize_sequence(value, safe_enabled, max_depth, _depth, seen)

    if is_dataclass(value) and not isinstance(value, type):
        return serialize_value(
            asdict(value),
            safe_enabled=safe_enabled,
            max_depth=max_depth,
            _depth=_depth + 1,
            _seen=seen,
        )

    return value


def deserialize_value(
    value: Any,
    *,
    safe_enabled: bool = False,
    max_depth: int = DEFAULT_MAX_DEPTH,
    _depth: int = 0,
    _seen: set[int] | None = None,
) -> Any:
    """Recursively decode values using RPC Toolkit Safe Mode conventions."""

    if _depth > max_depth:
        raise ValueError("Deserialization depth limit exceeded")

    seen = _seen if _seen is not None else set()

    if isinstance(value, str):
        if safe_enabled and value.startswith("S:"):
            return value[2:]

        if safe_enabled and value.startswith("D:"):
            return _parse_datetime(value[2:], fallback=value)

        if _BIGINT_RE.match(value):
            return int(value[:-1])

        if not safe_enabled and _ISO_DATE_RE.match(value):
            return _parse_datetime(value, fallback=value)

        return value

    if isinstance(value, Mapping):
        return _deserialize_mapping(value, safe_enabled, max_depth, _depth, seen)

    if isinstance(value, list):
        return _deserialize_sequence(value, safe_enabled, max_depth, _depth, seen)

    return value


def _serialize_mapping(
    value: Mapping[Any, Any],
    safe_enabled: bool,
    max_depth: int,
    depth: int,
    seen: set[int],
) -> dict[str, Any]:
    marker = id(value)
    if marker in seen:
        raise ValueError("Circular reference detected during serialization")

    seen.add(marker)
    try:
        return {
            str(key): serialize_value(
                item,
                safe_enabled=safe_enabled,
                max_depth=max_depth,
                _depth=depth + 1,
                _seen=seen,
            )
            for key, item in value.items()
        }
    finally:
        seen.remove(marker)


def _serialize_sequence(
    value: Sequence[Any],
    safe_enabled: bool,
    max_depth: int,
    depth: int,
    seen: set[int],
) -> list[Any]:
    marker = id(value)
    if marker in seen:
        raise ValueError("Circular reference detected during serialization")

    seen.add(marker)
    try:
        return [
            serialize_value(
                item,
                safe_enabled=safe_enabled,
                max_depth=max_depth,
                _depth=depth + 1,
                _seen=seen,
            )
            for item in value
        ]
    finally:
        seen.remove(marker)


def _deserialize_mapping(
    value: Mapping[Any, Any],
    safe_enabled: bool,
    max_depth: int,
    depth: int,
    seen: set[int],
) -> dict[str, Any]:
    marker = id(value)
    if marker in seen:
        raise ValueError("Circular reference detected during deserialization")

    seen.add(marker)
    try:
        return {
            str(key): deserialize_value(
                item,
                safe_enabled=safe_enabled,
                max_depth=max_depth,
                _depth=depth + 1,
                _seen=seen,
            )
            for key, item in value.items()
        }
    finally:
        seen.remove(marker)


def _deserialize_sequence(
    value: list[Any],
    safe_enabled: bool,
    max_depth: int,
    depth: int,
    seen: set[int],
) -> list[Any]:
    marker = id(value)
    if marker in seen:
        raise ValueError("Circular reference detected during deserialization")

    seen.add(marker)
    try:
        return [
            deserialize_value(
                item,
                safe_enabled=safe_enabled,
                max_depth=max_depth,
                _depth=depth + 1,
                _seen=seen,
            )
            for item in value
        ]
    finally:
        seen.remove(marker)


def _parse_datetime(value: str, *, fallback: str) -> _dt.datetime | str:
    try:
        normalized = value.replace("Z", "+00:00")
        return _dt.datetime.fromisoformat(normalized)
    except ValueError:
        return fallback

