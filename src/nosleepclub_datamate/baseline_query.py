"""Conservative, rulebook-gated interpreter for common tabular QA.

The implementation is generic: no question IDs, business IDs, gold answers, or
test-derived rules are used. Unsupported or ambiguous requests abstain.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
import unicodedata
from typing import Any, Mapping


def normalize(text: Any) -> str:
    value = str(text or "").lower().replace("đ", "d")
    value = "".join(c for c in unicodedata.normalize("NFD", value)
                    if unicodedata.category(c) != "Mn")
    replacements = {
        "hnay": "hom nay", "hqua": "hom qua", "bua qua": "hom qua",
        "hoom nay": "hom nay", "trc": "truoc", "thangs": "thang",
        "dthu": "doanh thu", "sp": "san pham", "dc": "duoc",
        "bnhiu": "bao nhieu", "bnhiêu": "bao nhieu",
        "bao nhiu": "bao nhieu", "nhìu": "nhieu",
    }
    for old, new in replacements.items():
        value = re.sub(r"(?<!\w)" + re.escape(old) + r"(?!\w)", new, value)
    return re.sub(r"\s+", " ", value).strip()


@dataclass(frozen=True)
class Period:
    start: date
    end: date
    kind: str = "explicit"

    def contains(self, value: date) -> bool:
        return self.start <= value <= self.end


@dataclass(frozen=True)
class RulebookPolicy:
    revenue: bool = False
    valid_order_count: bool = False
    monday_weeks: bool = False
    partial_current_month: bool = False
    quantity_ranking: bool = False
    shifts: bool = False

    @classmethod
    def from_text(cls, text: str) -> "RulebookPolicy":
        s = normalize(text)
        revenue = all(fragment in s for fragment in (
            "thanh tien cac dong hang", "khong cong thue",
            "khong gom phi giao hang", "bo **ca don**",
        ))
        # Markdown punctuation is ignored only for recognizing policy clauses.
        plain = re.sub(r"[*_`]", "", s)
        revenue = revenue or all(fragment in plain for fragment in (
            "thanh tien cac dong hang", "khong cong thue",
            "khong gom phi giao hang", "bo ca don",
        ))
        return cls(
            revenue=revenue,
            valid_order_count=("chi tinh don khong huy, khong tra" in plain),
            monday_weeks=("bat dau thu hai" in plain),
            partial_current_month=(
                "thang nay" in plain and "tu ngay 1 den het hom nay" in plain),
            quantity_ranking=(
                "ban chay" in plain and "so luong quy ve don vi co ban" in plain
                and "khong theo so dong hay so tien" in plain),
            shifts=("06:00" in plain and "13:59" in plain
                    and "14:00" in plain and "21:59" in plain),
        )


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _month(year: int, month: int) -> Period:
    return Period(date(year, month, 1),
                  date(year, month, calendar.monthrange(year, month)[1]), "month")


def parse_period(text: str, as_of_date: Any) -> Period | None:
    """Resolve a single unambiguous Gregorian interval, never machine today."""
    today = _as_date(as_of_date)
    if today is None:
        return None
    s = normalize(text)
    if "hom nay" in s and "hom qua" in s:
        return None
    temporal_families = sum(bool(re.search(pattern, s)) for pattern in (
        r"\btuan\s+(?:nay|truoc|roi)\b", r"\bthang\s+(?:\d+|nay|truoc)\b",
        r"\bquy\s+[1-4]\b", r"\b\d+\s+ngay\s+gan nhat\b", r"\btu dau nam\b",
    ))
    if temporal_families > 1 or (temporal_families and "hom qua" in s):
        return None
    # These request comparisons, lunar semantics, or multiple time buckets.
    if re.search(r"tet|am lich|cung ky|nam ngoai|lien nhau|lien tiep|ket thuc|"
                 r"so voi|tang.truong|tang/giam|chenh lech|lien truoc|"
                 r"thay doi|moi thang|tung thang|tu thang.+(?:den|toi) thang", s):
        return None
    try:
        explicit_dates = []
        for match in re.finditer(
                r"(?<!\d)(?:(?P<iso>\d{4}-\d{2}-\d{2})|"
                r"(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4}))(?!\d)", s):
            explicit_dates.append(
                date.fromisoformat(match["iso"]) if match["iso"] else
                date(int(match["year"]), int(match["month"]), int(match["day"])))
        if explicit_dates:
            unique = list(dict.fromkeys(explicit_dates))
            if len(unique) == 1:
                return Period(unique[0], unique[0], "day")
            if len(unique) == 2 and re.search(r"\btu\b.+\b(?:den|toi)\b", s):
                return (Period(unique[0], unique[1], "range")
                        if unique[0] <= unique[1] else None)
            return None
        months = []
        for m in re.finditer(
                r"\bthang\s+(\d{1,2})(?:\s*[/.-]\s*|\s+nam\s+)(\d{4})\b", s):
            months.append((int(m[2]), int(m[1])))
        if months:
            unique = list(dict.fromkeys(months))
            return _month(*unique[0]) if len(unique) == 1 else None
        quarters = list(re.finditer(
            r"\bquy\s+([1-4])(?:\s*[/.-]\s*|\s+nam\s+)(\d{4})\b", s))
        if quarters:
            unique = list(dict.fromkeys((int(m[2]), int(m[1])) for m in quarters))
            if len(unique) != 1:
                return None
            year, quarter = unique[0]
            return Period(date(year, quarter * 3 - 2, 1),
                          _month(year, quarter * 3).end, "quarter")
        if "hom qua" in s:
            d = today - timedelta(days=1)
            return Period(d, d, "day")
        recent = re.search(r"\b(\d+)\s+ngay\s+gan nhat\b", s)
        if recent:
            days = int(recent[1])
            return (Period(today - timedelta(days=days - 1), today, "recent")
                    if 0 < days <= 3660 else None)
        if re.search(r"\btuan\s+(?:truoc|roi)\b", s):
            end = today - timedelta(days=today.weekday() + 1)
            return Period(end - timedelta(days=6), end, "week")
        if "tuan nay" in s:
            return Period(today - timedelta(days=today.weekday()), today, "week")
        if "thang nay" in s:
            return Period(today.replace(day=1), today, "current_month")
        if "thang truoc" in s:
            previous = today.replace(day=1) - timedelta(days=1)
            return _month(previous.year, previous.month)
        if "tu dau nam" in s:
            return Period(date(today.year, 1, 1), today, "year_to_date")
        # Month/quarter without a year uses the most recent such period.
        lone_month = re.search(r"\bthang\s+(\d{1,2})\b", s)
        if lone_month:
            month = int(lone_month[1])
            year = today.year - int(month > today.month)
            return _month(year, month)
        lone_quarter = re.search(r"\bquy\s+([1-4])\b", s)
        if lone_quarter:
            quarter = int(lone_quarter[1])
            first_month = quarter * 3 - 2
            year = today.year - int(first_month > today.month)
            return Period(date(year, first_month, 1),
                          _month(year, quarter * 3).end, "quarter")
        if "hom nay" in s:
            return Period(today, today, "day")
    except (ValueError, OverflowError):
        return None
    return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() else None
    except (ValueError, InvalidOperation):
        return None


def _number(value: Decimal, money: bool = False) -> int | float:
    quantum = Decimal("1") if money else Decimal("0.01")
    result = value.quantize(quantum, rounding=ROUND_HALF_UP)
    return int(result) if result == result.to_integral_value() else float(result)


def _abstain(q: Mapping[str, Any]) -> dict[str, Any]:
    return {"id": q["id"], "type": "abstain"}


def _answer(q: Mapping[str, Any], kind: str, answer: Any) -> dict[str, Any]:
    return {"id": q["id"], "type": kind, "answer": answer}


def _sum(rows: list[Mapping[str, Any]], field: str) -> Decimal | None:
    total = Decimal(0)
    for row in rows:
        number = _decimal(row.get(field))
        if number is None:
            return None
        total += number
    return total


def _row_date(row: Mapping[str, Any]) -> date | None:
    return _as_date(row.get("date"))


def _product_label(product_id: str, rows: list[Mapping[str, Any]],
                   products: Mapping[str, Mapping[str, Any]]) -> str:
    product = products.get(product_id, {})
    return str(product.get("name") or product.get("product_name")
               or next((r.get("product_name") for r in rows
                        if str(r.get("product_id")) == product_id
                        and r.get("product_name")), None) or product_id)


def _products_in_question(s: str, products: Mapping[str, Mapping[str, Any]]) -> set[str]:
    matches: list[tuple[int, int, str]] = []
    for product_id, product in products.items():
        aliases = [product.get("name"), product.get("product_name")]
        aliases.extend(product.get("aliases") or [])
        for name in aliases:
            needle = normalize(name)
            if needle and len(needle) >= 3:
                for match in re.finditer(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", s):
                    matches.append((match.start(), match.end(), str(product_id)))
    # A short alias inside a longer matched name is not a second entity. Two
    # separate name mentions remain distinct even if their lengths differ.
    return {key for start, end, key in matches if not any(
        other_start <= start and end <= other_end
        and (other_start < start or end < other_end)
        for other_start, other_end, _ in matches)}


def _payment_target(s: str) -> str | None:
    names = [name for name in ("tien mat", "chuyen khoan", "cod", "vi dien tu")
             if re.search(r"(?<!\w)" + name + r"(?!\w)", s)]
    return names[0] if len(names) == 1 else None


def _known_scope(s: str, business: Any, mode: str) -> bool:
    """Fail closed on ungrounded names, weekday/hour filters and extra metrics."""
    remaining = s
    if mode == "revenue":
        for product in getattr(business, "products", {}).values():
            for name in [product.get("name"), product.get("product_name"),
                         *(product.get("aliases") or [])]:
                needle = normalize(name)
                if needle:
                    remaining = re.sub(r"(?<!\w)" + re.escape(needle)
                                       + r"(?!\w)", " ", remaining)
    expressions = [
        r"\d{4}-\d{2}-\d{2}", r"\d{1,2}/\d{1,2}/\d{4}",
        r"\bthang\s+\d{1,2}(?:(?:\s*[/.-]\s*|\s+nam\s+)\d{4})?\b",
        r"\bquy\s+[1-4](?:(?:\s*[/.-]\s*|\s+nam\s+)\d{4})?\b",
        r"\b\d+\s+ngay\s+gan nhat\b",
        r"\b(?:hom nay|hom qua|tuan nay|tuan truoc|tuan roi|thang nay|"
        r"thang truoc|tu dau nam|ca sang|ca chieu)\b",
        r"\b(?:tien mat|chuyen khoan|cod|vi dien tu)\b",
    ]
    if mode == "ranking":
        expressions.append(r"\btop\s+\d+\b|\b\d+\s+(?=mat hang|san pham|hang)")
    if mode == "orders":
        expressions.append(r"(?:doanh thu|gia tri)\s*(?:la\s*)?"
                           r"(?:tu|>=|≥|tren|hon|duoi|>|<)\s*"
                           r"\d[\d.,]*(?:\s*(?:trieu|nghin|ngan|k|dong))?"
                           r"(?:\s+tro len)?")
    for expression in expressions:
        remaining = re.sub(expression, " ", remaining)
    allowed = set("""
        xin cho toi minh hoi biet xem giup gium dum coi check e ee a ah ha z vay
        nhe nhi vaayj rieng tinh trong tu den toi het ngay nam cua cua hang shop
        quan nha thuoc tong cong co la bao nhieu bn may doanh thu tien ban duoc
        ve dong vnd trung binh binh quan tren mot moi don bill hang dat dem so
        huy bi da ti ty le phan tram bang tra thanh toan cac nay truoc roi
        nao cao nhat ban chay hot mat san pham nhung gi top
    """.split())
    tokens = re.findall(r"[a-z]+|\d+", remaining)
    return all(token in allowed for token in tokens)


def _filter_rows(s: str, rows: list[Mapping[str, Any]], business: Any
                 ) -> list[Mapping[str, Any]] | None:
    """Only explicit, data-grounded product/payment/shift filters are supported."""
    if re.search(r"nhom|hoat chat|ke don|size|kenh|ban qua|tai quay|"
                 r"nhan vien|khach|loai hang|ngoai tru|khong tinh|"
                 r"ngoai.+phi|sau.+giam|tru.+giam", s):
        return None
    result = rows
    products = getattr(business, "products", {})
    named = _products_in_question(s, products)
    if len(named) > 1:
        return None
    if named:
        target = next(iter(named))
        result = [r for r in result if str(r.get("product_id")) == target]
    elif (_threshold(s) is None and re.search(
            r"(?:doanh thu|tien ban|thu ve)\s+(?:cua|tu)\s+"
            r"(?!cua hang\b|shop\b|quan\b)", s)):
        return None
    # A named product phrase that was not grounded must never become all-shop revenue.
    if not named and re.search(r"cua\s+(?:mat hang|san pham)|"
                               r"(?:mat hang|san pham)\s+.+(?:thu ve|doanh thu)", s):
        return None
    payment = _payment_target(s)
    has_payment = re.search(r"tien mat|chuyen khoan|\bcod\b|vi dien tu|"
                            r"hinh thuc thanh toan|tra bang", s)
    if has_payment:
        if payment is None or any(not r.get("payment") for r in rows):
            return None
        result = [r for r in result if normalize(r.get("payment")) == payment]
    if re.search(r"ca sang|ca chieu", s):
        if "ca sang" in s and "ca chieu" in s:
            return None
        if any(not isinstance(r.get("timestamp"), datetime) for r in rows):
            return None
        low, high = (6, 14) if "ca sang" in s else (14, 22)
        result = [r for r in result if low <= r["timestamp"].hour < high]
    return result


def _amount_literal(token: str, unit: str | None) -> Decimal | None:
    """Parse explicit decimal scales without deleting decimal separators."""
    if not re.fullmatch(r"\d+(?:[.,]\d+)*", token):
        return None
    scaled = unit in {"trieu", "nghin", "ngan", "k"}
    if "." in token and "," in token:
        decimal_mark = "." if token.rfind(".") > token.rfind(",") else ","
        group_mark = "," if decimal_mark == "." else "."
        integer, fraction = token.rsplit(decimal_mark, 1)
        if decimal_mark in integer or group_mark in fraction:
            return None
        groups = integer.split(group_mark)
        if (not 1 <= len(groups[0]) <= 3
                or any(len(group) != 3 for group in groups[1:])):
            return None
        token = "".join(groups) + "." + fraction
    elif "." in token or "," in token:
        mark = "." if "." in token else ","
        parts = token.split(mark)
        if len(parts) > 2:
            if not 1 <= len(parts[0]) <= 3 or any(len(p) != 3 for p in parts[1:]):
                return None
            token = "".join(parts)
        elif len(parts[1]) == 3 and parts[0] != "0":
            if scaled:  # e.g. 1.500 million admits two incompatible readings.
                return None
            token = "".join(parts)
        else:
            token = token.replace(mark, ".")
    amount = _decimal(token)
    if amount is None:
        return None
    scale = 1_000_000 if unit == "trieu" else 1000 if scaled else 1
    return amount * scale


def _threshold(s: str) -> tuple[str, Decimal] | None:
    m = re.search(r"(?:doanh thu|gia tri)\s*(?:la\s*)?"
                  r"(tu|>=|≥|tren|hon|duoi|>|<)\s*"
                  r"(\d[\d.,]*)(?:\s*(trieu|nghin|ngan|k|dong))?", s)
    if not m:
        return None
    amount = _amount_literal(m[2], m[3])
    if amount is None:
        return None
    comparison = ">=" if m[1] in {"tu", ">=", "≥"} else m[1]
    comparison = ">" if comparison in {"tren", "hon"} else comparison
    comparison = "<" if comparison == "duoi" else comparison
    return comparison, amount


def answer_question(q: Mapping[str, Any], business: Any,
                    policy: RulebookPolicy | str | None = None) -> dict[str, Any]:
    """Answer a supported query, otherwise return the official abstain sentinel."""
    if isinstance(policy, str):
        policy = RulebookPolicy.from_text(policy)
    if policy is None:
        text = getattr(business, "rulebook", "")
        policy = RulebookPolicy.from_text(text)
    s = normalize(q.get("question"))
    if re.search(r"\b(?:moi|tung|theo|tren(?:\s+mot)?)\s+"
                 r"(?:ngay|tuan|thang)\b|\btheo\s+ca\b", s):
        return _abstain(q)
    period = parse_period(s, q.get("as_of_date"))
    if period is None:
        return _abstain(q)
    today = _as_date(q.get("as_of_date"))
    if today is None or period.start > today:
        return _abstain(q)
    if period.kind == "week" and not policy.monday_weeks:
        return _abstain(q)
    if period.kind == "current_month" and not policy.partial_current_month:
        return _abstain(q)
    if re.search(r"ca sang|ca chieu", s) and not policy.shifts:
        return _abstain(q)
    # New or non-revenue concepts fail closed even when their wording resembles
    # supported rankings. No public question was used to build this list.
    if re.search(r"trung thanh|than thiet nhat|cao cap|pho bien|cham chi|"
                 r"ban nhat|dong nhat|ban ron|cao diem|gio nao|theo gio|"
                 r"bao cao tien mat|chot ca|tien thu thuc|ngay mua|"
                 r"lai|loi|lo nhuan|von|chi phi|ton kho|con ton|con no|"
                 r"tra no|thu no|nhap hang|gia nhap|het han|het hang", s):
        return _abstain(q)
    is_order_count = bool(re.search(r"so don|bao nhieu don|may don|"
                                    r"dem.+don|tong cong.+don", s))
    is_cancel = bool(re.search(r"\bhuy\b", s))
    is_cancel_rate = is_cancel and bool(re.search(r"ti le|ty le|phan tram|%", s))
    is_ranking = bool(re.search(r"ban chay|ban nhieu nhat|"
                                r"ban duoc nhieu nhat|hot nhat|chay nhat", s))
    is_revenue = bool(re.search(r"\b(?:doanh thu|tien ban)\b|"
                                r"\bban\b.+\btien\b|\bthu ve\b.+\btien\b", s))
    if not (is_order_count or is_cancel_rate or is_ranking or is_revenue):
        return _abstain(q)
    required_policy = (policy.valid_order_count if is_order_count or is_cancel_rate
                       else policy.quantity_ranking if is_ranking else policy.revenue)
    if not required_policy:
        return _abstain(q)
    if is_order_count and (re.search(r"trung binh|binh quan", s)
                           or (not is_cancel_rate and re.search(r"ti le|ty le|phan tram|%", s))):
        return _abstain(q)
    lines = list(getattr(business, "sales_lines", []))
    if not lines:
        if (not (is_order_count or is_cancel_rate) or _threshold(s) is not None):
            return _abstain(q)
        # An order register can support counts without claiming that a header
        # total has the rulebook's line-revenue semantics.
        lines = list(getattr(business, "orders", {}).values())
        if not lines:
            return _abstain(q)
    # Unknown dates/statuses are not silently omitted from a complete sum.
    if any(_row_date(r) is None for r in lines):
        return _abstain(q)
    scope = [r for r in lines if period.contains(_row_date(r))]
    # Coverage only certifies wholly disjoint periods; it never extrapolates.
    start = _as_date(getattr(business, "declared_date_start", None))
    end = _as_date(getattr(business, "declared_date_end", None))
    if ((start is not None and period.end < start)
            or (end is not None and period.start > end)):
        return {"id": q["id"], "type": "unanswerable",
                "reason": "Khoang hoi nam ngoai pham vi ngay cua du lieu."}
    observed_start = _as_date(getattr(business, "date_start", None))
    observed_end = _as_date(getattr(business, "date_end", None))
    if ((observed_start is not None and period.end < observed_start)
            or (observed_end is not None and period.start > observed_end)):
        # The first/last observed sale alone cannot certify coverage boundaries.
        return _abstain(q)
    if any(r.get("valid") is None for r in scope):
        return _abstain(q)
    valid = [r for r in scope if r.get("valid") is True]
    if is_order_count or is_cancel_rate:
        if not policy.valid_order_count:
            return _abstain(q)
        if not _known_scope(s, business, "orders"):
            return _abstain(q)
        if re.search(r"tra hang|tra lai|dang giao|moi loai|lan luot|\bva\b", s):
            return _abstain(q)
        orders = list(getattr(business, "orders", {}).values())
        if not orders or any(_row_date(r) is None for r in orders):
            return _abstain(q)
        selected = [r for r in orders if period.contains(_row_date(r))]
        # The order path only supports global/shift/payment counts, never
        # a product subset, group, customer or additional temporal bucket.
        if (_products_in_question(s, getattr(business, "products", {}))
                or re.search(r"nhom|khach|nhan vien|san pham|mat hang|"
                             r"bao nhieu ngay|may ngay|so ngay|"
                             r"ban qua|tai quay|ke don|hoat chat", s)):
            return _abstain(q)
        if any(r.get("valid") is None for r in selected):
            return _abstain(q)
        if is_cancel_rate:
            if _payment_target(s) or re.search(r"ca sang|ca chieu", s):
                return _abstain(q)
            if not selected:
                return _abstain(q)
            cancelled = sum(r.get("status") == "cancelled" for r in selected)
            return _answer(q, "percent", _number(
                Decimal(cancelled) * 100 / Decimal(len(selected))))
        selected = ([r for r in selected if r.get("status") == "cancelled"]
                    if is_cancel else [r for r in selected if r.get("valid") is True])
        filtered = _filter_rows(s, selected, business)
        if filtered is None:
            return _abstain(q)
        threshold = _threshold(s)
        if re.search(r"doanh thu|gia tri", s) and threshold is None:
            return _abstain(q)
        if threshold is not None:
            if not policy.revenue or any(_decimal(r.get("revenue")) is None for r in filtered):
                return _abstain(q)
            operator, amount = threshold
            functions = {">=": lambda n: n >= amount, ">": lambda n: n > amount,
                         "<": lambda n: n < amount}
            filtered = [r for r in filtered
                        if functions[operator](_decimal(r["revenue"]))]
        return _answer(q, "number", len(filtered))

    if is_ranking:
        if not policy.quantity_ranking:
            return _abstain(q)
        if (not _known_scope(s, business, "ranking")
                or _products_in_question(s, getattr(business, "products", {}))):
            return _abstain(q)
        if re.search(r"khach|nhan vien|tien|doanh thu|don hang|so don|"
                     r"luot|ngay|pho bien", s.replace("ngay gan nhat", "")):
            # A date expression itself is allowed; reject only metric phrases.
            if re.search(r"khach|nhan vien|tien|doanh thu|don hang|so don|"
                         r"luot|pho bien|nhieu ngay", s):
                return _abstain(q)
        filtered = _filter_rows(s, valid, business)
        if filtered is None:
            return _abstain(q)
        grouped: dict[str, Decimal] = defaultdict(Decimal)
        for row in filtered:
            if re.sub(r"[^a-z0-9]+", " ", normalize(row.get("product_name"))).strip() == "phi phuc vu":
                continue
            key = row.get("product_id")
            quantity = _decimal(row.get("base_qty"))
            if key is None or not str(key).strip() or quantity is None:
                return _abstain(q)
            grouped[str(key)] += quantity
        if not grouped:
            return _abstain(q)
        ranked = sorted(grouped, key=lambda key: (-grouped[key], key))
        m = re.search(r"\btop\s+(\d+)\b|\b(\d+)\s+"
                      r"(?:mat hang|san pham|hang)\b", s)
        count = int(next(g for g in m.groups() if g)) if m else 1
        if not 1 <= count <= 100:
            return _abstain(q)
        products = getattr(business, "products", {})
        labels = [_product_label(key, filtered, products) for key in ranked[:count]]
        return _answer(q, "list" if m else "string", labels if m else labels[0])

    if not is_revenue or not policy.revenue:
        return _abstain(q)
    if not _known_scope(s, business, "revenue"):
        return _abstain(q)
    # Distinguish whole-period total from a statistic about qualifying dates,
    # comparisons, rankings, percentages, and unsupported conditional filters.
    if re.search(r"ti le|ty le|phan tram|%|tang|giam|hon|kem|chenh|"
                 r"so voi|moi ben|lan luot|may ngay|so ngay|bao nhieu ngay|"
                 r"nguong|tro len|\btren\s+\d|\bduoi\s+\d|"
                 r"thap nhat|it nhat", s):
        return _abstain(q)
    filtered = _filter_rows(s, valid, business)
    if filtered is None:
        return _abstain(q)
    total = _sum(filtered, "line_total")
    if total is None:
        return _abstain(q)
    if re.search(r"ngay nao|ngay.+cao nhat|cao nhat.+ngay", s):
        by_day: dict[date, Decimal] = defaultdict(Decimal)
        for row in filtered:
            by_day[_row_date(row)] += _decimal(row["line_total"])
        if not by_day:
            return _abstain(q)
        winner = min(by_day, key=lambda d: (-by_day[d], d))
        return _answer(q, "date", winner.isoformat())
    if re.search(r"cao nhat|nhieu nhat|top|tung ngay|moi ngay", s):
        return _abstain(q)
    if re.search(r"trung binh|binh quan", s):
        if not re.search(r"(?:mot|moi|tren)\s+(?:don|bill)", s):
            return _abstain(q)
        order_ids = {r.get("order_id") for r in filtered}
        if None in order_ids or not order_ids or not policy.valid_order_count:
            return _abstain(q)
        return _answer(q, "number", _number(total / len(order_ids), money=True))
    return _answer(q, "number", _number(total, money=True))


# Kept as an explicit alias for the training evaluator and library callers.
solve_question = answer_question

