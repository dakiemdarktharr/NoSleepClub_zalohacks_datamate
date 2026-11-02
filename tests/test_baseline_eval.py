"""Original synthetic reference/prediction fixtures for the local proxy only."""

import json
from pathlib import Path
import tempfile
import unittest

from nosleepclub_datamate.baseline_eval import classify_prediction, evaluate_records, freeze_training_split


def reference(kind, answer=None, aliases=None):
    return {"id": "synthetic", "type": kind, "answer": answer, "alias": aliases or []}


class ProxyMatchingTests(unittest.TestCase):
    def assertVerdict(self, kind, answer, guessed, expected="correct", aliases=None):
        self.assertEqual(classify_prediction({"id": "synthetic", "type": kind, "answer": guessed},
                                             reference(kind, answer, aliases)), expected)

    def test_numbers_reject_strings_boolean_nonfinite_and_one_vnd_error(self):
        self.assertVerdict("number", 1_000_000_000, 1_000_000_001, "wrong")
        self.assertVerdict("number", 18, "18", "wrong")
        self.assertVerdict("number", 1, True, "wrong")
        self.assertVerdict("number", 1, float("nan"), "wrong")
        self.assertVerdict("number", 0.3, 0.1 + 0.2)

    def test_percent_scale_sign_and_no_automatic_output_rounding(self):
        self.assertVerdict("percent", -12.34, -12.344, "wrong")
        self.assertVerdict("percent", -12.34, -12.340000000000002)
        self.assertVerdict("percent", 12.34, 0.1234, "wrong")
        self.assertVerdict("percent", -12.34, 12.34, "wrong")

    def test_strings_normalize_unicode_case_punctuation_but_keep_accents(self):
        self.assertVerdict("string", "Cà phê sữa", "  CÀ--PHÊ   SỮA! ")
        self.assertVerdict("string", "Cà phê sữa", "Ca phe sua", "wrong")
        self.assertVerdict("string", "Cà phê sữa", "SYNTHETIC-ITEM-1", aliases=["synthetic item 1"])

    def test_dates_and_booleans_have_strict_formats(self):
        self.assertVerdict("date", "2026-02", "2026-02")
        self.assertVerdict("date", "2026-02-01", "01/02/2026", "wrong")
        self.assertVerdict("date", "2026-02-30", "2026-02-30", "wrong")
        self.assertVerdict("boolean", True, True)
        self.assertVerdict("boolean", True, 1, "wrong")

    def test_ordered_list_uses_parallel_aliases_and_preserves_numeric_types(self):
        self.assertVerdict("list", ["Mặt hàng A", "Mặt hàng B"], ["A1", "B2"],
                           aliases=[["A1"], ["B2"]])
        self.assertVerdict("list", ["Mặt hàng A", "Mặt hàng B"], ["B2", "A1"], "wrong",
                           aliases=[["A1"], ["B2"]])
        self.assertVerdict("list", [3, 10], ["3", 10], "wrong")

    def test_table_rows_unordered_columns_named_or_positional_and_aliases(self):
        gold = {"columns": ["customer", "debt"], "rows": [["Khách A", 5], ["Khách B", 10]]}
        swapped = {"columns": ["DEBT", "CUSTOMER"], "rows": [[10, "B2"], [5, "A1"]]}
        self.assertVerdict("table", gold, swapped, aliases=[["A1"], ["B2"]])
        positional = {"columns": ["who", "amount"], "rows": [["Khách B", 10], ["Khách A", 5]]}
        self.assertVerdict("table", gold, positional)
        bad = {"columns": ["who", "amount"], "rows": [["Khách A", 5], ["Khách A", 5]]}
        self.assertVerdict("table", gold, bad, "wrong")

    def test_table_alias_matching_does_not_greedily_consume_the_only_row(self):
        gold = {"columns": ["entity", "count"], "rows": [["A", 5], ["B", 5]]}
        predicted = {"columns": ["entity", "count"], "rows": [["shared", 5], ["only-A", 5]]}
        self.assertVerdict("table", gold, predicted, aliases=[["shared", "only-A"], ["shared"]])

    def test_unanswerable_is_scored_answer_abstain_is_neutral_invalid_reason_is_missing(self):
        gold = reference("unanswerable")
        self.assertEqual(classify_prediction({"type": "unanswerable"}, gold), "correct")
        self.assertEqual(classify_prediction({"type": "abstain"}, gold), "abstain")
        self.assertEqual(classify_prediction(None, gold), "abstain")
        self.assertEqual(classify_prediction({"type": "number", "answer": 0}, gold), "wrong")
        self.assertEqual(classify_prediction({"type": "unanswerable", "reason": 1}, gold), "abstain")
        self.assertEqual(classify_prediction({"type": "unanswerable"}, reference("number", 0)), "wrong")

    def test_type_mismatch_is_wrong_and_missing_predictions_use_full_denominator(self):
        labels = [reference("number", 7), {**reference("string", "A"), "id": "synthetic-missing"}]
        report, verdicts = evaluate_records(labels, [{"id": "synthetic", "type": "string", "answer": "7"}])
        self.assertEqual((report["C"], report["W"], report["A"]), (0, 1, 1))
        self.assertEqual(report["PA"], -0.5)
        self.assertEqual(report["missing_as_abstain"], 1)
        self.assertEqual(len(verdicts), 2)
        self.assertIn("NOT THE OFFICIAL", report["notice"])

    def test_duplicate_or_extra_ids_rejected(self):
        gold = [reference("number", 1)]
        prediction = {"id": "synthetic", "type": "number", "answer": 1}
        for predictions in ([prediction, prediction], [{**prediction, "id": "outside"}]):
            with self.subTest(predictions=predictions), self.assertRaises(ValueError):
                evaluate_records(gold, predictions)


class FrozenTrainingSplitTests(unittest.TestCase):
    def test_frozen_split_is_reused_verified_and_source_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train = root / "train"
            train.mkdir()
            questions = [{"id": f"synthetic-q-{i}", "business_id": f"synthetic-b-{i // 3}"}
                         for i in range(90)]
            source = train / "questions.jsonl"
            source.write_text("".join(json.dumps(record) + "\n" for record in questions), encoding="utf-8")
            first = freeze_training_split(train, root / "splits", "frozen")
            second = freeze_training_split(train, root / "splits", "frozen")
            self.assertEqual(first, second)
            train_businesses = set(first["partitions"]["train"]["business_ids"])
            dev_businesses = set(first["partitions"]["dev"]["business_ids"])
            self.assertFalse(train_businesses & dev_businesses)
            self.assertEqual(len(train_businesses | dev_businesses), 30)
            with self.assertRaisesRegex(ValueError, "frozen"):
                freeze_training_split(train, root / "splits", "different")
            source.write_text(source.read_text(encoding="utf-8") + json.dumps(
                {"id": "synthetic-new", "business_id": "synthetic-b-new"}) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen"):
                freeze_training_split(train, root / "splits", "frozen")


if __name__ == "__main__":
    unittest.main()
