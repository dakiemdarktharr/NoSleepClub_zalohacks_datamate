"""Wholly synthetic regression cases for the conservative query interpreter."""
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
import unittest

from nosleepclub_datamate.baseline_query import (
    RulebookPolicy, answer_question, parse_period, _threshold,
)


POLICY = RulebookPolicy(True, True, True, True, True, True)


def business_fixture():
    products = {
        "A01": {"name": "Nuoc tao", "base_unit": "chai"},
        "A02": {"name": "Tra xanh", "base_unit": "chai"},
        "FEE": {"name": "Phi phuc vu"},
    }
    definitions = [
        ("O1", 6, "A01", 2, 200, True, "sold", "tien mat"),
        ("O1", 6, "A02", 1, 100, True, "sold", "tien mat"),
        ("O2", 7, "A02", 4, 400, True, "shipping", "chuyen khoan"),
        ("O3", 7, "A01", 20, 2000, False, "returned", "tien mat"),
        ("O4", 8, "A01", 30, 3000, False, "cancelled", "tien mat"),
        ("O5", 9, "A01", 3, 300, True, "sold", "tien mat"),
    ]
    lines = []
    orders = {}
    for oid, day, pid, qty, total, valid, status, payment in definitions:
        row = dict(order_id=oid, date=date(2026, 7, day),
                   timestamp=datetime(2026, 7, day, 9), product_id=pid,
                   product_name=products[pid]["name"], base_qty=qty,
                   quantity=qty, line_total=total, valid=valid, status=status,
                   payment=payment)
        lines.append(row)
        order = orders.setdefault(oid, dict(row, revenue=0))
        order["revenue"] += total
    return SimpleNamespace(sales_lines=lines, orders=orders, products=products,
                           customers={}, date_start=date(2026, 7, 1),
                           date_end=date(2026, 7, 31),
                           declared_date_start=date(2026, 7, 1),
                           declared_date_end=date(2026, 7, 31))


def question(text, as_of="2026-07-08"):
    return {"id": "synthetic-question", "question": text, "as_of_date": as_of}


