"""Run the conservative baseline on a split without reading reference answers.

Outputs and traces are private contest artifacts. The manifest binds an output
to its inputs and implementation; it is not an official evaluation receipt.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import hashlib
import json
import math
from pathlib import Path
import re
import time
from typing import Any

from .io import identifier, json_bytes, read_jsonl


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_submission(records: list[dict[str, Any]], expected_ids: list[str]) -> None:
    """Validate all public types and exact question membership, not correctness."""
    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("duplicate question identifiers")
    seen: set[str] = set()
    for record in records:
        record_id = identifier(record.get("id"), "submission id")
        if record_id in seen:
            raise ValueError("duplicate submission identifier")
        seen.add(record_id)
        kind = record.get("type")
        value = record.get("answer")
        if "reason" in record and not isinstance(record["reason"], str):
            raise ValueError("reason must be a string")
        if kind in ("abstain", "unanswerable"):
            if "answer" in record:
                raise ValueError("special types must omit answer")
        elif kind in ("number", "percent"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("numeric answer must be a finite JSON number")
        elif kind == "boolean":
            if not isinstance(value, bool):
                raise ValueError("boolean answer must be a JSON boolean")
        elif kind == "string":
            if not isinstance(value, str):
                raise ValueError("string answer must be a JSON string")
        elif kind == "date":
            from datetime import date

            if not isinstance(value, str):
                raise ValueError("date answer must be an ISO date string")
            try:
                if re.fullmatch(r"\d{4}-\d{2}", value):
                    parsed = date.fromisoformat(value + "-01")
                    if parsed.strftime("%Y-%m") != value:
                        raise ValueError("invalid month")
                else:
                    parsed = date.fromisoformat(value)
            except ValueError as exc:
                raise ValueError("date answer must be a valid ISO date") from exc
            if parsed.isoformat() != value and parsed.strftime("%Y-%m") != value:
                raise ValueError("date answer must use YYYY-MM-DD or YYYY-MM")
        elif kind == "list":
            if not isinstance(value, list):
                raise ValueError("list answer must be a JSON array")
        elif kind == "table":
            if not isinstance(value, dict) or set(value) != {"columns", "rows"}:
                raise ValueError("table answer must have columns and rows")
            columns, rows = value["columns"], value["rows"]
            if not isinstance(columns, list) or not all(isinstance(c, str) for c in columns):
                raise ValueError("table columns must be strings")
            if not isinstance(rows, list) or not all(isinstance(row, list) and len(row) == len(columns) for row in rows):
                raise ValueError("table rows must match column width")
        else:
            raise ValueError("unsupported submission type")
        # Also checks nested values for JSON compatibility and nonfinite numbers.
        json_bytes(record)
    if seen != set(expected_ids):
        raise ValueError("submission membership differs from questions")


def run_baseline(split: Path, output_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    from .baseline_data import load_business
    from .baseline_query import RulebookPolicy, solve_question

    split = split.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir.is_relative_to(split):
        raise ValueError("output directory must be outside the read-only input split")
    if output_dir.exists():
        raise ValueError("output directory already exists; refusing to overwrite a run")
    questions, question_raw = read_jsonl(split / "questions.jsonl")
    ids = [identifier(q.get("id"), "question id") for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question identifiers")
    data_root = (split / "data").resolve(strict=True)
    business_paths: dict[str, Path] = {}
    for question in questions:
        business_id = identifier(question.get("business_id"), "business id")
        identifier(question.get("question"), "question text")
        identifier(question.get("as_of_date"), "as_of_date")
        business_path = (data_root / business_id).resolve()
        if not business_path.is_relative_to(data_root) or business_path == data_root:
            raise ValueError("business path escapes split data directory")
        business_paths[business_id] = business_path
    rule_path = split / "rulebook.md"
    policy = RulebookPolicy.from_text(rule_path.read_text(encoding="utf-8-sig"))
    source_hashes = {
        path.name: file_sha256(path)
        for path in sorted(Path(__file__).parent.glob("*.py"))
    }
    inputs = {"questions.jsonl": hashlib.sha256(question_raw).hexdigest(), "rulebook.md": file_sha256(rule_path)}
    if (split / "calendar.csv").is_file():
        inputs["calendar.csv"] = file_sha256(split / "calendar.csv")
    for business_path in business_paths.values():
        for path in sorted(business_path.rglob("*")):
            if path.is_file():
                resolved = path.resolve()
                if not resolved.is_relative_to(data_root):
                    raise ValueError("business file escapes split data directory")
                inputs[path.relative_to(split).as_posix()] = file_sha256(path)
    output_dir.mkdir(parents=True, exist_ok=False)
    answers: dict[str, dict[str, Any]] = {}
    traces = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        grouped[question["business_id"]].append(question)
    # The laptop has 16 GB RAM. Retaining every raw workbook and canonical
    # business at once can exhaust it; questions are independent within groups.
    for group_number, (business_id, group) in enumerate(grouped.items(), 1):
        loading_started = time.perf_counter()
        business = None
        load_error = None
        try:
            business = load_business(business_paths[business_id])
        except Exception as exc:
            load_error = "business_load_" + type(exc).__name__
        for position, question in enumerate(group):
            tick = loading_started if position == 0 else time.perf_counter()
            error = load_error
            try:
                answer = ({"id": question["id"], "type": "abstain"}
                          if load_error else solve_question(question, business, policy))
                validate_submission([answer], [question["id"]])
            except Exception as exc:
                error = "question_" + type(exc).__name__
                answer = {"id": question["id"], "type": "abstain"}
            answers[question["id"]] = answer
            traces.append({"id": question["id"], "final_answer": answer,
                           "elapsed_seconds": time.perf_counter() - tick,
                           "error": error})
        del business
        gc.collect()
        # Only aggregate progress reaches stdout; records remain in private logs.
        print(json.dumps({"businesses_completed": group_number,
                          "businesses_total": len(grouped),
                          "questions_completed": len(answers)}), flush=True)
    records = [answers[record_id] for record_id in ids]
    validate_submission(records, ids)
    if source_hashes != {
        path.name: file_sha256(path)
        for path in sorted(Path(__file__).parent.glob("*.py"))
    }:
        raise ValueError("implementation changed during run; output was not finalized")
    output_path = output_dir / "submission.jsonl"
    output_path.write_bytes(b"".join(json_bytes(record) + b"\n" for record in records))
    log_dir = output_dir / "logs"
    log_dir.mkdir()
    (log_dir / "questions.jsonl").write_bytes(b"".join(json_bytes(trace) + b"\n" for trace in traces))
    manifest = {
        "implementation": "conservative-deterministic-baseline-v1",
        "inference_model_parameters": 0, "external_inference_api_calls": 0,
        "question_count": len(records), "business_count": len(business_paths),
        "types": dict(Counter(record["type"] for record in records)),
        "input_sha256": inputs, "source_sha256": source_hashes,
        "submission_sha256": file_sha256(output_path),
        "elapsed_seconds": time.perf_counter() - started,
        "notice": "Machine-generated predictions; no reference answers were loaded. No official score measured by this runner.",
    }
    (output_dir / "manifest.json").write_bytes(json_bytes(manifest) + b"\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_baseline(args.split, args.output_dir)
    print(json.dumps({key: result[key] for key in ("implementation", "question_count", "business_count", "types", "submission_sha256", "elapsed_seconds", "notice")}, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
