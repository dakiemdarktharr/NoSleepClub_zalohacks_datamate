"""Local typed-answer proxy for training diagnostics, never the official evaluator.

Only allowed training questions/labels are consumed by the runner. References
and their aliases are used after inference, never provided to the solver. Table
duplicate handling, numeric floating tolerance and malformed-record behavior must
still be checked against the organizer's actual evaluator.
"""

import argparse
from collections import defaultdict
from datetime import date
from decimal import Decimal
import gc
import hashlib
import importlib
import json
import math
from pathlib import Path
import re
import sys
import time
import unicodedata
from typing import Any, Iterable, Mapping

from .io import identifier, json_bytes, read_jsonl
from .metrics import summarize_verdicts
from .splits import split_training_questions
from .baseline_run import _input_hashes, file_sha256, validate_submission

REFERENCE_TYPES = {"number", "percent", "string", "date", "boolean", "list", "table", "unanswerable"}
PROXY_NOTICE = (
    "LOCAL PROXY, NOT THE OFFICIAL EVALUATOR. Alias/format matching is original "
    "code for training diagnostics; table duplicate handling, numeric floating "
    "tolerance and malformed records require official-evaluator confirmation."
)


def normalize_string(value: str) -> str:
    value = unicodedata.normalize("NFC", value).lower()
    value = "".join(character if character.isalpha() or character.isdigit() or character.isspace()
                    else " " for character in value)
    return " ".join(value.split())


def _number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and (
        not isinstance(value, float) or math.isfinite(value)
    )


def _number_equal(predicted: Any, reference: Any) -> bool:
    if not _number(predicted) or not _number(reference):
        return False
    left, right = Decimal(str(predicted)), Decimal(str(reference))
    if left == right:
        return True
    if isinstance(predicted, int) and isinstance(reference, int):
        return False
    try:
        # Ignore representational noise, never a broad relative VND tolerance.
        tolerance = min(4 * max(math.ulp(float(predicted)), math.ulp(float(reference))), 1e-7)
        return abs(left - right) <= Decimal(str(tolerance))
    except OverflowError:
        return False


def _percent_equal(predicted: Any, reference: Any) -> bool:
    # The solver must emit the correctly rounded number. The proxy may ignore
    # representation noise, but must not repair a semantically different output.
    return _number_equal(predicted, reference)


def _string_equal(predicted: Any, reference: Any, aliases: Any = None) -> bool:
    if not isinstance(predicted, str) or not isinstance(reference, str):
        return False
    accepted = [reference]
    if isinstance(aliases, list):
        accepted.extend(alias for alias in aliases if isinstance(alias, str))
    normalized = normalize_string(predicted)
    return any(normalized == normalize_string(candidate) for candidate in accepted)


def _scalar_equal(predicted: Any, reference: Any, aliases: Any = None) -> bool:
    if isinstance(reference, str):
        return _string_equal(predicted, reference, aliases)
    return _number_equal(predicted, reference)