class PeriodTests(unittest.TestCase):
    def test_week_crosses_year_boundary(self):
        p = parse_period("Doanh thu tuan truoc", "2026-01-01")
        self.assertEqual((p.start, p.end), (date(2025, 12, 22), date(2025, 12, 28)))

    def test_current_month_is_to_asof(self):
        p = parse_period("Doanh thu thang nay", "2026-07-08")
        self.assertEqual((p.start, p.end), (date(2026, 7, 1), date(2026, 7, 8)))

    def test_explicit_month_is_whole_month(self):
        p = parse_period("Doanh thu thang 2/2024", "2026-07-08")
        self.assertEqual(p.end, date(2024, 2, 29))

    def test_recent_includes_asof(self):
        p = parse_period("Doanh thu 3 ngay gan nhat", "2026-07-08")
        self.assertEqual((p.start, p.end), (date(2026, 7, 6), date(2026, 7, 8)))

    def test_missing_year_uses_past_period(self):
        p = parse_period("Doanh thu thang 12", "2026-07-08")
        self.assertEqual(p.start, date(2025, 12, 1))

    def test_ambiguous_multi_period_abstains(self):
        self.assertIsNone(parse_period("Doanh thu thang 6/2026 so voi thang 5/2026",
                                       "2026-07-08"))

    def test_invalid_dates_and_missing_today(self):
        self.assertIsNone(parse_period("Doanh thu ngay 31/02/2026", "2026-07-08"))
        self.assertIsNone(parse_period("Doanh thu hom nay", None))

    def test_conflicting_relative_days_are_not_silently_selected(self):
        self.assertIsNone(parse_period("Doanh thu hom nay hom qua", "2026-07-08"))

    def test_mixed_month_and_quarter_are_not_silently_selected(self):
        self.assertIsNone(parse_period("Doanh thu quy 2/2026 thang 7/2026", "2026-07-08"))

    def test_mixed_date_formats_preserve_textual_range_order(self):
        p = parse_period("Doanh thu tu 01/07/2026 den 2026-07-05", "2026-07-08")
        self.assertEqual((p.start, p.end), (date(2026, 7, 1), date(2026, 7, 5)))
        self.assertIsNone(parse_period("Doanh thu tu 05/07/2026 den 2026-07-01",
                                       "2026-07-08"))


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.business = business_fixture()

    def solve(self, text, policy=POLICY):
        return answer_question(question(text), self.business, policy)

    def test_revenue_excludes_returned_cancelled_and_relative_future(self):
        self.assertEqual(self.solve("Tong doanh thu thang nay la bao nhieu?")["answer"], 700)

    def test_explicit_month_has_documented_full_month_scope(self):
        self.assertEqual(self.solve("Tong doanh thu thang 7/2026 la bao nhieu?")["answer"], 1000)

    def test_order_count_is_not_line_count(self):
        self.assertEqual(self.solve("Thang nay co bao nhieu don hang?")["answer"], 2)

    def test_cancelled_count(self):
        self.assertEqual(self.solve("Dem so don da huy trong thang nay")["answer"], 1)

    def test_cancelled_rate_includes_all_states_in_denominator(self):
        result = self.solve("Ti le don huy thang nay la bao nhieu %?")
        self.assertEqual((result["type"], result["answer"]), ("percent", 25))

    def test_average_order_uses_distinct_orders_and_rounds_money(self):
        self.assertEqual(
            self.solve("Doanh thu trung binh tren mot don thang nay la bao nhieu?")["answer"], 350)

    def test_product_revenue_is_grounded(self):
        self.assertEqual(
            self.solve("Doanh thu cua Nuoc tao thang nay la bao nhieu?")["answer"], 200)

    def test_unknown_named_product_does_not_become_shop_total(self):
        self.assertEqual(
            self.solve("Thang nay ban Nuoc le duoc bao nhieu tien?")["type"], "abstain")

    def test_multiple_products_do_not_select_only_the_longest_name(self):
        self.business.products["A02"]["name"] = "Tra xanh dac biet"
        self.assertEqual(self.solve(
            "Doanh thu cua Nuoc tao, Tra xanh dac biet thang nay la bao nhieu?")["type"],
            "abstain")

    def test_contained_alias_does_not_make_a_single_name_ambiguous(self):
        self.business.products["A03"] = {"name": "Nuoc"}
        self.assertEqual(self.solve("Doanh thu cua Nuoc tao thang nay la bao nhieu?")["answer"],
                         200)

    def test_unknown_weekday_or_hour_filter_abstains(self):
        for text in ("Doanh thu thu hai thang nay la bao nhieu?",
                     "Doanh thu tu 10h den 12h thang nay la bao nhieu?"):
            with self.subTest(text=text):
                self.assertEqual(self.solve(text)["type"], "abstain")

    def test_unimplemented_new_concepts_abstain(self):
        for text in ("Khach trung thanh nhat thang nay la ai?",
                     "Mat hang pho bien nhat thang nay la gi?",
                     "Bao cao tien mat ca sang thang nay la bao nhieu?"):
            with self.subTest(text=text):
                self.assertEqual(self.solve(text)["type"], "abstain")

    def test_top_products_use_base_quantity(self):
        result = self.solve("Top 2 mat hang ban chay nhat thang nay la gi?")
        self.assertEqual((result["type"], result["answer"]),
                         ("list", ["Tra xanh", "Nuoc tao"]))

    def test_top_product_ties_use_code(self):
        self.business.sales_lines[2]["base_qty"] = 1
        result = self.solve("Mat hang nao ban chay nhat thang nay?")
        self.assertEqual(result["answer"], "Nuoc tao")

    def test_peak_revenue_day(self):
        result = self.solve("Ngay nao doanh thu cao nhat trong thang nay?")
        self.assertEqual((result["type"], result["answer"]), ("date", "2026-07-07"))

    def test_valid_empty_period_is_zero(self):
        result = self.solve("Doanh thu ngay 02/07/2026 la bao nhieu?")
        self.assertEqual((result["type"], result["answer"]), ("number", 0))

    def test_unknown_amount_abstains(self):
        self.business.sales_lines[0]["line_total"] = None
        self.assertEqual(self.solve("Doanh thu thang nay la bao nhieu?")["type"], "abstain")

    def test_unknown_status_abstains(self):
        self.business.sales_lines[0]["valid"] = None
        self.assertEqual(self.solve("Doanh thu thang nay la bao nhieu?")["type"], "abstain")

    def test_missing_policy_abstains(self):
        self.assertEqual(self.solve("Doanh thu thang nay la bao nhieu?",
                                    RulebookPolicy())["type"], "abstain")
        self.assertEqual(self.solve("Doanh thu thang 6/2026 la bao nhieu?",
                                    RulebookPolicy())["type"], "abstain")

    def test_declared_outside_period_is_unanswerable(self):
        self.assertEqual(self.solve("Doanh thu thang 6/2026 la bao nhieu?")["type"],
                         "unanswerable")

    def test_observed_only_boundary_is_uncertain(self):
        self.business.declared_date_start = None
        self.assertEqual(self.solve("Doanh thu thang 6/2026 la bao nhieu?")["type"],
                         "abstain")

    def test_future_period_abstains(self):
        self.assertEqual(self.solve("Doanh thu thang 9/2026 la bao nhieu?")["type"],
                         "abstain")

    def test_revenue_threshold_count(self):
        result = self.solve("Thang nay co bao nhieu don co doanh thu tu 350 dong tro len?")
        self.assertEqual((result["type"], result["answer"]), ("number", 1))

    def test_no_order_ids_means_no_order_count(self):
        self.business.orders = {}
        self.assertEqual(self.solve("Thang nay co bao nhieu don?")["type"], "abstain")

    def test_order_only_register_supports_counts_not_revenue(self):
        self.business.sales_lines = []
        self.assertEqual(self.solve("Thang nay co bao nhieu don?")["answer"], 2)
        self.assertEqual(self.solve("Ti le don huy thang nay la bao nhieu %?")["answer"], 25)
        self.assertEqual(self.solve("Doanh thu thang nay la bao nhieu?")["type"], "abstain")
        self.assertEqual(self.solve(
            "Thang nay co bao nhieu don co doanh thu tu 350 dong tro len?")["type"],
            "abstain")

    def test_per_day_and_average_counts_are_not_period_totals(self):
        for text in ("Thang nay trung binh moi ngay co bao nhieu don?",
                     "Thang nay moi ngay co bao nhieu don?",
                     "Ti le don huy moi ngay thang nay la bao nhieu %?",
                     "Moi ngay thang nay top 2 mat hang ban chay nhat la gi?"):
            with self.subTest(text=text):
                self.assertEqual(self.solve(text)["type"], "abstain")

    def test_unsupported_non_temporal_fact_does_not_become_unanswerable(self):
        self.assertEqual(self.solve("Ten cua hang trong thang 6/2026 la gi?")["type"],
                         "abstain")

    def test_scaled_thresholds_preserve_decimal_values(self):
        for literal in ("1.5 nghin", "1,5 nghin"):
            with self.subTest(literal=literal):
                self.assertEqual(_threshold("doanh thu tu " + literal + " tro len"),
                                 (">=", Decimal(1500)))
        self.assertEqual(_threshold("doanh thu tu 0.5 trieu tro len"),
                         (">=", Decimal(500000)))
        self.assertEqual(_threshold("doanh thu tu 1.500.000 dong tro len"),
                         (">=", Decimal(1500000)))

    def test_malformed_threshold_is_not_coerced_to_an_integer(self):
        self.assertEqual(self.solve(
            "Thang nay co bao nhieu don co doanh thu tu 1.2.3 dong tro len?")["type"],
            "abstain")

    def test_nonfinite_order_revenue_abstains_without_exception(self):
        self.business.orders["O1"]["revenue"] = float("nan")
        self.assertEqual(self.solve(
            "Thang nay co bao nhieu don co doanh thu tu 350 dong tro len?")["type"],
            "abstain")

    def test_punctuated_service_fee_is_not_a_product_rank(self):
        fee = dict(self.business.sales_lines[0], product_id="FEE",
                   product_name="Phi phuc vu.", base_qty=999)
        self.business.sales_lines.append(fee)
        self.assertEqual(self.solve("Mat hang nao ban chay nhat thang nay?")["answer"],
                         "Tra xanh")


if __name__ == "__main__":
    unittest.main()

