"""Nghiệp vụ đơn hàng, khách, giữ chỗ nguyên liệu theo id cá thể, độ tươi và kiểm mâu thuẫn cho `quan` (Contract v1.2).

Hỗ trợ cả chế độ `--mode quan` độc lập (đủ 6 món) lẫn `--mode day` (lọc món theo `day_plan` của Ngày hiện tại):
  - Kho thô là mảng cá thể `[{id, kind, fresh(Fraction)}]`.
  - `customers[].reserved` là mảng id cá thể `["I1", ...]`, không trỏ hàng ươn, không trùng giữa các đơn.
  - Chọn cá thể tươi nhất (hòa theo id nhỏ); khi hàng giữ bị ươn, nhả toàn bộ và thử giữ lại đúng 1 lần theo `(order_tick, table_id)`.
  - Chốt giá theo độ tươi: `base_price = floor(giá_niêm_yết * trung_bình_fresh / 100)`.
"""

from decimal import Decimal, ROUND_FLOOR
import math

from ..errors import BadInput
from ..freshness_v12 import (
    compute_fresh_price,
    get_freshness_cfg,
    is_spoiled,
    parse_item_list,
    serialize_item,
    to_fraction,
)
from ..ids import id_key, sort_by_id
from ..inventory import KINDS_V11

TICK = 60.0

CUSTOMER_STATES = ("waiting", "eating")
ORDER_STATUSES = ("reserved", "assigned", "unfulfillable", "served")
STOVE_STATES = ("idle", "cooking", "ready")

DISH_KEYS = {"order_id", "dish_id", "base_price"}
STOVE_KEYS = {"id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks"}
TABLE_KEYS = {"id", "pos"}
CUSTOMER_KEYS = {
    "id", "table_id", "dish_id", "order_tick", "state",
    "patience_ticks_left", "eat_ticks_left", "order_status",
    "reserved", "base_price", "tip",
}


def ticks_from_s(seconds) -> int:
    return int(round(seconds * TICK))


def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_nonneg_int(name: str, v) -> int:
    if not _is_int(v) or v < 0:
        raise BadInput(f"{name} phải là số nguyên không âm")
    return v


def _check_pos_int(name: str, v) -> int:
    if not _is_int(v) or v <= 0:
        raise BadInput(f"{name} phải là số nguyên dương")
    return v


def clamp_reputation(value: float, t_quan: dict) -> float:
    clamped = min(float(t_quan["reputation_max"]), max(float(t_quan["reputation_min"]), float(value)))
    return round(clamped, 6)


def compute_tip(base_price: int, patience_ticks_left: int, t_quan: dict) -> int:
    """Chốt boa = floor(base_price * tip_rate) nếu patience_ticks_left / patience_max >= tip_min_patience_ratio."""
    patience_max = ticks_from_s(t_quan["patience_s"])
    qualifies = Decimal(patience_ticks_left) >= Decimal(str(t_quan["tip_min_patience_ratio"])) * Decimal(patience_max)
    if not qualifies:
        return 0
    return int((Decimal(base_price) * Decimal(str(t_quan["tip_rate"]))).to_integral_value(rounding=ROUND_FLOOR))


def normalize_recipe(recipe: dict) -> dict:
    return {k: recipe[k] for k in sorted(recipe) if recipe[k] > 0}


def validate_dish_payload(dish, menu: dict, label: str = "dish", allowed_dishes=None) -> dict:
    if not isinstance(dish, dict):
        raise BadInput(f"{label} phải là object món")
    if set(dish) != DISH_KEYS:
        raise BadInput(f"{label} phải có đúng các khóa {sorted(DISH_KEYS)}")
    oid = dish["order_id"]
    if not isinstance(oid, str) or not oid:
        raise BadInput(f"{label}.order_id phải là chuỗi khác rỗng")
    did = dish["dish_id"]
    if not isinstance(did, str) or did not in menu:
        raise BadInput(f"{label}.dish_id không hợp lệ: {did!r}")
    if allowed_dishes is not None and did not in allowed_dishes:
        raise BadInput(f"{label}.dish_id ({did}) không nằm trong kế hoạch ngày")
    bp = _check_pos_int(f"{label}.base_price", dish["base_price"])
    return {"order_id": oid, "dish_id": did, "base_price": bp}


