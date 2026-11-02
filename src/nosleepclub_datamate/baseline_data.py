"""Conservative, model-free business-file ingestion for a first runnable baseline.

Column meanings come from each input README and generic column aliases. No
question identifiers or business identifiers determine parsing or answers. Raw
tables stay available, and unknown values remain None. This is not a full ETL
system: ambiguous joins and unsupported layouts are reported, never completed by
inventing business facts.
"""

from __future__ import annotations

import csv
import io
import math
import re
import sqlite3
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any


def norm(value: Any) -> str:
    """ASCII, case-insensitive words for column/rule matching, not entity IDs."""
    text = unicodedata.normalize("NFKD", str(value or "").replace("Đ", "D").replace("đ", "d"))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _compact(value: Any) -> str:
    return norm(value).replace(" ", "")


def _entity_key(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or "")).casefold()
    return "".join(c for c in text if c.isalnum())


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    result = str(value).strip()
    return result or None


def parse_number(value: Any) -> float | None:
    """Read common Vietnamese/English numeric notation, preserving unknowns."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    text = str(value).strip().replace("\u00a0", " ").replace("−", "-")
    if not text or norm(text) in {"na", "null", "none", "nan", "inf", "infinity"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    match = re.match(r"^[+-]?\d[\d., ]*", text)
    if not match:
        return None
    token = match.group().strip().replace(" ", "")
    suffix = norm(text[match.end():])
    scale = 1_000_000 if suffix in {"tr", "trieu", "million"} else 1_000 if suffix == "k" else 1
    if "," in token and "." in token:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        token = token.replace(thousands, "").replace(decimal, ".")
    elif "," in token or "." in token:
        separator = "," if "," in token else "."
        pieces = token.split(separator)
        if len(pieces) > 2 and all(len(piece) == 3 for piece in pieces[1:]):
            token = "".join(pieces)
        elif len(pieces) == 2 and len(pieces[1]) == 3 and pieces[0].lstrip("+-") != "0" and scale == 1:
            token = "".join(pieces)
        elif len(pieces) == 2:
            token = token.replace(separator, ".")
        else:
            return None
    try:
        number = float(token) * scale
    except ValueError:
        return None
    return (-number if negative else number) if math.isfinite(number) else None


def parse_datetime(value: Any, *, year: int | None = None, on_date: date | None = None) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime.combine(value, time())
    if isinstance(value, time):
        return datetime.combine(on_date, value) if on_date else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 20_000 <= value <= 90_000:
            return datetime(1899, 12, 30) + timedelta(days=float(value))
        if on_date and 0 <= value < 1:
            return datetime.combine(on_date, time()) + timedelta(days=float(value))
        return None
    text = _text(value)
    if not text:
        return None
    if re.fullmatch(r"\d{5}(?:\.\d+)?", text):
        return parse_datetime(float(text), year=year, on_date=on_date)
    words = norm(text)
    vietnamese = re.fullmatch(r"(?:ngay )?(\d{1,2}) (?:thg|thang) (\d{1,2})(?: (?:nam )?(\d{4}))?", words)
    if vietnamese:
        day, month, stated_year = vietnamese.groups()
        if stated_year or year:
            try:
                return datetime(int(stated_year or year), int(month), int(day))
            except ValueError:
                return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M:%S",
                    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, pattern)
        except ValueError:
            pass
    short = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})", text)
    if short and year:
        try:
            return datetime(year, int(short[2]), int(short[1]))
        except ValueError:
            return None
    if on_date:
        for pattern in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.combine(on_date, datetime.strptime(text, pattern).time())
            except ValueError:
                pass
    return None


def parse_date(value: Any, *, year: int | None = None) -> date | None:
    parsed = parse_datetime(value, year=year)
    return parsed.date() if parsed else None


def normalize_status(value: Any) -> str:
    text = norm(value)
    if not text:
        return "unknown"
    if re.search(r"\b(huy|cancelled|canceled|cancel|void|khong giao duoc|bo don)\b", text):
        return "cancelled"
    if re.search(r"\b(tra hang|doi tra|hoan tra|tra lai|tra ve|returned|return|refund|partial return|tra mot phan)\b", text):
        return "returned"
    if text in {"tra", "doi", "hoan"}:
        return "returned"
    if re.search(r"\b(dang giao|dang van chuyen|shipping|delivering|in transit|processing|dang xu ly)\b", text):
        return "shipping"
    if re.search(r"\b(hoan thanh|hoan tat|da giao|da lay|da nhan|xong|ok|completed|complete|done|success|finished|thanh cong)\b", text):
        return "sold"
    return "unknown"


@dataclass
class DataTable:
    name: str
    source_file: str
    sheet: str | None
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    field_map: dict[str, str] = field(default_factory=dict)
    kind: str = "other"
    row_numbers: list[int] = field(default_factory=list)


@dataclass
class BusinessData:
    root: Path
    readme: str
    tables: list[DataTable] = field(default_factory=list)
    sales_lines: list[dict[str, Any]] = field(default_factory=list)
    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    customers: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    capabilities: set[str] = field(default_factory=set)
    date_start: date | None = None
    date_end: date | None = None
    declared_date_start: date | None = None
    declared_date_end: date | None = None
    rulebook: str = ""

    @property
    def lines(self) -> list[dict[str, Any]]:
        return self.sales_lines


_ALIASES = {
    "order_id": ["mã hóa đơn", "mã đơn", "mã đơn hàng", "MaHoaDon", "MaDonHang", "order id", "Mã phiếu", "Số phiếu", "Mã bill", "Số hóa đơn", "Số CT"],
    "date": ["ngày bán", "ngày đặt hàng", "ngày tháng", "ngày lập", "NgayLap", "NgayDat", "ngày giao dịch", "ngày", "date", "Thời gian"],
    "timestamp": ["ThoiGianLap", "thời gian tạo", "thời điểm đặt đơn", "ngày giờ tạo", "giờ", "created at"],
    "status": ["trạng thái", "trạng thái đơn hàng", "trạng thái đơn", "tình trạng", "TinhTrang", "Status", "Kết quả", "Ghi chú TT"],
    "product_id": ["mã hàng", "mã hàng hóa", "MaHangHoa", "mã SKU", "MaSP", "product id", "mã sản phẩm", "mã mặt hàng"],
    "product_name": ["tên hàng", "tên hàng hóa", "tên sản phẩm", "TenSP", "ten_hang", "Hàng", "Hàng bán", "Nội dung", "Product", "Tên món", "TenGoi"],
    "quantity": ["số lượng", "SoLuong", "SL", "so_luong", "số lượng sản phẩm", "số lượng hàng", "số lượng bán", "SL bán", "quantity", "S.L"],
    "base_qty": ["SLQuyDoi", "số lượng quy đổi", "số lượng lẻ", "SL lẻ", "Quy ra ĐV lẻ", "base quantity"],
    "unit": ["đơn vị tính", "DonViTinh", "ĐVT", "DVT", "DonVi", "Unit", "đơn vị", "Đơn vị (tính)"],
    "base_unit": ["đơn vị cơ bản", "DonViCoSo", "đơn vị gốc", "ĐV nhỏ", "ĐV gốc"],
    "large_unit": ["đơn vị quy đổi", "ĐV lớn", "ĐV nhập"],
    "factor": ["hệ số", "HeSoQuyDoi", "hệ số QĐ", "tỉ lệ quy đổi", "quy đổi"],
    "line_total": ["thành tiền", "ThanhTien", "TriGia", "Trị giá", "Amount", "Tiền bán", "Thành tiền (đ)"],
    "unit_price": ["đơn giá", "DonGia", "GiaDonVi", "giá sản phẩm", "Giá 1 đv", "Price", "Giá lẻ"],
    "cost": ["giá vốn lúc bán", "GiaVonLucBan", "Giá vốn", "GiaVonHang"],
    "order_revenue": ["TongTienHang", "Tổng tiền hàng", "Tiền hàng"],
    "order_total": ["TongThanhToan", "Tổng sau giảm giá", "Tổng đơn", "Tổng bill", "Phải thu"],
    "discount": ["giảm giá", "ChietKhau", "discount"],
    "customer_id": ["mã khách hàng", "MaKhachHang", "Mã KH", "Customer ID", "mã khách", "mã khách mua"],
    "customer_name": ["Tên khách hàng", "TênKH", "TenKH", "khách hàng", "khách", "Đối tác", "Bên mua"],
    "group": ["nhóm hàng", "Nhóm hàng(3 Cấp)", "DanhMuc", "nhóm hàng hóa", "nhóm khách hàng", "LoaiKhachHang", "nhóm khách", "loại sản phẩm"],
    "employee": ["người bán", "nhân viên", "mã nhân viên", "MaNhanVien", "nhân viên bán"],
    "payment": ["hình thức thanh toán", "phương thức thanh toán", "PhuongThucTT", "HTTT", "PTTT", "Trả bằng"],
    "channel": ["kênh bán", "KenhBanHang", "loại bán"],
    "row_no": ["STT", "SoThuTu", "số thứ tự", "No.", "TT dòng"],
    "return_qty": ["SLTraQuyDoi", "số lượng trả", "SL trả"],
    "note": ["ghi chú", "DienGiai", "ghi chu", "note"],
}
_ALIAS_LOOKUP = {_compact(alias): key for key, aliases in _ALIASES.items() for alias in aliases}


def _description_field(description: str, context: str) -> str | None:
    desc = norm(description)
    if "cot trong" in desc or "khong co du lieu" in desc:
        return None
    if desc.startswith("ma don") and "nhap" not in desc:
        return "order_id"
    if desc.startswith("ma hang"):
        return "product_id"
    if desc.startswith("ma khach"):
        return "customer_id"
    if desc.startswith("ma nhan vien"):
        return "employee"
    if desc.startswith("ngay ban"):
        return "date"
    if desc.startswith("thoi diem dat") or desc.startswith("gio dat"):
        return "timestamp"
    if desc.startswith("trang thai don"):
        return "status"
    if desc.startswith("so luong da doi"):
        return "base_qty"
    if desc.startswith("so luong khach tra"):
        return "return_qty"
    if desc == "so luong":
        return "quantity"
    if desc.startswith("so thu tu dong trong don"):
        return "row_no"
    if desc.startswith("thanh tien sau giam"):
        return "line_total"
    if desc.startswith("tien hang cua don") or desc.startswith("tong tien hang cua don"):
        return "order_revenue"
    if desc.startswith("tong tien don") or desc.startswith("so khach phai tra cho ca don"):
        return "order_total"
    if desc.startswith("ten khach"):
        return "customer_name"
    if desc.startswith("ten hang"):
        return "product_name"
    if desc == "ten":
        return "customer_name" if "khach" in context else "product_name"
    if desc.startswith("don vi co ban"):
        return "base_unit"
    if desc.startswith("don vi lon"):
        return "large_unit"
    if desc.startswith("he so"):
        return "factor"
    if desc == "don vi tinh":
        return "unit"
    if desc == "don gia":
        return "unit_price"
    if desc == "gia von":
        return "cost"
    if desc in {"nhom hang", "nhom khach"}:
        return "group"
    if desc.startswith("hinh thuc thanh toan"):
        return "payment"
    if desc == "kenh ban":
        return "channel"
    if desc == "ghi chu":
        return "note"
    return None


def _repair_name(value: str) -> str:
    try:
        return value.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _readme_maps(readme: str) -> dict[tuple[str, str], dict[str, str | None]]:
    result: dict[tuple[str, str], dict[str, str | None]] = {}
    target: dict[str, str | None] | None = None
    context = ""
    for line in readme.splitlines():
        if line.startswith("##"):
            target = None
            quoted = re.findall(r"`([^`]+)`", line)
            if norm(line).startswith("cot trong") or "cot trong" in norm(line):
                if quoted:
                    filename = _compact(Path(quoted[0]).name)
                    sheet = _compact(quoted[1]) if len(quoted) > 1 else ""
                    context = norm(" ".join(quoted))
                    target = result.setdefault((filename, sheet), {})
        elif target is not None:
            match = re.match(r"\s*-\s+\*\*(.+?)\*\*:\s*(.+)", line)
            if match:
                target[_compact(match[1])] = _description_field(match[2], context)
    return result


def _field_map(columns: tuple[str, ...], filename: str, sheet: str | None,
               descriptions: dict[tuple[str, str], dict[str, str | None]]) -> dict[str, str]:
    source = _compact(_repair_name(filename))
    sheet_key = _compact(sheet or "")
    documented = descriptions.get((source, sheet_key), descriptions.get((source, ""), {}))
    result: dict[str, str] = {}
    for column in columns:
        key = _compact(column)
        canonical = documented.get(key) if key in documented else _ALIAS_LOOKUP.get(key)
        if canonical:
            result.setdefault(canonical, column)
    context = norm((_repair_name(filename) + " " + (sheet or "")))
    if "khach" in context and "order_id" not in result:
        for column in columns:
            if _compact(column) in {"ten", "tengoi", "kh", "khachhangten"}:
                result["customer_name"] = column
                if result.get("product_name") == column:
                    result.pop("product_name")
    return result


def _kind(table: DataTable) -> str:
    fields = set(table.field_map)
    context = _compact(_repair_name(table.source_file) + " " + (table.sheet or table.name))
    if "factor" in fields:
        return "conversion"
    if "trahang" in context or "return_qty" in fields:
        return "returns"
    if any(word in context for word in ("nhaphang", "phieunhap", "chitietnhap", "donnhap", "sogiaohang", "phieugiaohang", "thekho", "lichsugia", "banggia", "chiph", "sothuoc", "chinhanh", "nhanvien", "nhacungcap", "lohang", "thongtinthuoc")):
        return "other"
    if "quantity" in fields and "line_total" in fields and ("product_id" in fields or "product_name" in fields) and ("date" in fields or "order_id" in fields):
        return "sales"
    if "customer_id" in fields and "customer_name" in fields and "order_id" not in fields:
        return "customers"
    if ("product_id" in fields or "product_name" in fields) and "order_id" not in fields and "date" not in fields and "quantity" not in fields:
        return "products"
    if "order_id" in fields and "date" in fields and "status" in fields:
        return "orders"
    return "other"


def _from_grid(name: str, source: str, sheet: str | None, grid: list[tuple[int, tuple[Any, ...]]],
               descriptions: dict[tuple[str, str], dict[str, str | None]]) -> DataTable | None:
    if not grid:
        return None
    candidates = []
    for offset, (_, values) in enumerate(grid[:30]):
        strings = tuple(_text(value) or "" for value in values)
        mapped = _field_map(strings, source, sheet, descriptions)
        count = sum(bool(value) for value in strings)
        score = 10 * len(mapped) + count
        candidates.append((score, -offset, offset))
    offset = max(candidates)[2]
    values = grid[offset][1]
    used: dict[str, int] = defaultdict(int)
    columns = []
    for index, value in enumerate(values):
        column = _text(value) or f"_column_{index + 1}"
        used[column] += 1
        columns.append(column if used[column] == 1 else f"{column}__{used[column]}")
    cols = tuple(columns)
    rows, row_numbers = [], []
    for row_number, values in grid[offset + 1:]:
        if not any(value is not None and _text(value) for value in values):
            continue
        row = {column: values[index] if index < len(values) else None for index, column in enumerate(cols)}
        if sum(_compact(row[column]) == _compact(column) for column in cols) >= max(2, len(cols) * 0.6):
            continue
        rows.append(row)
        row_numbers.append(row_number)
    table = DataTable(name, source, sheet, cols, rows, _field_map(cols, source, sheet, descriptions), row_numbers=row_numbers)
    table.kind = _kind(table)
    return table


def _load_tables(root: Path, descriptions: dict, warnings: list[str]) -> list[DataTable]:
    tables = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        suffix = path.suffix.casefold()
        if suffix == ".csv":
            raw = path.read_bytes()
            text = None
            for encoding in ("utf-8-sig", "utf-16", "cp1258", "cp1252"):
                try:
                    text = raw.decode(encoding)
                    break
                except UnicodeError:
                    pass
            if text is None:
                warnings.append(f"unreadable encoding: {path.name}")
                continue
            try:
                dialect = csv.Sniffer().sniff(text[:20000], delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            grid = [(i, tuple(row)) for i, row in enumerate(csv.reader(io.StringIO(text), dialect), 1)]
            table = _from_grid(path.stem, path.name, None, grid, descriptions)
            if table:
                tables.append(table)
        elif suffix == ".xlsx":
            try:
                import openpyxl
            except ImportError as exc:
                raise RuntimeError("XLSX input requires openpyxl>=3.1.5") from exc
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            try:
                for worksheet in workbook.worksheets:
                    grid = [(i, tuple(row)) for i, row in enumerate(worksheet.iter_rows(values_only=True), 1)]
                    table = _from_grid(f"{path.stem}/{worksheet.title}", path.name, worksheet.title, grid, descriptions)
                    if table:
                        tables.append(table)
            finally:
                workbook.close()
        elif suffix in {".sqlite", ".sqlite3", ".db"}:
            connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            try:
                names = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
                for (name,) in names:
                    quoted = '"' + name.replace('"', '""') + '"'
                    cursor = connection.execute("SELECT * FROM " + quoted)
                    columns = tuple(column[0] for column in cursor.description)
                    rows = [dict(zip(columns, row)) for row in cursor]
                    table = DataTable(name, path.name, name, columns, rows,
                                      _field_map(columns, name, name, descriptions), row_numbers=list(range(1, len(rows) + 1)))
                    table.kind = _kind(table)
                    tables.append(table)
            finally:
                connection.close()
    return tables


def _canonical_rows(table: DataTable):
    """Forward-fill only order metadata, resetting whenever the order changes."""
    carry: dict[str, Any] = {}
    metadata = {"order_id", "date", "timestamp", "status", "customer_id", "customer_name", "employee", "payment", "channel", "note"}
    previous_order = None
    for index, raw in enumerate(table.rows):
        row = {field: raw.get(column) for field, column in table.field_map.items()}
        first = next((_text(value) for value in raw.values() if _text(value)), "")
        if norm(first) in {"tong", "tong cong", "cong", "subtotal", "total"} or norm(first).startswith("tong cong "):
            carry = {}
            previous_order = None
            continue
        order_id = _text(row.get("order_id"))
        if order_id and order_id != previous_order:
            carry = {}
            previous_order = order_id
        if table.kind == "sales" and "order_id" in table.field_map:
            for field in metadata:
                if _text(row.get(field)) is None and field in carry:
                    row[field] = carry[field]
                elif _text(row.get(field)) is not None:
                    carry[field] = row[field]
        row["provenance"] = f"{table.source_file}:{table.sheet or ''}:{table.row_numbers[index] if table.row_numbers else index + 2}"
        row["_raw_key"] = tuple((key, repr(value)) for key, value in sorted(raw.items()))
        yield row


def _sheet_year(sheet: str | None) -> int | None:
    years = re.findall(r"(?:19|20)\d{2}", sheet or "")
    return int(years[-1]) if years else None


def _put_entity(destination: dict, key: str, row: dict, name_field: str) -> dict:
    entry = destination.setdefault(key, {"id": key, "name": None, "group": None, "base_unit": None, "aliases": []})
    name = _text(row.get(name_field))
    if name:
        if not entry["name"]:
            entry["name"] = name
        if name not in entry["aliases"]:
            entry["aliases"].append(name)
    for field in ("group", "base_unit"):
        value = _text(row.get(field))
        if value:
            entry[field] = value
    entry[name_field] = entry["name"]
    return entry


def _anonymous_customer(value: Any) -> bool:
    return norm(value) in {"", "khach le", "le", "vang lai", "khach vang lai", "walk in", "guest"}


def load_business(root: Path) -> BusinessData:
    """Load only the supplied business directory; never open question/answer files."""
    root = Path(root)
    readme_path = next((p for p in root.iterdir() if p.name.casefold() == "readme.md"), None)
    readme = readme_path.read_text(encoding="utf-8-sig") if readme_path else ""
    result = BusinessData(root=root, readme=readme)
    rule_path = root.parent.parent / "rulebook.md"
    if rule_path.is_file():
        result.rulebook = rule_path.read_text(encoding="utf-8-sig")
    coverage = re.search(r"(?:có đến hết|co den het)\s+(\d{1,2}/\d{1,2}/\d{4})", readme, re.I)
    if coverage:
        result.declared_date_end = parse_date(coverage[1])
    descriptions = _readme_maps(readme)
    result.tables = _load_tables(root, descriptions, result.warnings)
    conversions: dict[tuple[str, str], tuple[float, str | None]] = {}
    for name, unit, factor, base in re.findall(r"^\s*-\s+(.+?):\s*1\s+(.+?)\s*=\s*([\d.,]+)\s+(.+?)\s*$", readme, re.M):
        number = parse_number(factor)
        if number and number > 0:
            conversions[(_entity_key(name), _entity_key(unit))] = (number, base.strip())
    return_orders: set[str] = set()
    raw_sales: list[tuple[DataTable, dict[str, Any]]] = []
    for table in result.tables:
        for row in _canonical_rows(table):
            oid = _text(row.get("order_id"))
            if table.kind == "products":
                key = _text(row.get("product_id")) or "name:" + _entity_key(row.get("product_name"))
                if key != "name:":
                    if "base_unit" not in row and "unit" in row:
                        row["base_unit"] = row["unit"]
                    _put_entity(result.products, key, row, "product_name")
            elif table.kind == "customers":
                key = _text(row.get("customer_id"))
                if key:
                    _put_entity(result.customers, key, row, "customer_name")
            elif table.kind == "conversion":
                key = _text(row.get("product_id")) or _text(row.get("product_name"))
                unit = _text(row.get("large_unit")) or _text(row.get("unit"))
                factor = parse_number(row.get("factor"))
                if key and unit and factor and factor > 0:
                    conversions[(_entity_key(key), _entity_key(unit))] = (factor, _text(row.get("base_unit")))
            elif table.kind == "returns":
                qty = parse_number(row.get("return_qty"))
                if oid and ("return_qty" not in table.field_map or (qty is not None and qty > 0)):
                    return_orders.add(oid)
            elif table.kind == "orders" and oid:
                order = dict(row)
                order["order_id"] = oid
                order["date"] = parse_date(row.get("date"), year=_sheet_year(table.sheet))
                order["timestamp"] = parse_datetime(row.get("timestamp"), year=_sheet_year(table.sheet), on_date=order["date"])
                order["status"] = normalize_status(row.get("status"))
                order["revenue"] = parse_number(row.get("order_revenue"))
                order.pop("_raw_key", None)
                if oid in result.orders:
                    old = result.orders[oid]
                    if any(old.get(field) != order.get(field) for field in ("date", "status", "revenue")):
                        result.warnings.append("conflicting order header; affected order marked uncertain")
                        old["status"] = "unknown"
                        old["revenue"] = None
                else:
                    result.orders[oid] = order
            elif table.kind == "sales":
                raw_sales.append((table, row))
    product_names: dict[str, list[str]] = defaultdict(list)
    for key, product in result.products.items():
        for alias in product["aliases"]:
            name_key = _entity_key(alias)
            if key not in product_names[name_key]:
                product_names[name_key].append(key)
    seen_lines = set()
    note_rules = norm(result.rulebook + "\n" + readme)
    notes_default_sold = "ghi chu khong nhac trang thai la don hoan thanh" in note_rules
    for table, row in raw_sales:
        oid = _text(row.get("order_id"))
        if oid:
            fingerprint = (oid, row["_raw_key"])
            if fingerprint in seen_lines:
                continue
            seen_lines.add(fingerprint)
        product_id = _text(row.get("product_id"))
        name = _text(row.get("product_name"))
        if not product_id and name and len(product_names.get(_entity_key(name), [])) == 1:
            product_id = product_names[_entity_key(name)][0]
        key = product_id or "name:" + _entity_key(name)
        product = result.products.get(key, {})
        name = name or product.get("name")
        if not name and not product_id:
            continue
        parent = result.orders.get(oid, {})
        line_date = parse_date(row.get("date"), year=_sheet_year(table.sheet))
        line_date = parent.get("date") or line_date
        timestamp = parent.get("timestamp") or parse_datetime(row.get("timestamp"), year=_sheet_year(table.sheet), on_date=line_date)
        status = parent.get("status") or normalize_status(row.get("status"))
        if status == "unknown" and "status" not in table.field_map and "note" in table.field_map:
            status = normalize_status(row.get("note"))
            if status == "unknown" and notes_default_sold:
                status = "sold"
        quantity = parse_number(row.get("quantity"))
        base_qty = parse_number(row.get("base_qty"))
        unit = _text(row.get("unit"))
        base_unit = product.get("base_unit")
        conversion = conversions.get((_entity_key(product_id), _entity_key(unit))) or conversions.get((_entity_key(name), _entity_key(unit)))
        if conversion:
            factor, declared_base = conversion
            base_unit = declared_base or base_unit
            if base_qty is None and quantity is not None:
                base_qty = quantity * factor
        elif unit and (not base_unit or _entity_key(unit) == _entity_key(base_unit)):
            # The supplied default rule makes an unlisted unit a base unit.
            base_unit = base_unit or unit
            if base_qty is None:
                base_qty = quantity
        line = {
            "order_id": oid, "date": line_date, "timestamp": timestamp,
            "status": status, "valid": None,
            "product_id": product_id, "product_name": name,
            "quantity": quantity, "base_qty": base_qty, "unit": unit, "base_unit": base_unit,
            "line_total": parse_number(row.get("line_total")),
            "unit_price": parse_number(row.get("unit_price")), "cost": parse_number(row.get("cost")),
            "group": product.get("group"), "provenance": row["provenance"],
        }
        for field in ("customer_id", "customer_name", "employee", "payment", "channel"):
            line[field] = _text(parent.get(field)) or _text(row.get(field))
        customer = result.customers.get(line["customer_id"], {})
        line["customer_name"] = line["customer_name"] or customer.get("name")
        line["customer_group"] = customer.get("group")
        if _anonymous_customer(line["customer_name"]) and not line["customer_id"]:
            line["customer_name"] = None
        if quantity is not None and quantity < 0 and oid:
            return_orders.add(oid)
        if status == "returned" and oid:
            return_orders.add(oid)
        if key != "name:" and not product:
            product = _put_entity(result.products, key, {"product_name": name, "base_unit": base_unit}, "product_name")
        result.sales_lines.append(line)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in result.sales_lines:
        if line["order_id"]:
            grouped[line["order_id"]].append(line)
    for oid, lines in grouped.items():
        order = result.orders.setdefault(oid, {"order_id": oid})
        dates = [line["date"] for line in lines if line["date"] and line["status"] != "returned" and (line["quantity"] or 0) >= 0]
        if not order.get("date"):
            order["date"] = min(dates) if dates else next((line["date"] for line in lines if line["date"]), None)
        statuses = {line["status"] for line in lines} - {"unknown"}
        if oid in return_orders:
            order["status"] = "returned"
        elif "cancelled" in statuses:
            order["status"] = "cancelled"
        elif len(statuses) == 1:
            order["status"] = next(iter(statuses))
        elif len(statuses) > 1:
            order["status"] = "unknown"
        else:
            order.setdefault("status", "unknown")
        amounts = [line["line_total"] for line in lines]
        order["revenue"] = math.fsum(amounts) if all(value is not None for value in amounts) else None
        for field in ("timestamp", "customer_id", "customer_name", "customer_group", "employee", "payment", "channel"):
            if not order.get(field):
                values = [line.get(field) for line in lines if line.get(field) is not None]
                order[field] = values[0] if values and all(value == values[0] for value in values) else None
    for oid, order in result.orders.items():
        if oid in return_orders:
            order["status"] = "returned"
        order["valid"] = True if order.get("status") in {"sold", "shipping"} else False if order.get("status") in {"cancelled", "returned"} else None
        customer = result.customers.get(_text(order.get("customer_id")), {})
        order["customer_name"] = _text(order.get("customer_name")) or customer.get("name")
        order["customer_group"] = customer.get("group")
    for line in result.sales_lines:
        if line["order_id"] in result.orders:
            order = result.orders[line["order_id"]]
            line["date"], line["status"], line["valid"] = order.get("date"), order["status"], order["valid"]
        else:
            line["valid"] = True if line["status"] in {"sold", "shipping"} else False if line["status"] in {"cancelled", "returned"} else None
    dates = [row["date"] for row in list(result.orders.values()) + result.sales_lines if row.get("date")]
    result.date_start = min(dates) if dates else None
    result.date_end = result.declared_date_end or (max(dates) if dates else None)
    if result.sales_lines:
        result.capabilities.add("sales")
        if all(line.get("date") is not None for line in result.sales_lines):
            result.capabilities.add("sales_dates_complete")
        else:
            result.warnings.append("some sales dates could not be parsed; period totals require abstention")
    if result.orders:
        result.capabilities.add("order_ids")
        if all(order.get("date") is not None for order in result.orders.values()):
            result.capabilities.add("orders_dates_complete")
        if any(order.get("revenue") is not None for order in result.orders.values()):
            result.capabilities.add("sale_revenue")
    for field, capability in (("quantity", "sale_quantity"), ("base_qty", "base_quantity"), ("line_total", "sale_revenue"), ("product_name", "product_names"), ("customer_id", "customer_ids"), ("customer_group", "customer_groups"), ("employee", "employee"), ("payment", "payment"), ("channel", "channel")):
        if any(line.get(field) is not None for line in result.sales_lines):
            result.capabilities.add(capability)
    return result
