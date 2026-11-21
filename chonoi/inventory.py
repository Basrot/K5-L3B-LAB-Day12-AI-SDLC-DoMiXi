"""File kho v1.2 (Contract G — kho cá thể có độ tươi):
    {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}

Đọc: từ chối file kho đếm (dict), sai schema, kind lạ, id trùng, fresh ngoài [0, 100] (BadInput -> mã 2).
Ghi: sắp theo id (`sort_by_id`), qua file tạm cùng thư mục rồi thay thế nguyên tử, byte-ổn-định.
"""

import json
import os
import tempfile

from .errors import BadInput
from .freshness_v12 import parse_item_list, serialize_items_sorted

KINDS_V11 = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")
KINDS_P1 = KINDS_V11  # alias tương thích cho bản live


def validate_items(items, kinds=KINDS_V11):
    """Kiểm mảng cá thể v1.2 `[{id, kind, fresh}]`; từ chối dict đếm với BadInput (mã 2)."""
    return parse_item_list(items, allowed_kinds=kinds, label="items")


def read_inventory(path: str, kinds=KINDS_V11) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if not isinstance(data["items"], list):
        raise BadInput("Contract v1.2 yêu cầu items là mảng cá thể [{id, kind, fresh}], không nhận kho đếm")
    return parse_item_list(data["items"], allowed_kinds=kinds, label="items")


def hold_to_items(hold: list) -> dict:
    """Tiện ích đếm (dùng riêng cho luồng chuyển kho bộ nhớ bản live)."""
    counts = {}
    for entry in hold:
        k = entry["kind"] if isinstance(entry, dict) else entry
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items: list, spoiled_below=30):
    payload = serialize_items_sorted(items, spoiled_below=spoiled_below)
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": payload}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