def _validate_reserved_ids(raw, label: str) -> list:
    if not isinstance(raw, list):
        raise BadInput(f"{label} phải là mảng id cá thể [\"I1\", ...] (Contract v1.2 không nhận dict)")
    seen = set()
    out = []
    for idx, ident in enumerate(raw):
        if not isinstance(ident, str) or not ident:
            raise BadInput(f"{label}[{idx}] phải là chuỗi id khác rỗng")
        if ident in seen:
            raise BadInput(f"{label}: trùng id cá thể {ident}")
        seen.add(ident)
        out.append(ident)
    return sorted(out, key=id_key)


def _validate_pos_bounds(name: str, pos, bounds: dict):
    if not (isinstance(pos, list) and len(pos) == 2 and all(_is_num(c) for c in pos)):
        raise BadInput(f"{name} phải là [x, z]")
    for c, axis in zip(pos, ("x", "z")):
        lo, hi = bounds[axis]
        if not (lo <= c <= hi):
            raise BadInput(f"{name} nằm ngoài vùng quán ({axis} ∈ [{lo}, {hi}])")


def validate_quan_scenario_block(block: dict, tuning: dict, in_day_mode: bool = False, allowed_dishes=None):
    """Kiểm cấu trúc và bất biến mức luật của khối `scenario.quan` (Contract v1.2)."""
    t_quan = tuning["quan"]
    menu = tuning["menu"]
    bounds = t_quan["bounds"]
    spoiled_below = get_freshness_cfg(tuning)["spoiled_below"]

    if in_day_mode:
        if "stock" in block:
            raise BadInput("cấm khai quan.stock khi chạy --mode day (dùng gather.hold)")
        if "reputation" in block:
            raise BadInput("cấm khai quan.reputation khi chạy --mode day (dùng day.reputation)")

    if "random_customers" in block and not isinstance(block["random_customers"], bool):
        raise BadInput("quan.random_customers phải là boolean")

    if "reputation" in block:
        rep = block["reputation"]
        lo, hi = t_quan["reputation_min"], t_quan["reputation_max"]
        if not _is_num(rep) or not (lo <= rep <= hi):
            raise BadInput(f"quan.reputation phải nằm trong [{lo}, {hi}]")

    default_stoves = {s["id"]: dict(s) for s in t_quan["stoves"]}
    default_tables = {tb["id"]: dict(tb) for tb in t_quan["tables"]}

    merged_stoves = {sid: dict(s) for sid, s in default_stoves.items()}
    for st in block.get("stoves", []):
        extra = set(st) - STOVE_KEYS
        if extra:
            raise BadInput(f"stoves.{st['id']}: trường lạ {sorted(extra)}")
        if st["id"] not in default_stoves:
            raise BadInput(f"stoves: id không tồn tại trong tuning: {st['id']}")
        if "pos" in st:
            _validate_pos_bounds(f"stoves.{st['id']}.pos", st["pos"], bounds)
        merged_stoves[st["id"]].update(st)

    merged_tables = {tid: dict(tb) for tid, tb in default_tables.items()}
    for tb in block.get("tables", []):
        extra = set(tb) - TABLE_KEYS
        if extra:
            raise BadInput(f"tables.{tb['id']}: trường lạ {sorted(extra)}")
        if tb["id"] not in default_tables:
            raise BadInput(f"tables: id không tồn tại trong tuning: {tb['id']}")
        if "pos" in tb:
            _validate_pos_bounds(f"tables.{tb['id']}.pos", tb["pos"], bounds)
        merged_tables[tb["id"]].update(tb)

    stock = parse_item_list(block["stock"], allowed_kinds=KINDS_V11, label="quan.stock") if "stock" in block else None

    init_quan_entities(
        t_quan=t_quan,
        menu=menu,
        stock=stock,
        stoves=sort_by_id(list(merged_stoves.values())),
        tables=sort_by_id(list(merged_tables.values())),
        raw_customers=block.get("customers", []),
        raw_hand=block.get("hand"),
        ids=None,
        allowed_dishes=allowed_dishes,
        check_stock_capacity=(stock is not None),
        spoiled_below=spoiled_below,
    )


