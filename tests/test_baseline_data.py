"""Wholly synthetic cases for the conservative data baseline."""

import csv
import hashlib
import sqlite3
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from nosleepclub_datamate.baseline_data import load_business, normalize_status, parse_date, parse_number


class BaselineDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.split = Path(self.temporary.name) / "split"
        self.shop = self.split / "data" / "synthetic-shop"
        self.shop.mkdir(parents=True)
        (self.shop / "README.md").write_text("# Original synthetic shop\n", encoding="utf-8")

    def csv(self, name, rows):
        with (self.shop / name).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerows(rows)

    def test_numeric_and_date_formats(self):
        for value, expected in (("25.000đ", 25000), ("1,5", 1.5), ("1 bao 25kg", 1),
                                ("1.234,50", 1234.5), ("0.125", .125), ("25,5k", 25500)):
            self.assertEqual(parse_number(value), expected)
        self.assertIsNone(parse_number(True))
        self.assertIsNone(parse_number(""))
        self.assertEqual(parse_date("2 thg 3 2026"), date(2026, 3, 2))
        self.assertEqual(parse_date("02/03", year=2025), date(2025, 3, 2))
        self.assertEqual(parse_date(46023), date(2026, 1, 1))

    def test_status_aliases_keep_returns_distinct_from_cancellations(self):
        self.assertEqual(normalize_status("ok"), "sold")
        self.assertEqual(normalize_status("hàng trả về"), "returned")
        self.assertEqual(normalize_status("trả lại"), "returned")
        self.assertEqual(normalize_status("Không giao được"), "cancelled")
        self.assertEqual(normalize_status("Đang vận chuyển"), "shipping")

    def test_whole_order_returns_dedup_and_forward_fill(self):
        self.csv("sales.csv", [
            ["Mã đơn", "Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền"],
            ["A", "01/01/2026", "completed", "Synthetic tea", 1, 10],
            ["A", "01/01/2026", "completed", "Synthetic tea", 1, 10],
            ["", "", "", "Synthetic cake", 2, 20],
            ["B", "02/01/2026", "shipping", "Synthetic tea", 1, 10],
            ["A", "10/01/2026", "returned", "Synthetic tea", -1, -10],
        ])
        data = load_business(self.shop)
        self.assertEqual(len(data.sales_lines), 4)
        self.assertEqual(data.orders["A"]["status"], "returned")
        self.assertFalse(data.orders["A"]["valid"])
        self.assertEqual(data.orders["A"]["date"], date(2026, 1, 1))
        self.assertTrue(data.orders["B"]["valid"])
        self.assertTrue(all(line["valid"] is False for line in data.sales_lines if line["order_id"] == "A"))

    def test_no_order_identifier_preserves_identical_rows(self):
        self.csv("sales.csv", [
            ["Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền"],
            ["01/01/2026", "completed", "Synthetic tea", 1, 10],
            ["01/01/2026", "completed", "Synthetic tea", 1, 10],
        ])
        data = load_business(self.shop)
        self.assertEqual(len(data.sales_lines), 2)
        self.assertEqual(data.orders, {})

    def test_readme_semantics_and_explicit_unit_conversion(self):
        (self.shop / "README.md").write_text(
            "## Cột trong `sales.csv`\n"
            "- **When**: ngày bán\n- **Code**: mã đơn\n"
            "- **Outcome**: trạng thái đơn\n- **Goods**: tên hàng\n"
            "- **Count**: số lượng\n- **Costed**: thành tiền sau giảm\n"
            "- **Pack**: đơn vị tính\n"
            "## Quy ước\n- Synthetic tea: 1 box = 6 cups\n",
            encoding="utf-8",
        )
        self.csv("sales.csv", [["When", "Code", "Outcome", "Goods", "Count", "Costed", "Pack"],
                               ["01/01/2026", "A", "completed", "Synthetic tea", 2, 120, "box"]])
        data = load_business(self.shop)
        self.assertEqual(data.sales_lines[0]["base_qty"], 12)
        self.assertEqual(data.sales_lines[0]["base_unit"], "cups")
        self.assertEqual(data.orders["A"]["revenue"], 120)

    def test_legacy_csv_is_not_misdecoded_as_bomless_utf16(self):
        text = ("Ma don,Ngay ban,Trang thai,Ten hang,So luong,Thanh tien\n"
                "A,01/01/2026,completed,Café,1,10\n")
        for encoding in ("cp1252", "utf-16"):
            with self.subTest(encoding=encoding):
                raw = text.encode(encoding)
                if encoding == "cp1252" and len(raw) % 2:
                    raw += b"\n"
                (self.shop / "sales.csv").write_bytes(raw)
                data = load_business(self.shop)
                self.assertEqual(len(data.sales_lines), 1)
                self.assertEqual(data.sales_lines[0]["product_name"], "Café")
                self.assertEqual(data.orders["A"]["revenue"], 10)

    def test_conflicting_unit_conversions_preserve_unknown_quantity(self):
        self.csv("sales.csv", [["Mã đơn", "Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền", "Đơn vị tính"],
                               ["A", "01/01/2026", "completed", "Synthetic tea", 2, 120, "box"]])
        for second_factor, expected in ((12, None), (6, 12)):
            with self.subTest(second_factor=second_factor):
                (self.shop / "README.md").write_text(
                    "## Quy ước\n- Synthetic tea: 1 box = 6 cups\n"
                    f"- Synthetic tea: 1 box = {second_factor} cups\n", encoding="utf-8")
                data = load_business(self.shop)
                self.assertEqual(data.sales_lines[0]["base_qty"], expected)
                self.assertEqual(data.orders["A"]["revenue"], 120)
                if expected is None:
                    self.assertTrue(any("ambiguous unit conversion" in warning for warning in data.warnings))

    def test_unknown_status_remains_unknown(self):
        self.csv("sales.csv", [["Mã đơn", "Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền"],
                               ["A", "01/01/2026", "unrecognized status", "Synthetic tea", 1, 10]])
        self.assertIsNone(load_business(self.shop).sales_lines[0]["valid"])

    def test_note_default_needs_an_explicit_rule_clause(self):
        self.csv("sales.csv", [["Mã đơn", "Ngày bán", "Ghi chú", "Tên hàng", "Số lượng", "Thành tiền"],
                               ["A", "01/01/2026", "Synthetic note", "Synthetic tea", 1, 10]])
        (self.split / "rulebook.md").write_text(
            "Ghi chú là văn bản. Trạng thái có hoàn thành và huỷ.", encoding="utf-8")
        self.assertIsNone(load_business(self.shop).sales_lines[0]["valid"])
        (self.split / "rulebook.md").write_text(
            "Ghi chú không nhắc trạng thái là đơn hoàn thành.", encoding="utf-8")
        self.assertTrue(load_business(self.shop).sales_lines[0]["valid"])

    def test_unknown_date_is_preserved_and_flagged(self):
        self.csv("sales.csv", [["Mã đơn", "Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền"],
                               ["A", "not a date", "completed", "Synthetic tea", 1, 10]])
        data = load_business(self.shop)
        self.assertEqual(len(data.sales_lines), 1)
        self.assertIsNone(data.sales_lines[0]["date"])
        self.assertNotIn("sales_dates_complete", data.capabilities)
        self.assertTrue(data.warnings)

    def test_sqlite_read_only_join_and_line_revenue(self):
        path = self.shop / "shop.sqlite"
        connection = sqlite3.connect(path)
        connection.executescript(
            "CREATE TABLE don_hang(MaHoaDon TEXT, NgayLap TEXT, TinhTrang TEXT, TongTienHang INTEGER, TongThanhToan INTEGER);"
            "INSERT INTO don_hang VALUES('A','01/01/2026','completed',100,80);"
            "CREATE TABLE san_pham(MaHangHoa TEXT, TenGoi TEXT, DonViCoSo TEXT);"
            "INSERT INTO san_pham VALUES('P','Synthetic tea','cup');"
            "CREATE TABLE chi_tiet_don(MaHoaDon TEXT, MaHangHoa TEXT, SL INTEGER, TriGia INTEGER);"
            "INSERT INTO chi_tiet_don VALUES('A','P',2,100);"
        )
        connection.commit()
        connection.close()
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        data = load_business(self.shop)
        self.assertEqual(data.sales_lines[0]["product_name"], "Synthetic tea")
        self.assertEqual(data.orders["A"]["revenue"], 100)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    def test_xlsx_title_header_and_sheet_year(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl not installed")
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = "03.2025"
        sheet.append(["ORIGINAL SYNTHETIC TITLE"])
        sheet.append([])
        sheet.append(["Mã đơn", "Ngày bán", "Trạng thái", "Tên hàng", "Số lượng", "Thành tiền"])
        sheet.append(["A", "02/03", "completed", "Synthetic tea", 1, 10])
        sheet.append([None, None, None, "Synthetic cake", 1, 20])
        book.save(self.shop / "sales.xlsx")
        book.close()
        data = load_business(self.shop)
        self.assertEqual(len(data.sales_lines), 2)
        self.assertEqual(data.orders["A"]["date"], date(2025, 3, 2))
        self.assertEqual(data.orders["A"]["revenue"], 30)


if __name__ == "__main__":
    unittest.main()
