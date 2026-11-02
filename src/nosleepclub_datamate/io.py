"""Small strict JSON helpers that never print source records in errors."""

import json
import math
from pathlib import Path
from typing import Any


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object member")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON constant")


def _finite_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("JSON number exceeds finite float range")
    return result


def identifier(value: Any, field: str) -> str:
    """Validate an exact identifier; preserve its spelling rather than normalize it."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def json_bytes(value: Any) -> bytes:
    """Canonical UTF-8 JSON used for deterministic local manifests and hashes."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], bytes]:
    """Return object records and original bytes; blank lines are invalid JSONL."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("input must be UTF-8 JSONL") from exc
    records = []
    # JSONL records are separated by physical LF, not Unicode line separators
    # that are legal characters inside a JSON string. Allow one final LF and
    # remove only the CR belonging to a CRLF record delimiter.
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for line_number, line in enumerate(lines, start=1):
        if line.endswith("\r"):
            line = line[:-1]
        if not line.strip():
            raise ValueError(f"line {line_number}: blank JSONL record")
        try:
            value = json.loads(line, object_pairs_hook=_unique_object,
                               parse_constant=_reject_constant, parse_float=_finite_float)
        except ValueError as exc:
            raise ValueError(f"line {line_number}: invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: record must be an object")
        records.append(value)
    return records, raw