def init_quan_entities(
    t_quan: dict,
    menu: dict,
    stock: list | None,
    stoves: list,
    tables: list,
    raw_customers: list,
    raw_hand,
    ids=None,
    allowed_dishes=None,
    check_stock_capacity: bool = True,
    spoiled_below=30,
):
    """Chuẩn hóa và kiểm mâu thuẫn mức luật cho stoves, hand, customers (Contract v1.2).

    Trả về `(stoves, hand, customers)` đã chuẩn hóa và sắp theo id.
    """
    patience_max = ticks_from_s(t_quan["patience_s"])
    eat_max = ticks_from_s(t_quan["eat_s"])

    # 1. Chuẩn hóa & kiểm từng bếp
    dishes_by_order = {}
    norm_stoves = []
    for raw_st in sort_by_id(stoves):
        st = dict(raw_st)
        st["pos"] = [float(c) for c in st["pos"]]
        state = st.get("state", "idle")
        if state not in STOVE_STATES:
            raise BadInput(f"stoves.{st['id']}.state không hợp lệ: {state!r}")
        cook_left = _check_nonneg_int(f"stoves.{st['id']}.cook_ticks_left", st.get("cook_ticks_left", 0))
        ready_ticks = _check_nonneg_int(f"stoves.{st['id']}.ready_ticks", st.get("ready_ticks", 0))
        raw_dish = st.get("dish")

        if state == "idle":
            if raw_dish is not None or cook_left != 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{st['id']}: bếp idle không được có món hoặc bộ đếm dương")
            dish = None
        elif state == "cooking":
            if raw_dish is None:
                raise BadInput(f"stoves.{st['id']}: bếp cooking phải có dish")
            if cook_left <= 0 or ready_ticks != 0:
                raise BadInput(f"stoves.{st['id']}: bếp cooking phải có cook_ticks_left > 0 và ready_ticks == 0")
            dish = validate_dish_payload(raw_dish, menu, f"stoves.{st['id']}.dish", allowed_dishes=allowed_dishes)
        else:  # ready
            if raw_dish is None:
                raise BadInput(f"stoves.{st['id']}: bếp ready phải có dish")
            if cook_left != 0:
                raise BadInput(f"stoves.{st['id']}: bếp ready phải có cook_ticks_left == 0")
            dish = validate_dish_payload(raw_dish, menu, f"stoves.{st['id']}.dish", allowed_dishes=allowed_dishes)

        if dish is not None:
            oid = dish["order_id"]
            if oid in dishes_by_order:
                raise BadInput(f"đơn {oid} xuất hiện trùng trên nhiều bếp/tay")
            dishes_by_order[oid] = (f"stoves.{st['id']}", dish)

        st.update(state=state, dish=dish, cook_ticks_left=cook_left, ready_ticks=ready_ticks)
        norm_stoves.append(st)

    # 2. Kiểm tay người chơi
    if raw_hand is None:
        hand = None
    else:
        hand = validate_dish_payload(raw_hand, menu, "hand", allowed_dishes=allowed_dishes)
        oid = hand["order_id"]
        if oid in dishes_by_order:
            raise BadInput(f"đơn {oid} cùng nằm trên bếp và tay")
        dishes_by_order[oid] = ("hand", hand)

    # 3. Chuẩn hóa & kiểm từng khách
    known_tables = {tb["id"] for tb in tables}
    seen_tables = set()
    seen_cids = set()
    customers = []
    explicit_reserved = []
    auto_reserved = []

    for raw_c in raw_customers:
        if not isinstance(raw_c, dict):
            raise BadInput("mỗi khách phải là object")
        extra = set(raw_c) - CUSTOMER_KEYS
        if extra:
            raise BadInput(f"customers: trường lạ {sorted(extra)}")
        cid = raw_c.get("id")
        if not isinstance(cid, str) or not cid:
            raise BadInput("customers: thiếu id hợp lệ")
        if cid in seen_cids:
            raise BadInput(f"customers: id trùng {cid}")
        seen_cids.add(cid)

        tid = raw_c.get("table_id")
        if not isinstance(tid, str) or tid not in known_tables:
            raise BadInput(f"customers.{cid}: table_id không tồn tại: {tid!r}")
        if tid in seen_tables:
            raise BadInput(f"hai khách cùng bàn {tid}")
        seen_tables.add(tid)

        dish_id = raw_c.get("dish_id")
        if not isinstance(dish_id, str) or dish_id not in menu:
            raise BadInput(f"customers.{cid}: dish_id không hợp lệ: {dish_id!r}")
        if allowed_dishes is not None and dish_id not in allowed_dishes:
            raise BadInput(f"customers.{cid}: món {dish_id} không nằm trong kế hoạch ngày")

        order_tick = _check_nonneg_int(f"customers.{cid}.order_tick", raw_c.get("order_tick", 0))
        state = raw_c.get("state", "waiting")
        if state not in CUSTOMER_STATES:
            raise BadInput(f"customers.{cid}.state không hợp lệ: {state!r}")

        order_status = raw_c.get("order_status", "reserved")
        if order_status not in ORDER_STATUSES:
            raise BadInput(f"customers.{cid}.order_status không hợp lệ: {order_status!r}")

        default_patience = patience_max if state == "waiting" else 0
        patience_left = _check_nonneg_int(
            f"customers.{cid}.patience_ticks_left",
            raw_c.get("patience_ticks_left", default_patience),
        )
        if patience_left > patience_max:
            raise BadInput(f"customers.{cid}.patience_ticks_left vượt kiên nhẫn tối đa ({patience_max})")

        eat_left = _check_nonneg_int(f"customers.{cid}.eat_ticks_left", raw_c.get("eat_ticks_left", 0))
        if eat_left > eat_max:
            raise BadInput(f"customers.{cid}.eat_ticks_left vượt thời gian ăn tối đa ({eat_max})")

        has_reserved_key = "reserved" in raw_c
        raw_res = raw_c.get("reserved")
        raw_bp = raw_c.get("base_price")
        raw_tip = raw_c.get("tip")

        if state == "eating":
            if order_status != "served":
                raise BadInput(f"customers.{cid}: khách eating phải có order_status='served'")
            if eat_left <= 0:
                raise BadInput(f"customers.{cid}: khách eating phải có eat_ticks_left > 0")
            if cid in dishes_by_order:
                raise BadInput(f"customers.{cid}: khách eating không được còn món ở bếp/tay")
            if has_reserved_key:
                res_norm = _validate_reserved_ids(raw_res, f"customers.{cid}.reserved")
                if res_norm:
                    raise BadInput(f"customers.{cid}: khách eating phải có reserved rỗng")
            if raw_bp is None or raw_tip is None:
                raise BadInput(f"customers.{cid}: khách eating phải khai base_price và tip đã chốt")
            base_price = _check_pos_int(f"customers.{cid}.base_price", raw_bp)
            tip = _check_nonneg_int(f"customers.{cid}.tip", raw_tip)
            reserved = []
        else:  # state == "waiting"
            if order_status == "served":
                raise BadInput(f"customers.{cid}: khách waiting không thể có order_status='served'")
            if eat_left != 0:
                raise BadInput(f"customers.{cid}: khách waiting phải có eat_ticks_left == 0")
            if raw_tip is not None:
                tip_val = _check_nonneg_int(f"customers.{cid}.tip", raw_tip)
                if tip_val != 0:
                    raise BadInput(f"customers.{cid}: khách waiting chưa chốt boa dương")
            tip = None

            if order_status == "assigned":
                if has_reserved_key:
                    res_norm = _validate_reserved_ids(raw_res, f"customers.{cid}.reserved")
                    if res_norm:
                        raise BadInput(f"customers.{cid}: đơn assigned phải có reserved rỗng")
                if cid not in dishes_by_order:
                    raise BadInput(f"customers.{cid}: đơn assigned phải có đúng một món ở bếp hoặc tay")
                _, dish = dishes_by_order[cid]
                if dish["dish_id"] != dish_id:
                    raise BadInput(f"customers.{cid}: món trên bếp/tay ({dish['dish_id']}) không khớp đơn ({dish_id})")
                if raw_bp is not None:
                    base_price = _check_pos_int(f"customers.{cid}.base_price", raw_bp)
                    if base_price != dish["base_price"]:
                        raise BadInput(f"customers.{cid}: base_price không khớp món trên bếp/tay")
                else:
                    base_price = dish["base_price"]
                reserved = []
            elif order_status == "unfulfillable":
                if cid in dishes_by_order:
                    raise BadInput(f"customers.{cid}: đơn unfulfillable không được có món ở bếp/tay")
                if has_reserved_key:
                    res_norm = _validate_reserved_ids(raw_res, f"customers.{cid}.reserved")
                    if res_norm:
                        raise BadInput(f"customers.{cid}: đơn unfulfillable phải có reserved rỗng")
                base_price = _check_pos_int(f"customers.{cid}.base_price", raw_bp) if raw_bp is not None else None
                reserved = []
            else:  # order_status == "reserved"
                if cid in dishes_by_order:
                    raise BadInput(f"customers.{cid}: đơn reserved không được có món ở bếp/tay")
                base_price = _check_pos_int(f"customers.{cid}.base_price", raw_bp) if raw_bp is not None else None
                if has_reserved_key:
                    res_norm = _validate_reserved_ids(raw_res, f"customers.{cid}.reserved")
                    expected_total = sum(normalize_recipe(menu[dish_id]["recipe"]).values())
                    if len(res_norm) != expected_total:
                        raise BadInput(f"customers.{cid}: số lượng cá thể reserved khác công thức món {dish_id}")
                    reserved = res_norm
                else:
                    reserved = None  # sẽ cấp tự động theo (order_tick, id_key(table_id))

        cust = {
            "id": cid,
            "table_id": tid,
            "dish_id": dish_id,
            "order_tick": order_tick,
            "state": state,
            "patience_ticks_left": patience_left,
            "eat_ticks_left": eat_left,
            "order_status": order_status,
            "reserved": reserved,
            "base_price": base_price,
            "tip": tip,
        }
        customers.append(cust)
        if order_status == "reserved":
            if reserved is not None:
                explicit_reserved.append(cust)
            else:
                auto_reserved.append(cust)

    # 4. Mọi món trên bếp/tay phải liên kết tới một khách `assigned` có thật
    customers_by_id = {c["id"]: c for c in customers}
    for oid, (src, _) in dishes_by_order.items():
        if oid not in customers_by_id:
            raise BadInput(f"{src}: không có khách {oid} (tham chiếu id không tạo thực thể)")

    # 5. Kiểm trùng id giữa các đơn explicit_reserved ngay cả khi chưa có stock (ví dụ stock đến từ --inventory)
    used_ids = set()
    for c in explicit_reserved:
        for item_id in c["reserved"]:
            if item_id in used_ids:
                raise BadInput(f"customers.{c['id']}: cá thể {item_id} bị dùng chung giữa hai đơn")
            used_ids.add(item_id)

    # 6. Kiểm đối chiếu tồn kho thực tế (tồn tại, chưa ươn, khớp công thức) & cấp giữ chỗ mặc định
    if check_stock_capacity:
        stock_by_id = {it["id"]: it for it in (stock or [])}
        for c in explicit_reserved:
            recipe = normalize_recipe(menu[c["dish_id"]]["recipe"])
            counts = {}
            for item_id in c["reserved"]:
                it = stock_by_id.get(item_id)
                if it is None:
                    raise BadInput(f"customers.{c['id']}: cá thể {item_id} không có trong kho")
                if is_spoiled(it, spoiled_below):
                    raise BadInput(f"customers.{c['id']}: không thể giữ cá thể đã ươn {item_id}")
                counts[it["kind"]] = counts.get(it["kind"], 0) + 1
            if {k: counts[k] for k in sorted(counts)} != recipe:
                raise BadInput(f"customers.{c['id']}: danh sách reserved không khớp công thức món {c['dish_id']}")

        for c in sorted(auto_reserved, key=lambda x: (x["order_tick"], id_key(x["table_id"]))):
            recipe = normalize_recipe(menu[c["dish_id"]]["recipe"])
            picked = _pick_freshest_ids(recipe, stock or [], used_ids, spoiled_below)
            if picked is None:
                raise BadInput(f"customers.{c['id']}: không đủ hàng chưa ươn trong kho để giữ chỗ cho đơn reserved")
            c["reserved"] = picked
            used_ids.update(picked)
    else:
        for c in auto_reserved:
            c["reserved"] = []

    if ids is not None:
        for it in (stock or []):
            ids.reserve(it["id"])
        for c in customers:
            ids.reserve(c["id"])

    return norm_stoves, hand, sort_by_id(customers)


