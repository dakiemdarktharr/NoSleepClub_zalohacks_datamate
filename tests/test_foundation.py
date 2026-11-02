"""Behavioral boundaries using original synthetic inputs only."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from nosleepclub_datamate.metrics import summarize_verdicts
from nosleepclub_datamate.io import read_jsonl
from nosleepclub_datamate.models import PARAMETER_LIMIT, validate_models
from nosleepclub_datamate.splits import PARTITIONS, split_training_questions


ROOT = Path(__file__).resolve().parents[1]


def write_jsonl(path, records):
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def model(**changes):
    entry = {
        "name": "synthetic-model-declaration",
        "parameter_count": 1,
        "public_release_date": "2026-09-30",
        "license": "Apache-2.0",
        "checkpoint_sha256": "a" * 64,
    }
    entry.update(changes)
    return entry


class MetricsTests(unittest.TestCase):
    def test_missing_records_are_abstentions_and_gap_weights_errors_twice(self):
        result = summarize_verdicts([
            {"id": "synthetic-c", "verdict": "correct"},
            {"id": "synthetic-w", "verdict": "wrong"},
            {"id": "synthetic-a", "verdict": "abstain"},
        ], 5)
        self.assertEqual((result["C"], result["W"], result["A"]), (1, 1, 3))
        self.assertEqual(result["missing_as_abstain"], 2)
        self.assertEqual(result["PA"], 0)
        self.assertEqual(result["coverage"], 0.4)
        self.assertEqual(result["selective_accuracy"], 0.5)
        self.assertEqual(result["gap"], 1)

    def test_all_missing_has_undefined_selective_accuracy(self):
        result = summarize_verdicts([], 4)
        self.assertEqual(result["A"], 4)
        self.assertEqual(result["PA"], 0)
        self.assertEqual(result["coverage"], 0)
        self.assertIsNone(result["selective_accuracy"])

    def test_perfect_and_all_wrong_extremes(self):
        for verdict, expected_pa, expected_gap in (("correct", 1, 0), ("wrong", -1, 2)):
            with self.subTest(verdict=verdict):
                result = summarize_verdicts([{"id": "synthetic", "verdict": verdict}], 1)
                self.assertEqual(result["PA"], expected_pa)
                self.assertEqual(result["gap"], expected_gap)
                self.assertEqual(1 - result["PA"], result["gap"])

    def test_rejects_invalid_total_duplicate_ids_and_unknown_verdict(self):
        valid = {"id": "synthetic", "verdict": "correct"}
        for invalid_total in (0, -1, True, 2.0):
            with self.subTest(total=invalid_total), self.assertRaises(ValueError):
                summarize_verdicts([], invalid_total)
        for records, total in (([valid, valid], 2), ([valid], 0),
                               ([valid, {"id": "another", "verdict": "wrong"}], 1),
                               ([{"id": "x", "verdict": "unanswerable"}], 1),
                               ([{"id": " ", "verdict": "correct"}], 1),
                               ([{"verdict": "correct"}], 1),
                               ([{"id": "x", "verdict": []}], 1)):
            with self.subTest(records=records), self.assertRaises(ValueError):
                summarize_verdicts(records, total)


class JsonlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "synthetic.jsonl"
        self.addCleanup(self.temporary.cleanup)

    def test_unicode_line_separators_inside_json_strings_are_preserved(self):
        records = [{"id": "synthetic", "question": "a\u2028b\u2029c\u0085d"}]
        write_jsonl(self.path, records)
        parsed, _ = read_jsonl(self.path)
        self.assertEqual(parsed, records)

    def test_crlf_and_optional_final_delimiter(self):
        records = [{"id": "synthetic-a"}, {"id": "synthetic-b"}]
        for suffix in (b"", b"\r\n"):
            raw = b"\r\n".join(json.dumps(record).encode("utf-8") for record in records) + suffix
            self.path.write_bytes(raw)
            with self.subTest(suffix=suffix):
                parsed, original = read_jsonl(self.path)
                self.assertEqual(parsed, records)
                self.assertEqual(original, raw)

    def test_blank_physical_records_are_rejected(self):
        for raw in (b"\n", b'{}\n\n', b'{}\r\n\r\n', b'{}\n \n{}'):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "blank"):
                read_jsonl(self.path)

    def test_duplicate_json_members_cannot_silently_replace_ids_or_nested_answers(self):
        for raw in (b'{"id":"first","id":"second"}',
                    b'{"id":"a","answer":{"amount":1,"amount":2}}'):
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "invalid JSON"):
                read_jsonl(self.path)

    def test_nonfinite_literals_and_overflow_are_rejected_at_any_depth(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            self.path.write_text('{"id":"a","answer":[' + token + ']}', encoding="utf-8")
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "invalid JSON"):
                read_jsonl(self.path)


class ModelManifestTests(unittest.TestCase):
    def test_exact_aggregate_limit_is_allowed(self):
        result = validate_models({"models": [
            model(parameter_count=14_000_000_000),
            model(name="synthetic-small", parameter_count=1_000_000_000,
                  checkpoint_sha256="b" * 64),
        ]})
        self.assertEqual(result["total_parameter_count"], PARAMETER_LIMIT)
        self.assertEqual(result["remaining_parameter_budget"], 0)
        self.assertIn("not verified", result["scope"])

    def test_aggregate_limit_plus_one_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeds"):
            validate_models({"models": [
                model(parameter_count=PARAMETER_LIMIT),
                model(checkpoint_sha256="b" * 64),
            ]})

    def test_release_cutoff_is_exclusive_and_dates_are_real(self):
        for release in ("2026-10-01", "2026-10-02", "2026-09-31", "20260930", ""):
            with self.subTest(release=release), self.assertRaises(ValueError):
                validate_models({"models": [model(public_release_date=release)]})
        self.assertTrue(validate_models({"models": [model(public_release_date="2024-02-29")]})
                        ["valid_declared_constraints"])

    def test_parameter_count_must_be_positive_integer_not_boolean(self):
        for parameters in (True, False, 0, -1, 1.0, "100"):
            with self.subTest(parameters=parameters), self.assertRaises(ValueError):
                validate_models({"models": [model(parameter_count=parameters)]})

    def test_duplicate_checkpoint_is_case_insensitive(self):
        with self.assertRaisesRegex(ValueError, "duplicate checkpoint"):
            validate_models({"models": [model(), model(checkpoint_sha256="A" * 64)]})

    def test_required_evidence_fields_and_empty_models(self):
        for changes in ({"name": " "}, {"license": ""}, {"checkpoint_sha256": "abc"},
                        {"checkpoint_sha256": "z" * 64}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_models({"models": [model(**changes)]})
        for invalid in ([], {}, {"models": {}}, {"models": [None]}):
            with self.subTest(manifest=invalid), self.assertRaises(ValueError):
                validate_models(invalid)
        self.assertEqual(validate_models({"models": []})["total_parameter_count"], 0)


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.input = self.root / "synthetic-questions.jsonl"
        self.records = [
            {"id": f"synthetic-q-{business}-{question}",
             "business_id": f"synthetic-business-{business}",
             "question": "Một câu hỏi tổng hợp do kiểm thử tự tạo.",
             "as_of_date": "2026-02-03"}
            for business in range(60) for question in range(3)
        ]
        write_jsonl(self.input, self.records)

    def run_split(self, name, **kwargs):
        return split_training_questions(
            self.input, self.root / name, source_split="train", **kwargs
        )

    def test_no_question_loss_or_business_overlap_and_hashes_match(self):
        manifest = self.run_split("partitions")
        seen_questions = set()
        seen_businesses = set()
        for name, details in manifest["partitions"].items():
            raw = (self.root / "partitions" / details["file"]).read_bytes()
            self.assertEqual(details["sha256"], hashlib.sha256(raw).hexdigest())
            records = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
            businesses = {record["business_id"] for record in records}
            self.assertFalse(seen_businesses & businesses)
            seen_businesses.update(businesses)
            self.assertEqual(details["question_count"], len(records))
            self.assertEqual(details["business_count"], len(businesses))
            for record in records:
                self.assertNotIn(record["id"], seen_questions)
                seen_questions.add(record["id"])
            self.assertEqual(set(details["business_ids"]), businesses)
            self.assertIn(name, PARTITIONS)
        self.assertEqual(seen_questions, {record["id"] for record in self.records})
        self.assertEqual(len(seen_businesses), 60)
        self.assertEqual(manifest["source_sha256"], hashlib.sha256(self.input.read_bytes()).hexdigest())

    def test_membership_and_output_are_invariant_to_input_order(self):
        first = self.run_split("first", seed="fixed-seed")
        write_jsonl(self.input, list(reversed(self.records)))
        second = self.run_split("second", seed="fixed-seed")
        self.assertEqual(first["partitions"], second["partitions"])
        self.assertEqual(first["canonical_questions_sha256"], second["canonical_questions_sha256"])
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])
        for name in PARTITIONS:
            self.assertEqual((self.root / "first" / f"{name}.jsonl").read_bytes(),
                             (self.root / "second" / f"{name}.jsonl").read_bytes())

    def test_different_seed_changes_group_assignment(self):
        first = self.run_split("first", seed="synthetic-seed-1")
        second = self.run_split("second", seed="synthetic-seed-2")
        self.assertNotEqual(first["partitions"], second["partitions"])

    def test_editing_and_adding_questions_never_moves_existing_businesses(self):
        first = self.run_split("before", seed="fixed-seed")
        changed = [dict(record) for record in self.records]
        changed[0]["question"] = "Synthetic wording changed after the split was fixed."
        changed.append({"id": "synthetic-added-question", "business_id": "synthetic-business-0"})
        changed.append({"id": "synthetic-new-business-question", "business_id": "synthetic-business-new"})
        write_jsonl(self.input, changed)
        second = self.run_split("after", seed="fixed-seed")
        memberships = lambda manifest: {
            business: name for name, details in manifest["partitions"].items()
            for business in details["business_ids"]
        }
        old_memberships = memberships(first)
        new_memberships = memberships(second)
        self.assertEqual(old_memberships, {business: new_memberships[business] for business in old_memberships})
        self.assertNotEqual(first["business_content_sha256"]["synthetic-business-0"],
                            second["business_content_sha256"]["synthetic-business-0"])
        self.assertEqual(first["business_content_sha256"]["synthetic-business-1"],
                         second["business_content_sha256"]["synthetic-business-1"])
        self.assertEqual(second["question_count"], first["question_count"] + 2)
        self.assertEqual(second["algorithm"], "sha256(seed,business_id)")

    def test_small_dataset_can_have_empty_splits_and_is_not_overwritten(self):
        write_jsonl(self.input, self.records[:3])
        manifest = self.run_split("small")
        sizes = [entry["question_count"] for entry in manifest["partitions"].values()]
        self.assertEqual(sorted(sizes), [0, 0, 0, 3])
        original = (self.root / "small" / "manifest.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "overwriting"):
            self.run_split("small", seed="different")
        self.assertEqual((self.root / "small" / "manifest.json").read_bytes(), original)

    def test_nontraining_duplicate_missing_business_and_invalid_ratios_rejected(self):
        with self.assertRaisesRegex(ValueError, "train"):
            split_training_questions(self.input, self.root / "test", source_split="public")
        for ratios in ((0.5, 0.2, 0.1, 0.1), (-0.1, 0.9, 0.1, 0.1),
                       (float("nan"), 0.2, 0.1, 0.1), (True, 0, 0, 0), (1, 0)):
            with self.subTest(ratios=ratios), self.assertRaises(ValueError):
                self.run_split("invalid-ratios", ratios=ratios)
        for records in ([self.records[0], self.records[0]],
                        [{"id": "synthetic", "question": "missing business"}],
                        [{"id": " ", "business_id": "synthetic"}], []):
            write_jsonl(self.input, records)
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.run_split("invalid-records")
        self.assertFalse((self.root / "invalid-records").exists())

    def test_explicit_zero_ratios_and_input_preservation(self):
        original = self.input.read_bytes()
        manifest = self.run_split("all-train", ratios=(1, 0, 0, 0))
        self.assertEqual(manifest["partitions"]["train"]["question_count"], len(self.records))
        self.assertEqual(self.input.read_bytes(), original)
        for name in ("dev", "calibration", "lockbox"):
            self.assertEqual(manifest["partitions"][name]["question_count"], 0)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def cli(self, *arguments):
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "nosleepclub_datamate", *map(str, arguments)],
            cwd=ROOT, env=environment, text=True, capture_output=True, check=False,
            encoding="utf-8",
        )

    def test_all_three_commands_end_to_end(self):
        verdicts = self.root / "verdicts.jsonl"
        write_jsonl(verdicts, [{"id": "synthetic", "verdict": "correct"}])
        summary = self.cli("summarize", verdicts, "--expected-total", 2)
        self.assertEqual(summary.returncode, 0, summary.stderr)
        self.assertEqual(json.loads(summary.stdout)["PA"], 0.5)
        manifest = self.root / "models.json"
        manifest.write_text(json.dumps({"models": [model()]}), encoding="utf-8")
        models = self.cli("validate-models", manifest)
        self.assertEqual(models.returncode, 0, models.stderr)
        self.assertEqual(json.loads(models.stdout)["total_parameter_count"], 1)
        questions = self.root / "questions.jsonl"
        write_jsonl(questions, [{"id": "synthetic", "business_id": "synthetic-business"}])
        split = self.cli("split", questions, "--source-split", "train",
                         "--output-dir", self.root / "partitions")
        self.assertEqual(split.returncode, 0, split.stderr)
        self.assertEqual(json.loads(split.stdout)["question_count"], 1)
        self.assertNotIn("synthetic-business", split.stdout)
        self.assertTrue((self.root / "partitions" / "manifest.json").exists())

    def test_invalid_input_and_missing_required_flags_have_nonzero_exit(self):
        verdicts = self.root / "bad.jsonl"
        verdicts.write_text('{"id":"synthetic","verdict":"unknown"}\n', encoding="utf-8")
        invalid = self.cli("summarize", verdicts, "--expected-total", 1)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("error:", invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)
        self.assertEqual(invalid.stdout, "")
        self.assertEqual(self.cli("summarize", verdicts).returncode, 2)
        self.assertEqual(self.cli("split", verdicts, "--output-dir", self.root / "bad").returncode, 2)


if __name__ == "__main__":
    unittest.main()
