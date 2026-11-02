"""Aggregate externally produced verdicts; never compare predictions to references."""

from collections.abc import Iterable
from typing import Any

from .io import identifier


def summarize_verdicts(
    records: Iterable[dict[str, Any]], expected_total: int
) -> dict[str, Any]:
    """Summarize correct/wrong/abstain verdicts from an upstream evaluator.

    The caller supplies N because absent output records still count as abstentions.
    This function does not verify upstream verdict correctness or ID membership.
    """
    if isinstance(expected_total, bool) or not isinstance(expected_total, int) or expected_total <= 0:
        raise ValueError("expected_total must be a positive integer")
    counts = {"correct": 0, "wrong": 0, "abstain": 0}
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("verdict record must be an object")
        question_id = identifier(record.get("id"), "id")
        if question_id in seen:
            raise ValueError("duplicate question id")
        seen.add(question_id)
        verdict = record.get("verdict")
        if not isinstance(verdict, str) or verdict not in counts:
            raise ValueError("verdict must be correct, wrong, or abstain")
        counts[verdict] += 1
    if len(seen) > expected_total:
        raise ValueError("expected_total cannot be smaller than observed records")
    missing = expected_total - len(seen)
    correct = counts["correct"]
    wrong = counts["wrong"]
    abstain = counts["abstain"] + missing
    answered = correct + wrong
    return {
        "expected_total": expected_total,
        "observed_records": len(seen),
        "missing_as_abstain": missing,
        "C": correct,
        "W": wrong,
        "A": abstain,
        "PA": (correct - wrong) / expected_total,
        "coverage": answered / expected_total,
        "selective_accuracy": correct / answered if answered else None,
        "gap": (abstain + 2 * wrong) / expected_total,
    }