# --- Nghiệp vụ kho khả dụng, chọn cá thể tươi nhất, ươn hàng, đơn hàng & vòng đời khách ---

def _reserved_id_set(customers: list) -> set:
    out = set()
    for c in customers:
        res = c.get("reserved")
        if isinstance(res, list):
            out.update(res)
    return out


def _pick_freshest_ids(recipe: dict, stock: list, used_ids: set, spoiled_below=30):
    """Chọn các cá thể chưa ươn tươi nhất (hòa theo id nhỏ) khớp `recipe`, trả mảng id đã sắp theo `id_key` hoặc None."""
    picked = []
    for kind, need in normalize_recipe(recipe).items():
        candidates = [
            it for it in stock
            if it["kind"] == kind and it["id"] not in used_ids and not is_spoiled(it, spoiled_below)
        ]
        if len(candidates) < need:
            return None
        candidates.sort(key=lambda it: (-to_fraction(it["fresh"]), id_key(it["id"])))
        picked.extend(it["id"] for it in candidates[:need])
    return sorted(picked, key=id_key)


def available_unspoiled_items(stock: list, customers: list, spoiled_below=30) -> list:
    """Danh sách cá thể chưa ươn và chưa bị đơn nào giữ chỗ."""
    used = _reserved_id_set(customers)
    return [it for it in stock if it["id"] not in used and not is_spoiled(it, spoiled_below)]


