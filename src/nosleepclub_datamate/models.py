"""Validate declared model-budget evidence, not provenance or license legality."""

import re
from datetime import date
from typing import Any

from .io import identifier

PARAMETER_LIMIT = 15_000_000_000
RELEASE_CUTOFF = date(2026, 10, 1)
SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def validate_models(manifest: Any) -> dict[str, Any]:
    """Reject invalid declarations; require a separate human provenance/license audit.

    An empty model list is valid for a model-free deterministic solution. All model
    instances/components used at inference must be declared, including sequential
    use and full MoE parameter counts. This tool cannot inspect omitted weights.
    """
    if not isinstance(manifest, dict) or not isinstance(manifest.get("models"), list):
        raise ValueError("manifest must contain a models list")
    total = 0
    seen_checkpoints = set()
    for model in manifest["models"]:
        if not isinstance(model, dict):
            raise ValueError("each model must be an object")
        identifier(model.get("name"), "model name")
        parameters = model.get("parameter_count")
        if isinstance(parameters, bool) or not isinstance(parameters, int) or parameters <= 0:
            raise ValueError("parameter_count must be a positive integer, not boolean")
        total += parameters
        release = model.get("public_release_date")
        if not isinstance(release, str) or not DATE_PATTERN.fullmatch(release):
            raise ValueError("public_release_date must be ISO YYYY-MM-DD")
        try:
            release_date = date.fromisoformat(release)
        except ValueError as exc:
            raise ValueError("public_release_date is not a valid calendar date") from exc
        if release_date >= RELEASE_CUTOFF:
            raise ValueError("model weights must have been public before 2026-10-01")
        identifier(model.get("license"), "license")
        checkpoint = model.get("checkpoint_sha256")
        if not isinstance(checkpoint, str) or not SHA256_PATTERN.fullmatch(checkpoint):
            raise ValueError("checkpoint_sha256 must contain exactly 64 hexadecimal characters")
        checkpoint = checkpoint.lower()
        if checkpoint in seen_checkpoints:
            raise ValueError("duplicate checkpoint_sha256 declaration")
        seen_checkpoints.add(checkpoint)
    if total > PARAMETER_LIMIT:
        raise ValueError(f"declared parameter total exceeds {PARAMETER_LIMIT}")
    return {
        "valid_declared_constraints": True,
        "model_count": len(manifest["models"]),
        "total_parameter_count": total,
        "parameter_limit": PARAMETER_LIMIT,
        "remaining_parameter_budget": PARAMETER_LIMIT - total,
        "release_cutoff_exclusive": RELEASE_CUTOFF.isoformat(),
        "scope": "Declared fields only; provenance, completeness, checkpoint bytes, and license permissions are not verified.",
    }
