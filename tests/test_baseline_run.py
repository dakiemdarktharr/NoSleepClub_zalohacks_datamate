"""Synthetic format gates that prevent uploading a mismatched result file."""

import unittest
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import weakref

from nosleepclub_datamate.baseline_run import run_baseline, validate_submission


class SubmissionValidationTests(unittest.TestCase):
    def test_membership_is_checked_not_just_row_count(self):
        with self.assertRaisesRegex(ValueError, "membership"):
            validate_submission([{"id": "other", "type": "abstain"}], ["wanted"])

    def test_duplicate_cannot_hide_a_missing_answer(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_submission([
                {"id": "a", "type": "abstain"},
                {"id": "a", "type": "number", "answer": 7},
            ], ["a", "b"])

    def test_special_types_omit_answer_and_have_string_reason(self):
        validate_submission([
            {"id": "a", "type": "unanswerable", "reason": "Synthetic field is absent"},
            {"id": "b", "type": "abstain"},
        ], ["a", "b"])
        for extra in ({"answer": None}, {"reason": 0}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                validate_submission([{"id": "a", "type": "unanswerable", **extra}], ["a"])

    def test_json_number_is_not_boolean_or_nonfinite(self):
        for value in (True, float("nan"), float("inf"), "42"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_submission([{"id": "a", "type": "number", "answer": value}], ["a"])

    def test_date_requires_actual_iso_calendar_day(self):
        for value in ("2026-02-30", "20260102", "02/01/2026"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_submission([{"id": "a", "type": "date", "answer": value}], ["a"])
        validate_submission([{"id": "a", "type": "date", "answer": "2026-01-02"}], ["a"])
        validate_submission([{"id": "a", "type": "date", "answer": "2026-01"}], ["a"])
        with self.assertRaises(ValueError):
            validate_submission([{"id": "a", "type": "date", "answer": "2026-13"}], ["a"])

    def test_table_rows_have_declared_width_and_finite_cells(self):
        for rows in ([["Synthetic entity"]], [["Synthetic entity", float("nan")]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                validate_submission([{"id": "a", "type": "table", "answer": {
                    "columns": ["entity", "total"], "rows": rows}}], ["a"])


class PrivateRunnerTests(unittest.TestCase):
    def test_interleaved_businesses_release_memory_preserve_order_and_never_read_gold(self):
        class Business:
            pass

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            split = root / "split"
            for name in ("alpha", "beta"):
                business_dir = split / "data" / name
                business_dir.mkdir(parents=True)
                (business_dir / "README.md").write_text("Wholly synthetic fixture", encoding="utf-8")
            questions = [
                {"id": "first", "business_id": "beta", "question": "Synthetic total?", "as_of_date": "2026-01-01"},
                {"id": "second", "business_id": "alpha", "question": "Synthetic total?", "as_of_date": "2026-01-01"},
                {"id": "third", "business_id": "beta", "question": "Synthetic total?", "as_of_date": "2026-01-01"},
            ]
            (split / "questions.jsonl").write_text("".join(json.dumps(q) + "\n" for q in questions), encoding="utf-8")
            (split / "rulebook.md").write_text("Synthetic test policy", encoding="utf-8")
            # Invalid bytes deliberately make accidental label ingestion fail.
            (split / "answers.jsonl").write_bytes(b"\xff\xfeTHIS MUST NEVER BE READ")
            references = []
            loaded = []

            def load(path):
                self.assertTrue(all(reference() is None for reference in references))
                instance = Business()
                instance.value = 2 if path.name == "beta" else 1
                references.append(weakref.ref(instance))
                loaded.append(path.name)
                return instance

            def solve(question, business, policy):
                return {"id": question["id"], "type": "number", "answer": business.value}

            output = root / "private-run"
            with patch("nosleepclub_datamate.baseline_data.load_business", new=load), \
                 patch("nosleepclub_datamate.baseline_query.solve_question", new=solve), \
                 redirect_stdout(io.StringIO()):
                manifest = run_baseline(split, output)
            predictions = [json.loads(line) for line in (output / "submission.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([row["id"] for row in predictions], ["first", "second", "third"])
            self.assertEqual([row["answer"] for row in predictions], [2, 1, 2])
            self.assertEqual(loaded, ["beta", "alpha"])
            self.assertTrue(all(reference() is None for reference in references))
            self.assertNotIn("answers.jsonl", manifest["input_sha256"])
            self.assertIn("io.py", manifest["source_sha256"])
            original = (output / "submission.jsonl").read_bytes()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run_baseline(split, output)
            self.assertEqual(original, (output / "submission.jsonl").read_bytes())


if __name__ == "__main__":
    unittest.main()