def available_stock(stock: list, customers: list, spoiled_below=30) -> dict:
    """Đếm số lượng khả dụng chưa ươn theo loại (phục vụ kiểm nấu được & HUD)."""
    counts = {}
    for it in available_unspoiled_items(stock, customers, spoiled_below=spoiled_below):
        counts[it["kind"]] = counts.get(it["kind"], 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def select_items_for_recipe(recipe: dict, stock: list, customers: list, spoiled_below=30):
    """Chọn mảng id cá thể tươi nhất chưa ươn cho `recipe` dựa trên danh sách khách hiện tại."""
    return _pick_freshest_ids(recipe, stock, _reserved_id_set(customers), spoiled_below=spoiled_below)


def cookable_dishes(menu: dict, stock: list, customers: list, allowed_dishes=None, spoiled_below=30) -> list:
    """Danh sách dish_id nấu được từ hàng chưa ươn khả dụng, sắp theo mã Unicode."""
    avail = available_stock(stock, customers, spoiled_below=spoiled_below)
    candidates = sorted(menu) if allowed_dishes is None else [d for d in sorted(menu) if d in allowed_dishes]
    return [
        dish_id
        for dish_id in candidates
        if all(avail.get(k, 0) >= cnt for k, cnt in menu[dish_id]["recipe"].items())
    ]


def re_reserve_after_spoil(stock: list, customers: list, menu: dict, spoiled_below=30):
    """Xử lý các đơn `reserved` có cá thể vừa ươn theo thứ tự `(order_tick, id_key(table_id))`.

    Mỗi đơn bị ảnh hưởng: nhả toàn bộ phần giữ hiện tại và thử giữ lại đúng một lần từ hàng tươi nhất chưa ươn.
    Không đủ thì chuyển sang `unfulfillable` (khách tiếp tục chờ tới hạn kiên nhẫn).
    """
    stock_by_id = {it["id"]: it for it in stock}
    affected = []
    for c in customers:
        if c["state"] != "waiting" or c["order_status"] != "reserved":
            continue
        res = c.get("reserved") or []
        if any(
            (item_id not in stock_by_id) or is_spoiled(stock_by_id[item_id], spoiled_below)
            for item_id in res
        ):
            affected.append(c)

    affected.sort(key=lambda c: (c["order_tick"], id_key(c["table_id"])))
    for c in affected:
        c["reserved"] = []
        picked = select_items_for_recipe(menu[c["dish_id"]]["recipe"], stock, customers, spoiled_below=spoiled_below)
        if picked is not None:
            c["reserved"] = picked
        else:
            c["order_status"] = "unfulfillable"


def oldest_reserved_order(customers: list):
    """Đơn `reserved` cũ nhất theo `(order_tick, id_key(table_id))` cho bếp idle."""
    candidates = [c for c in customers if c["state"] == "waiting" and c["order_status"] == "reserved"]
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c["order_tick"], id_key(c["table_id"])))