def _date_valid(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", value):
        return False
    try:
        date.fromisoformat(value if len(value) == 10 else value + "-01")
        return True
    except ValueError:
        return False


def _table_equal(predicted: Any, reference: Any, aliases: Any) -> bool:
    if not isinstance(predicted, dict) or not isinstance(reference, dict):
        return False
    columns, rows = predicted.get("columns"), predicted.get("rows")
    gold_columns, gold_rows = reference.get("columns"), reference.get("rows")
    if not all(isinstance(value, list) for value in (columns, rows, gold_columns, gold_rows)):
        return False
    if len(columns) != len(gold_columns) or len(rows) != len(gold_rows):
        return False
    if not all(isinstance(column, str) for column in columns + gold_columns):
        return False
    if not all(isinstance(row, list) and len(row) == len(columns) for row in rows):
        return False
    if not all(isinstance(row, list) and len(row) == len(gold_columns) for row in gold_rows):
        return False
    normalized = [normalize_string(column) for column in columns]
    gold_normalized = [normalize_string(column) for column in gold_columns]
    if len(set(normalized)) != len(normalized) or len(set(gold_normalized)) != len(gold_normalized):
        return False
    if set(normalized) == set(gold_normalized):
        order = [normalized.index(column) for column in gold_normalized]
    else:
        order = list(range(len(columns)))
    ordered_rows = [[row[position] for position in order] for row in rows]

    def matches(row, gold_row, gold_index):
        entity_aliases = aliases[gold_index] if isinstance(aliases, list) and gold_index < len(aliases) else []
        return all(_scalar_equal(cell, gold_cell, entity_aliases if index == 0 else [])
                   for index, (cell, gold_cell) in enumerate(zip(row, gold_row)))

    # Bipartite matching avoids greedy errors when entity aliases overlap.
    assigned: dict[int, int] = {}

    def place(gold_index, visited):
        for index, row in enumerate(ordered_rows):
            if index in visited or not matches(row, gold_rows[gold_index], gold_index):
                continue
            visited.add(index)
            if index not in assigned or place(assigned[index], visited):
                assigned[index] = gold_index
                return True
        return False

    return all(place(gold_index, set()) for gold_index in range(len(gold_rows)))


def classify_prediction(prediction: Mapping[str, Any] | None,
                        reference: Mapping[str, Any]) -> str:
    """Return a proxy correct/wrong/abstain verdict, using gold aliases only here."""
    reference_type = reference.get("type")
    if not isinstance(reference_type, str) or reference_type not in REFERENCE_TYPES:
        raise ValueError("invalid reference type")
    if prediction is None:
        return "abstain"
    if not isinstance(prediction, Mapping):
        return "abstain"
    if "reason" in prediction and not isinstance(prediction["reason"], str):
        return "abstain"
    predicted_type = prediction.get("type")
    if predicted_type == "abstain":
        return "abstain"
    if predicted_type != reference_type:
        return "wrong"
    candidate = dict(prediction)
    candidate["id"] = "proxy-format-check"
    try:
        validate_submission([candidate], ["proxy-format-check"])
    except (ValueError, TypeError, OverflowError):
        return "wrong"
    if reference_type == "unanswerable":
        return "correct"
    if "answer" not in prediction:
        return "wrong"
    value, gold, aliases = prediction["answer"], reference.get("answer"), reference.get("alias", [])
    if reference_type == "number":
        equal = _number_equal(value, gold)
    elif reference_type == "percent":
        equal = _percent_equal(value, gold)
    elif reference_type == "string":
        equal = _string_equal(value, gold, aliases)
    elif reference_type == "date":
        equal = _date_valid(value) and value == gold
    elif reference_type == "boolean":
        equal = isinstance(value, bool) and isinstance(gold, bool) and value is gold
    elif reference_type == "list":
        equal = isinstance(value, list) and isinstance(gold, list) and len(value) == len(gold)
        if equal:
            equal = all(_scalar_equal(item, gold[index], aliases[index]
                        if isinstance(aliases, list) and index < len(aliases) else [])
                        for index, item in enumerate(value))
    else:
        equal = _table_equal(value, gold, aliases)
    return "correct" if equal else "wrong"


def _indexed(records: Iterable[Mapping[str, Any]], label: str) -> dict[str, Mapping[str, Any]]:
    result = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError(f"{label} records must be objects")
        question_id = identifier(record.get("id"), f"{label} id")
        if question_id in result:
            raise ValueError(f"duplicate {label} id")
        result[question_id] = record
    return result


def evaluate_records(references: Iterable[Mapping[str, Any]],
                     predictions: Iterable[Mapping[str, Any]],
                     questions: Iterable[Mapping[str, Any]] | None = None
                     ) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Aggregate proxy verdicts; reject extra IDs instead of quietly dropping them."""
    gold = _indexed(references, "reference")
    guessed = _indexed(predictions, "prediction")
    if not gold:
        raise ValueError("at least one reference is required")
    if guessed.keys() - gold.keys():
        raise ValueError("prediction contains ids outside the evaluated references")
    question_map = _indexed(questions, "question") if questions is not None else None
    if question_map is not None and question_map.keys() != gold.keys():
        raise ValueError("question and reference id sets differ")
    verdicts = [{"id": question_id, "verdict": classify_prediction(guessed.get(question_id), reference)}
                for question_id, reference in gold.items()]
    report = summarize_verdicts(verdicts, len(gold))
    report["missing_as_abstain"] = len(gold.keys() - guessed.keys())
    report["observed_records"] = len(guessed)
    report["notice"] = PROXY_NOTICE
    by_type = defaultdict(list)
    by_business = defaultdict(list)
    for verdict in verdicts:
        question_id = verdict["id"]
        by_type[gold[question_id]["type"]].append(verdict)
        if question_map is not None:
            business_id = identifier(question_map[question_id].get("business_id"), "business_id")
            by_business[business_id].append(verdict)
    report["by_type"] = {name: summarize_verdicts(values, len(values)) for name, values in sorted(by_type.items())}
    if question_map is not None:
        report["by_business"] = {name: summarize_verdicts(values, len(values)) for name, values in sorted(by_business.items())}
    return report, verdicts


def freeze_training_split(train_dir: Path, output_dir: Path, seed: str) -> dict[str, Any]:
    """Create or verify one immutable 80/20 business split of allowed training."""
    question_path = train_dir / "questions.jsonl"
    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return split_training_questions(question_path, output_dir, source_split="train",
                                        seed=seed, ratios=(0.8, 0.2, 0, 0))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_split") != "train" or manifest.get("seed") != seed or \
            manifest.get("algorithm") != "sha256(seed,business_id)" or \
            manifest.get("ratios") != {"train": 0.8, "dev": 0.2, "calibration": 0.0, "lockbox": 0.0} or \
            manifest.get("source_sha256") != hashlib.sha256(question_path.read_bytes()).hexdigest():
        raise ValueError("frozen split manifest does not match source, seed, ratios, or algorithm")
    if set(manifest.get("partitions", {})) != {"train", "dev", "calibration", "lockbox"}:
        raise ValueError("frozen split has invalid partitions")
    for name, details in manifest["partitions"].items():
        if details.get("file") != f"{name}.jsonl":
            raise ValueError("frozen partition path is invalid")
        if hashlib.sha256((output_dir / details["file"]).read_bytes()).hexdigest() != details["sha256"]:
            raise ValueError("frozen partition checksum mismatch")
    return manifest


def run_train_proxy(train_dir: Path, output_dir: Path, seed: str) -> dict[str, Any]:
    """Run dev first and release each business before loading the next.

    Existing reports are immutable: use a new output directory for a new run.
    A previously created, matching frozen split alone may be reused.
    """
    train_dir = train_dir.resolve(strict=True)
    output_dir = output_dir.resolve()
    if output_dir.is_relative_to(train_dir):
        raise ValueError("evaluation output must be outside the input training directory")
    artifacts = ["run.private.json"] + [f"{name}.{suffix}" for name in ("train", "dev")
                 for suffix in ("predictions.jsonl", "verdicts.jsonl", "report.json")]
    if any((output_dir / name).exists() for name in artifacts):
        raise ValueError("evaluation artifacts already exist; refusing to overwrite")
    data_module = importlib.import_module("nosleepclub_datamate.baseline_data")
    query_module = importlib.import_module("nosleepclub_datamate.baseline_query")
    rule_raw = (train_dir / "rulebook.md").read_bytes()
    policy = query_module.RulebookPolicy.from_text(rule_raw.decode("utf-8-sig"))
    source_paths = sorted(Path(__file__).parent.glob("*.py"))
    source_hashes = {path.name: file_sha256(path) for path in source_paths}
    all_questions, question_raw = read_jsonl(train_dir / "questions.jsonl")
    labels, label_raw = read_jsonl(train_dir / "answers.jsonl")
    question_map = _indexed(all_questions, "question")
    gold = _indexed(labels, "reference")
    if question_map.keys() != gold.keys():
        raise ValueError("training question and reference id sets differ")
    data_root = (train_dir / "data").resolve(strict=True)
    business_paths = {}
    for question in all_questions:
        business_id = identifier(question.get("business_id"), "business_id")
        business_path = (data_root / business_id).resolve()
        if business_path == data_root or not business_path.is_relative_to(data_root):
            raise ValueError("business path escapes training data directory")
        business_paths[business_id] = business_path
    input_hashes = _input_hashes(train_dir, business_paths)
    input_hashes["answers.jsonl"] = file_sha256(train_dir / "answers.jsonl")
    if any(input_hashes[name] != hashlib.sha256(raw).hexdigest()
           for name, raw in (("questions.jsonl", question_raw), ("answers.jsonl", label_raw),
                             ("rulebook.md", rule_raw))):
        raise ValueError("evaluation inputs changed while being read")
    split_dir = output_dir / "splits"
    split_manifest = freeze_training_split(train_dir, split_dir, seed)
    failures = []
    reports = {}
    for split_name in ("dev", "train"):
        started = time.monotonic()
        questions, _ = read_jsonl(split_dir / f"{split_name}.jsonl")
        predicted_by_id = {}
        grouped = defaultdict(list)
        for question in questions:
            business_id = identifier(question.get("business_id"), "business_id")
            grouped[business_id].append(question)
        for business_id, group in grouped.items():
            business_path = (data_root / business_id).resolve()
            if business_path == data_root or not business_path.is_relative_to(data_root):
                raise ValueError("business path escapes training data directory")
            business = None
            try:
                business = data_module.load_business(business_path)
            except Exception as exc:
                failures.append({"business_id": business_id, "error_type": type(exc).__name__, "message": str(exc)})
            for question in group:
                if business is None:
                    prediction = {"id": question["id"], "type": "abstain", "reason": "business_load_failed"}
                else:
                    try:
                        prediction = query_module.answer_question(question, business, policy)
                        validate_submission([prediction], [question["id"]])
                    except Exception as exc:
                        failures.append({"id": question["id"], "error_type": type(exc).__name__, "message": str(exc)})
                        prediction = {"id": question["id"], "type": "abstain", "reason": "solver_exception"}
                predicted_by_id[question["id"]] = prediction
            del business
            gc.collect()
        predictions = [predicted_by_id[question["id"]] for question in questions]
        if questions:
            selected_gold = [gold[question["id"]] for question in questions]
            report, verdicts = evaluate_records(selected_gold, predictions, questions)
        else:
            report, verdicts = {"notice": PROXY_NOTICE, "expected_total": 0}, []
        report["elapsed_seconds"] = round(time.monotonic() - started, 6)
        report["source_sha256"] = source_hashes
        reports[split_name] = report
        for filename, records in ((f"{split_name}.predictions.jsonl", predictions),
                                  (f"{split_name}.verdicts.jsonl", verdicts)):
            with (output_dir / filename).open("xb") as stream:
                stream.write(b"".join(json_bytes(record) + b"\n" for record in records))
        with (output_dir / f"{split_name}.report.json").open("xb") as stream:
            stream.write(json_bytes(report) + b"\n")
    if source_hashes != {path.name: file_sha256(path) for path in sorted(Path(__file__).parent.glob("*.py"))}:
        raise ValueError("implementation changed during evaluation; run was not finalized")
    final_inputs = _input_hashes(train_dir, business_paths)
    final_inputs["answers.jsonl"] = file_sha256(train_dir / "answers.jsonl")
    if input_hashes != final_inputs:
        raise ValueError("evaluation inputs changed during run; run was not finalized")
    run = {
        "notice": PROXY_NOTICE,
        "split_manifest_sha256": hashlib.sha256((split_dir / "manifest.json").read_bytes()).hexdigest(),
        "source_questions_sha256": split_manifest["source_sha256"],
        "source_labels_sha256": hashlib.sha256((train_dir / "answers.jsonl").read_bytes()).hexdigest(),
        "source_sha256": source_hashes,
        "input_sha256": input_hashes,
        "solver_module_sha256": hashlib.sha256(Path(query_module.__file__).read_bytes()).hexdigest(),
        "data_module_sha256": hashlib.sha256(Path(data_module.__file__).read_bytes()).hexdigest(),
        "reports": reports,
        "failures": failures,
    }
    with (output_dir / "run.private.json").open("xb") as stream:
        stream.write(json_bytes(run) + b"\n")
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=PROXY_NOTICE)
    parser.add_argument("--train-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path, help="private local artifact directory")
    parser.add_argument("--source-split", required=True, choices=("train",))
    parser.add_argument("--seed", default="nosleepclub-baseline-v1")
    args = parser.parse_args(argv)
    try:
        run = run_train_proxy(args.train_dir, args.output_dir, args.seed)
        public_summary = {
            "notice": PROXY_NOTICE,
            "failure_count": len(run["failures"]),
            "reports": {name: {key: value for key, value in report.items()
                               if key not in ("by_business", "by_type")}
                        for name, report in run["reports"].items()},
        }
        print(json.dumps(public_summary, ensure_ascii=False, sort_keys=True, allow_nan=False))
    except (ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
