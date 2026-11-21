"""Bộ xử lý độ tươi nguyên liệu chính xác bằng số hữu tỉ (`Fraction`) cho Test Contract v1.2.

Đảm bảo:
  - Không trôi dấu phẩy động ở ngưỡng ươn `30` (`gather` trừ 0.5/60 = 1/120, `quan` trừ 0.25/60 = 1/240).
  - Phép `floor(giá_niêm_yết * trung_bình_fresh / 100)` chính xác tuyệt đối.
  - Chuẩn hóa đầu ra JSON (file kho & snapshot) khớp nhau từng chữ số và không bao giờ nhảy nhánh tại ngưỡng 30.
"""

from fractions import Fraction
import math

from .errors import BadInput
from .ids import sort_by_id

ITEM_KEYS = {"id", "kind", "fresh"}
DEFAULT_FRESHNESS = {
    "initial": 100,
    "gather_decay_per_s": 0.5,
    "quan_decay_per_s": 0.25,
    "spoiled_below": 30,
}


def get_freshness_cfg(tuning: dict) -> dict:
    cfg = tuning.get("freshness")
    if isinstance(cfg, dict):
        return cfg
    return DEFAULT_FRESHNESS


def to_fraction(val) -> Fraction:
    if isinstance(val, Fraction):
        return val
    if isinstance(val, int) and not isinstance(val, bool):
        return Fraction(val)
    if isinstance(val, float) and math.isfinite(val):
        return Fraction(str(val))
    raise BadInput(f"giá trị fresh không hợp lệ: {val!r}")


def format_fresh(fresh: Fraction, spoiled_below=30):
    """Chuyển `Fraction` sang số JSON (làm tròn 3 chữ số, số nguyên giữ gọn int) và bảo toàn nhánh `< spoiled_below`."""
    f = to_fraction(fresh)
    if f.denominator == 1:
        return int(f)
    thresh = to_fraction(spoiled_below)
    rounded = round(float(f), 3)
    if rounded == 0:
        return 0
    if f < thresh and rounded >= float(thresh):
        rounded = round(float(thresh) - 0.001, 3)
    return rounded


def make_item(item_id: str, kind: str, fresh=100) -> dict:
    return {"id": item_id, "kind": kind, "fresh": to_fraction(fresh)}


def parse_item(raw, allowed_kinds=None, label: str = "item") -> dict:
    if not isinstance(raw, dict):
        raise BadInput(f"{label} phải là object {{id, kind, fresh}}")
    if set(raw) != ITEM_KEYS:
        raise BadInput(f"{label} phải có đúng các khóa {sorted(ITEM_KEYS)}")
    ident = raw["id"]
    if not isinstance(ident, str) or not ident:
        raise BadInput(f"{label}.id phải là chuỗi khác rỗng")
    kind = raw["kind"]
    if not isinstance(kind, str) or not kind:
        raise BadInput(f"{label}.kind không hợp lệ: {kind!r}")
    if allowed_kinds is not None and kind not in allowed_kinds:
        raise BadInput(f"{label}.kind ngoài phạm vi nguyên liệu: {kind!r}")
    raw_f = raw["fresh"]
    if isinstance(raw_f, bool) or not isinstance(raw_f, (int, float, Fraction)):
        raise BadInput(f"{label}.fresh phải là số hữu hạn trong [0, 100]")
    if isinstance(raw_f, float) and not math.isfinite(raw_f):
        raise BadInput(f"{label}.fresh phải là số hữu hạn trong [0, 100]")
    fresh = to_fraction(raw_f)
    if fresh < 0 or fresh > 100:
        raise BadInput(f"{label}.fresh nằm ngoài [0, 100]: {raw_f!r}")
    return {"id": ident, "kind": kind, "fresh": fresh}


def parse_item_list(raw_list, allowed_kinds=None, label: str = "items") -> list:
    if not isinstance(raw_list, list):
        raise BadInput(f"{label} phải là mảng cá thể [{{id, kind, fresh}}]")
    seen = set()
    out = []
    for idx, raw in enumerate(raw_list):
        it = parse_item(raw, allowed_kinds=allowed_kinds, label=f"{label}[{idx}]")
        if it["id"] in seen:
            raise BadInput(f"{label}: trùng id cá thể {it['id']}")
        seen.add(it["id"])
        out.append(it)
    return out


def serialize_item(item: dict, spoiled_below=30) -> dict:
    return {
        "id": item["id"],
        "kind": item["kind"],
        "fresh": format_fresh(item["fresh"], spoiled_below=spoiled_below),
    }


def serialize_items_sorted(items: list, spoiled_below=30) -> list:
    return [serialize_item(it, spoiled_below=spoiled_below) for it in sort_by_id(items)]


def serialize_items_in_order(items: list, spoiled_below=30) -> list:
    return [serialize_item(it, spoiled_below=spoiled_below) for it in items]


def is_spoiled(item: dict, spoiled_below=30) -> bool:
    return to_fraction(item["fresh"]) < to_fraction(spoiled_below)


def decay_items(items: list, decay_per_s, spoiled_below, location: str, events: list):
    """Hao tươi toàn bộ cá thể trong `items` 1 tick (duyệt theo id).

    Phát `spoiled` đúng 1 lần khi đi từ `>= spoiled_below` xuống `< spoiled_below` (so trước làm tròn).
    """
    step_decay = to_fraction(decay_per_s) / 60
    thresh = to_fraction(spoiled_below)
    for it in sort_by_id(items):
        before = to_fraction(it["fresh"])
        after = before - step_decay
        if after < 0:
            after = Fraction(0)
        it["fresh"] = after
        if before >= thresh and after < thresh:
            events.append(("spoiled", {"item_id": it["id"], "kind": it["kind"], "location": location}))


def compute_fresh_price(list_price: int, used_items: list) -> int:
    """Chốt giá = floor(giá_niêm_yết × trung_bình_fresh / 100) chính xác bằng số hữu tỉ."""
    if not used_items:
        return int(list_price)
    total_fresh = sum((to_fraction(it["fresh"]) for it in used_items), Fraction(0))
    exact = (Fraction(int(list_price)) * total_fresh) / (Fraction(100) * Fraction(len(used_items)))
    return math.floor(exact)