def consume_order_for_cooking(stock: list, customer: dict, menu: dict, spoiled_below=30):
    """Tiêu đúng các id cá thể đang giữ của đơn `reserved`, chốt giá theo độ tươi và chuyển sang `assigned`.

    Trả về `(cook_items_sorted, base_price)`:
      - `cook_items_sorted`: mảng cá thể `{id, kind, fresh}` sắp theo `(kind, id_key(id))`.
      - `base_price`: `floor(giá_niêm_yết * trung_bình_fresh / 100)`.
    """
    if customer["state"] != "waiting" or customer["order_status"] != "reserved":
        raise ValueError(f"đơn {customer['id']} không ở trạng thái reserved")
    reserved_ids = set(customer["reserved"])
    used_items = []
    remaining = []
    for it in stock:
        if it["id"] in reserved_ids:
            used_items.append(it)
        else:
            remaining.append(it)
    if len(used_items) != len(reserved_ids):
        raise ValueError(f"tồn kho thiếu cá thể giữ chỗ của đơn {customer['id']}")
    stock[:] = remaining

    base_price = compute_fresh_price(menu[customer["dish_id"]]["price"], used_items)
    used_sorted = sorted(used_items, key=lambda it: (it["kind"], id_key(it["id"])))
    cook_items = [serialize_item(it, spoiled_below=spoiled_below) for it in used_sorted]

    customer["reserved"] = []
    customer["order_status"] = "assigned"
    customer["base_price"] = base_price
    return cook_items, base_price


