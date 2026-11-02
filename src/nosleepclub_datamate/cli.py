"""CLI for honest verdict summaries, declared model checks and training splits."""

import argparse
import json
import sys
from pathlib import Path

from .io import read_jsonl
from .metrics import summarize_verdicts
from .models import validate_models
from .splits import DEFAULT_RATIOS, split_training_questions


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Offline research utilities. No official evaluator or inference implementation."
    )
    commands = root.add_subparsers(dest="command", required=True)
    summarize = commands.add_parser(
        "summarize", help="aggregate verdicts produced by an upstream evaluator"
    )
    summarize.add_argument("verdicts", type=Path, help="JSONL: id and verdict correct/wrong/abstain")
    summarize.add_argument("--expected-total", required=True, type=int, help="full question count N")
    models = commands.add_parser(
        "validate-models", help="check declared constraints, not provenance/license permissions"
    )
    models.add_argument("manifest", type=Path, help="JSON object with a models list")
    split = commands.add_parser(
        "split", help="write local training-only business-grouped partitions; keep them private"
    )
    split.add_argument("questions", type=Path)
    split.add_argument("--source-split", required=True, choices=("train",))
    split.add_argument("--output-dir", required=True, type=Path)
    split.add_argument("--seed", default="2026-11-02")
    split.add_argument("--ratios", nargs=4, type=float, default=DEFAULT_RATIOS,
                       metavar=("TRAIN", "DEV", "CALIBRATION", "LOCKBOX"))
    return root


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "summarize":
            records, _ = read_jsonl(arguments.verdicts)
            result = summarize_verdicts(records, arguments.expected_total)
        elif arguments.command == "validate-models":
            manifest = json.loads(arguments.manifest.read_text(encoding="utf-8-sig"))
            result = validate_models(manifest)
        else:
            manifest = split_training_questions(
                arguments.questions, arguments.output_dir,
                source_split=arguments.source_split, seed=arguments.seed, ratios=arguments.ratios,
            )
            # Membership lives in the private manifest, not stdout/public CI logs.
            result = {
                "manifest": str(arguments.output_dir / "manifest.json"),
                "question_count": manifest["question_count"],
                "business_count": manifest["business_count"],
                "partitions": {
                    name: {key: details[key] for key in ("question_count", "business_count", "sha256")}
                    for name, details in manifest["partitions"].items()
                },
                "notice": manifest["notice"],
            }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False))
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
