"""Original synthetic reference/prediction fixtures for the local proxy only."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import weakref

from nosleepclub_datamate.baseline_eval import classify_prediction, evaluate_records, freeze_training_split, run_train_proxy


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
        self.assertEqual(classify_prediction({"type": "unanswerable", "answer": 0}, gold), "wrong")

    def test_proxy_rejects_nested_or_boolean_list_cells(self):
        self.assertVerdict("list", [1], [True], "wrong")
        self.assertVerdict("list", ["synthetic"], [{"nested": "synthetic"}], "wrong")

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
    def test_proxy_binds_business_files_and_calendar_and_rejects_mutations(self):
        for changed_file in ("business", "calendar"):
            with self.subTest(changed_file=changed_file), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                train = root / "train"
                business = train / "data" / "synthetic"
                business.mkdir(parents=True)
                readme = business / "README.md"
                readme.write_text("Synthetic initial business", encoding="utf-8")
                calendar = train / "calendar.csv"
                calendar.write_text("synthetic\n1\n", encoding="utf-8")
                question = {"id": "synthetic-q", "business_id": "synthetic"}
                (train / "questions.jsonl").write_text(json.dumps(question) + "\n", encoding="utf-8")
                (train / "answers.jsonl").write_text(json.dumps(
                    {"id": "synthetic-q", "type": "number", "answer": 7, "alias": []}) + "\n", encoding="utf-8")
                (train / "rulebook.md").write_text("Synthetic policy", encoding="utf-8")

                def solve(question, loaded, policy):
                    target = readme if changed_file == "business" else calendar
                    target.write_text("Synthetic mutation", encoding="utf-8")
                    return {"id": question["id"], "type": "number", "answer": 7}

                output = root / "private-evaluation"
                with patch("nosleepclub_datamate.baseline_data.load_business", return_value=object()), \
                     patch("nosleepclub_datamate.baseline_query.answer_question", new=solve), \
                     self.assertRaisesRegex(ValueError, "inputs changed"):
                    run_train_proxy(train, output, "frozen")
                self.assertFalse((output / "run.private.json").exists())

    def test_proxy_releases_each_business_and_preserves_existing_reports(self):
        class Business:
            pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train = root / "train"
            train.mkdir()
            questions = [{"id": f"synthetic-q-{index}", "business_id": f"synthetic-b-{index % 8}",
                          "question": "Synthetic count?", "as_of_date": "2026-01-01"}
                         for index in range(24)]
            labels = [{"id": question["id"], "type": "number", "answer": 7, "alias": []}
                      for question in questions]
            for name, records in (("questions.jsonl", questions), ("answers.jsonl", labels)):
                (train / name).write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
            (train / "rulebook.md").write_text("Synthetic policy", encoding="utf-8")
            (train / "data").mkdir()
            references = []

            def load(path):
                self.assertTrue(all(reference() is None for reference in references))
                business = Business()
                references.append(weakref.ref(business))
                return business

            def solve(question, business, policy):
                return {"id": question["id"], "type": "number", "answer": 7}

            output = root / "private-evaluation"
            with patch("nosleepclub_datamate.baseline_data.load_business", new=load), \
                 patch("nosleepclub_datamate.baseline_query.answer_question", new=solve):
                report = run_train_proxy(train, output, "synthetic-seed")
            self.assertTrue(all(reference() is None for reference in references))
            self.assertEqual(sum(part["expected_total"] for part in report["reports"].values()), 24)
            self.assertEqual(len(references), 8)
            original = (output / "dev.report.json").read_bytes()
            with self.assertRaisesRegex(ValueError, "overwrite"):
                run_train_proxy(train, output, "synthetic-seed")
            self.assertEqual(original, (output / "dev.report.json").read_bytes())

    def test_frozen_manifest_cannot_redirect_a_partition_outside_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train = root / "train"
            train.mkdir()
            (train / "questions.jsonl").write_text('{"id":"synthetic","business_id":"synthetic"}\n', encoding="utf-8")
            freeze_training_split(train, root / "splits", "frozen")
            manifest_path = root / "splits" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["partitions"]["train"]["file"] = "../outside.jsonl"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "path"):
                freeze_training_split(train, root / "splits", "frozen")

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