def release_customer_links(customer: dict, stoves: list, hand):
    """Khi khách rời: nhả phần giữ thô, bỏ món của đơn đang nấu, ready hoặc trên tay (không hoàn tồn đã tiêu)."""
    customer["reserved"] = []
    oid = customer["id"]
    for st in stoves:
        dish = st.get("dish")
        if dish is not None and dish.get("order_id") == oid:
            st["state"] = "idle"
            st["dish"] = None
            st["cook_ticks_left"] = 0
            st["ready_ticks"] = 0
    if hand is not None and hand.get("order_id") == oid:
        hand = None
    return hand


def tick_customer_timers(customers: list):
    """Bước 1: giảm kiên nhẫn của khách waiting và thời gian ăn của khách eating (không âm)."""
    for c in customers:
        if c["state"] == "eating":
            c["eat_ticks_left"] = max(0, c["eat_ticks_left"] - 1)
        else:
            c["patience_ticks_left"] = max(0, c["patience_ticks_left"] - 1)


def process_waiting_departures(
    customers: list,
    tables: list,
    stoves: list,
    hand,
    t_quan: dict,
    reputation: float,
    closing: bool = False,
):
    """Bước 5 (phần khách chờ rời bàn): duyệt theo id bàn."""
    events = []
    by_table = {c["table_id"]: c for c in customers}
    for tb in sort_by_id(tables):
        c = by_table.get(tb["id"])
        if c is None or c["state"] != "waiting":
            continue
        if closing:
            reason = "closing"
        elif c["patience_ticks_left"] == 0:
            reason = "patience"
            reputation = clamp_reputation(reputation + t_quan["left_reputation_delta"], t_quan)
        else:
            continue
        hand = release_customer_links(c, stoves, hand)
        customers.remove(c)
        events.append((
            "customer_left",
            {"order_id": c["id"], "table_id": c["table_id"], "reason": reason, "reputation": reputation},
        ))
    return hand, reputation, events


def spawn_customer_if_due(
    phase_tick: int,
    t_quan: dict,
    menu: dict,
    stock: list,
    tables: list,
    customers: list,
    rng,
    ids,
    random_customers: bool = True,
    allowed_dishes=None,
    spoiled_below=30,
) -> list:
    """Bước 6: sinh khách mới theo `phase_tick` (chỉ gọi khi ca còn giờ)."""
    if not random_customers:
        return []
    first = t_quan["first_customer_tick"]
    interval = ticks_from_s(t_quan["customer_interval_s"])
    if phase_tick < first or (phase_tick - first) % interval != 0:
        return []

    occupied = {c["table_id"] for c in customers}
    free_tables = [tb for tb in sort_by_id(tables) if tb["id"] not in occupied]
    if not free_tables:
        return []

    table = free_tables[0]
    dishes = cookable_dishes(menu, stock, customers, allowed_dishes=allowed_dishes, spoiled_below=spoiled_below)
    if not dishes:
        return [("no_dish", {})]

    dish_id = rng.get("customer_order").choice(dishes)
    picked = select_items_for_recipe(menu[dish_id]["recipe"], stock, customers, spoiled_below=spoiled_below)
    if picked is None:
        return [("no_dish", {})]

    cid = ids.new("C")
    cust = {
        "id": cid,
        "table_id": table["id"],
        "dish_id": dish_id,
        "order_tick": phase_tick,
        "state": "waiting",
        "patience_ticks_left": ticks_from_s(t_quan["patience_s"]),
        "eat_ticks_left": 0,
        "order_status": "reserved",
        "reserved": picked,
        "base_price": None,
        "tip": None,
    }
    customers.append(cust)
    return [("customer_arrived", {"order_id": cid, "table_id": table["id"], "dish_id": dish_id})]
