"""Create immutable local training partitions grouped by business.

Outputs can contain protected training questions and must remain private. Hash
assignment is deterministic, not stratified; small inputs can have empty splits.
"""

import hashlib
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

from .io import identifier, json_bytes, read_jsonl

PARTITIONS = ("train", "dev", "calibration", "lockbox")
DEFAULT_RATIOS = (0.6, 0.2, 0.1, 0.1)


def split_training_questions(
    input_path: Path,
    output_dir: Path,
    *,
    source_split: str,
    seed: str = "2026-11-02",
    ratios: Sequence[float] = DEFAULT_RATIOS,
) -> dict[str, Any]:
    """Partition an explicitly declared training input; never relabel test inputs.

    The declaration is a guard, not proof of source provenance. Business ID plus
    seed determines membership, independent of question content or row order.
    Canonical business content hashes separately detect changed source questions.
    Existing partition files are never overwritten, protecting a fixed lockbox.
    """
    if source_split != "train":
        raise ValueError("only --source-split train is permitted")
    identifier(seed, "seed")
    if len(ratios) != len(PARTITIONS) or any(isinstance(value, bool) for value in ratios):
        raise ValueError("provide four numeric partition ratios")
    try:
        fractions = tuple(Fraction(str(value)) for value in ratios)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError("ratios must be finite numbers") from exc
    if any(value < 0 for value in fractions) or sum(fractions) != 1:
        raise ValueError("ratios must be nonnegative and sum exactly to one")
    records, raw = read_jsonl(input_path)
    if not records:
        raise ValueError("training input must contain at least one question")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for record in records:
        question_id = identifier(record.get("id"), "id")
        if question_id in seen:
            raise ValueError("duplicate question id")
        seen.add(question_id)
        business_id = identifier(record.get("business_id"), "business_id")
        groups[business_id].append(record)
    cutoffs = []
    running = Fraction(0)
    for value in fractions:
        running += value
        cutoffs.append(running)
    partitions: dict[str, list[dict[str, Any]]] = {name: [] for name in PARTITIONS}
    businesses: dict[str, list[str]] = {name: [] for name in PARTITIONS}
    business_content_hashes = {}
    for business_id, questions in sorted(groups.items()):
        ordered = sorted(questions, key=lambda question: question["id"])
        business_digest = hashlib.sha256(json_bytes(ordered)).hexdigest()
        business_content_hashes[business_id] = business_digest
        digest = hashlib.sha256(json_bytes({
            "seed": seed, "business_id": business_id
        })).digest()
        bucket = int.from_bytes(digest, "big")
        for name, cutoff in zip(PARTITIONS, cutoffs):
            if bucket * cutoff.denominator < cutoff.numerator * (1 << 256):
                partitions[name].extend(ordered)
                businesses[name].append(business_id)
                break
    payloads = {}
    entries = {}
    for name in PARTITIONS:
        ordered = sorted(partitions[name], key=lambda question: question["id"])
        payload = b"".join(json_bytes(record) + b"\n" for record in ordered)
        payloads[f"{name}.jsonl"] = payload
        entries[name] = {
            "file": f"{name}.jsonl",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "question_count": len(ordered),
            "business_count": len(businesses[name]),
            "business_ids": businesses[name],
        }
    canonical = sorted(records, key=lambda question: question["id"])
    manifest = {
        "schema_version": 1,
        "source_split": source_split,
        "seed": seed,
        "algorithm": "sha256(seed,business_id)",
        "ratios": {name: float(value) for name, value in zip(PARTITIONS, fractions)},
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "canonical_questions_sha256": hashlib.sha256(json_bytes(canonical)).hexdigest(),
        "question_count": len(records),
        "business_count": len(groups),
        "business_content_sha256": business_content_hashes,
        "partitions": entries,
        "notice": "Training-only declaration is not independently verified. Small sets may have empty partitions. Keep outputs and business identifiers private.",
    }
    payloads["manifest.json"] = json_bytes(manifest) + b"\n"
    if any((output_dir / name).exists() for name in payloads):
        raise ValueError("output contains partition files; choose a new directory instead of overwriting")
    output_dir.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for name, payload in payloads.items():
            path = output_dir / name
            with path.open("xb") as stream:
                created.append(path)
                stream.write(payload)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return manifest
