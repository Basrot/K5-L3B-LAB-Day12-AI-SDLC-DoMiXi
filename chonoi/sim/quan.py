"""Buổi tối — Mở Quán (`quan`) đầy đủ theo Test Contract v1.2 (2 bếp B1–B2, 4 bàn T1–T4, 6 món, độ tươi cá thể).

Thứ tự tick theo Contract v1.2:
  1. Đồng hồ & timer (`phase_tick`, `time_left_ticks`, bếp, khách).
  2. Hao tươi kho thô (0.25/s = 1/240 mỗi tick), phát hết `spoiled` theo `id` rồi mới xử lý giữ chỗ bị ươn theo `(order_tick, table_id)`.
  3. Xét bếp nấu xong (`dish_ready` theo id bếp).
  4. Di chuyển và tối đa một `interact` (chốt giá theo trung bình fresh khi bắt đầu nấu; boa theo giá đã chốt).
  5. Thanh toán, khách rời (`patience` / `closing`) & `quan_end`.
  6. Nếu còn giờ: sinh khách thường giữ các cá thể tươi nhất chưa ươn.
"""

import math

from ..freshness_v12 import (
    decay_items,
    get_freshness_cfg,
    parse_item_list,
    serialize_items_sorted,
)
from ..ids import id_key, sort_by_id
from ..inventory import KINDS_V11
from .quan_orders import (
    available_stock,
    clamp_reputation,
    compute_tip,
    consume_order_for_cooking,
    init_quan_entities,
    oldest_reserved_order,
    process_waiting_departures,
    re_reserve_after_spoil,
    spawn_customer_if_due,
    tick_customer_timers,
    ticks_from_s,
)
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"
    _live_mode = False

    def __init__(
        self,
        tuning,
        scenario,
        streams,
        ids,
        inventory=None,
        allowed_dishes=None,
        initial_money: int = 0,
        initial_earned: int = 0,
        initial_reputation=None,
    ):
        t = tuning["quan"]
        self.t = t
        self.tuning = tuning
        self.fresh_cfg = get_freshness_cfg(tuning)
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        self.allowed_dishes = set(allowed_dishes) if allowed_dishes is not None else None
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0

        # Kho v1.2: mảng cá thể [{id, kind, fresh(Fraction)}], giữ nguyên độ tươi kể cả hàng ươn.
        # Bản live (_live_mode=True) tự quản self.stock dạng dict đếm + self.fresh_items.
        if self._live_mode:
            src_stock = inventory if inventory is not None else scenario.get("stock", {})
            self.stock = dict(src_stock) if isinstance(src_stock, dict) else []
        else:
            raw_stock = inventory if inventory is not None else scenario.get("stock", [])
            self.stock = parse_item_list(raw_stock, allowed_kinds=KINDS_V11, label="quan.stock")

        self.phase_tick = 0
        self.random_customers = scenario.get("random_customers", True)
        self.time_left_ticks = scenario.get("time_left_ticks", ticks_from_s(t["duration_s"]))
        default_rep = t["reputation_initial"] if initial_reputation is None else initial_reputation
        self.reputation = clamp_reputation(scenario.get("reputation", default_rep), t)

        raw_stoves = self._merge(t["stoves"], scenario.get("stoves", []))
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        for tb in self.tables:
            tb["pos"] = [float(c) for c in tb["pos"]]

        self.stoves, self.hand, self.customers = init_quan_entities(
            t_quan=t,
            menu=self.menu,
            stock=None if self._live_mode else self.stock,
            stoves=raw_stoves,
            tables=self.tables,
            raw_customers=scenario.get("customers", []),
            raw_hand=scenario.get("hand"),
            ids=ids,
            allowed_dishes=self.allowed_dishes,
            check_stock_capacity=(not self._live_mode),
            spoiled_below=self.fresh_cfg["spoiled_below"],
        )

        self.money = int(initial_money)
        self.earned = int(initial_earned)
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def available_stock(self) -> dict:
        """Kho khả dụng chưa ươn = tồn vật lý chưa ươn − phần giữ chỗ (dùng cho chọn món và HUD)."""
        return available_stock(self.stock, self.customers, spoiled_below=self.fresh_cfg["spoiled_below"])

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        if self._live_mode and isinstance(self.stock, dict):
            stock_snap = {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0}
        else:
            stock_snap = serialize_items_sorted(self.stock, spoiled_below=self.fresh_cfg["spoiled_below"])
        cust_snaps = []
        for c in sort_by_id(self.customers):
            c_copy = dict(c)
            if "reserved" in c_copy:
                c_copy["reserved"] = dict(c_copy["reserved"]) if isinstance(c_copy["reserved"], dict) else list(c_copy["reserved"])
            cust_snaps.append(c_copy)
        return {
            "player": {"pos": list(self.pos), "vel": list(self.vel)},
            "stock": stock_snap,
            "hand": dict(self.hand) if self.hand is not None else None,
            "stoves": [
                {
                    "id": s["id"],
                    "pos": list(s["pos"]),
                    "state": s["state"],
                    "dish": dict(s["dish"]) if isinstance(s.get("dish"), dict) else s.get("dish"),
                    "cook_ticks_left": s["cook_ticks_left"],
                    "ready_ticks": s["ready_ticks"],
                }
                for s in sort_by_id(self.stoves)
            ],
            "tables": [
                {"id": tb["id"], "pos": list(tb["pos"]), "customer_id": occupied.get(tb["id"])}
                for tb in sort_by_id(self.tables)
            ],
            "customers": cust_snaps,
        }

    def step(self, inp):
        events = []
        spoiled_below = self.fresh_cfg["spoiled_below"]

        # 1. Tăng đồng hồ, giảm timer ca, nấu, ăn và kiên nhẫn.
        #    Chỉ tăng ready_ticks cho món đã ready ở ĐẦU bước.
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        ready_at_start = {st["id"] for st in self.stoves if st["state"] == "ready"}
        for st in self.stoves:
            if st["state"] == "cooking":
                st["cook_ticks_left"] = max(0, st["cook_ticks_left"] - 1)
            elif st["id"] in ready_at_start:
                st["ready_ticks"] += 1
        tick_customer_timers(self.customers)

        # 2. Hao tươi kho thô (kể cả hàng đang giữ chỗ), phát HẾT `spoiled` theo id rồi mới xử lý giữ chỗ bị ươn.
        if decay_items(self.stock, self.fresh_cfg["quan_decay_per_s"], spoiled_below, "stock", events):
            re_reserve_after_spoil(self.stock, self.customers, self.menu, spoiled_below=spoiled_below)

        # 3. Xét bếp theo id: món nấu xong chuyển ready (ready_ticks = 0, phát dish_ready).
        for st in sort_by_id(self.stoves):
            if st["state"] == "cooking" and st["cook_ticks_left"] == 0:
                st["state"] = "ready"
                st["ready_ticks"] = 0
                dish = st["dish"]
                events.append((
                    "dish_ready",
                    {"stove_id": st["id"], "order_id": dish["order_id"], "dish_id": dish["dish_id"]},
                ))

        # 4. Di chuyển rồi xét tối đa một interact theo (khoảng cách, bếp trước bàn, id).
        self._move(inp)
        if inp.pressed("interact"):
            self._handle_interact(events)

        # 5. Thanh toán, khách rời & đóng ca (theo id bàn).
        # 5a. Khách ăn xong (eat_ticks_left == 0) trả tiền và rời bàn ngay.
        self._collect_eating_payments(events, only_finished=True, reason="finished_eating")

        closing = self.time_left_ticks == 0
        if closing:
            # 5b (closing). Khách còn đang ăn (kể cả vừa được phục vụ ở bước 4) trả ngay.
            self._collect_eating_payments(events, only_finished=False, reason="closing")
            # 5c (closing). Khách còn chờ rời với `closing` và KHÔNG trừ uy tín; dọn món/giữ chỗ.
            self.hand, self.reputation, leave_events = process_waiting_departures(
                self.customers, self.tables, self.stoves, self.hand,
                self.t, self.reputation, closing=True,
            )
            events.extend(leave_events)
            self.done = True
            self.reason = "time"
            events.append((
                "quan_end",
                {
                    "reason": "time",
                    "money": self.money,
                    "earned": self.earned,
                    "shift_earned": self.shift_earned,
                    "reputation": self.reputation,
                },
            ))
            return events

        # 5b (ca còn giờ). Khách waiting hết kiên nhẫn rời bàn và giảm uy tín.
        self.hand, self.reputation, leave_events = process_waiting_departures(
            self.customers, self.tables, self.stoves, self.hand,
            self.t, self.reputation, closing=False,
        )
        events.extend(leave_events)

        # 6. Nếu còn giờ, sinh khách mới theo phase_tick (tôn trọng random_customers và allowed_dishes).
        events.extend(spawn_customer_if_due(
            self.phase_tick, self.t, self.menu, self.stock,
            self.tables, self.customers, self.rng, self.ids,
            random_customers=self.random_customers,
            allowed_dishes=self.allowed_dishes,
            spoiled_below=spoiled_below,
        ))
        return events

    def _handle_interact(self, events):
        radius = self.t["interact_radius"]
        spoiled_below = self.fresh_cfg["spoiled_below"]
        candidates = []
        for st in self.stoves:
            d = math.dist(self.pos, st["pos"])
            if d <= radius:
                candidates.append((d, 0, id_key(st["id"]), "stove", st))
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= radius:
                candidates.append((d, 1, id_key(tb["id"]), "table", tb))
        if not candidates:
            return
        # Chọn đúng 1 đối tượng gần nhất (bếp trước bàn, hòa theo id). Không làm được -> bỏ lượt.
        _, _, _, kind, target = min(candidates, key=lambda item: item[:3])
        if kind == "stove":
            if target["state"] == "idle":
                cust = oldest_reserved_order(self.customers)
                if cust is None:
                    return
                items, base_price = consume_order_for_cooking(
                    self.stock, cust, self.menu, spoiled_below=spoiled_below
                )
                target["state"] = "cooking"
                target["dish"] = {
                    "order_id": cust["id"],
                    "dish_id": cust["dish_id"],
                    "base_price": base_price,
                }
                target["cook_ticks_left"] = ticks_from_s(self.menu[cust["dish_id"]]["cook_s"])
                target["ready_ticks"] = 0
                events.append((
                    "cook_started",
                    {
                        "stove_id": target["id"],
                        "order_id": cust["id"],
                        "dish_id": cust["dish_id"],
                        "items": items,
                        "base_price": base_price,
                    },
                ))
            elif target["state"] == "ready":
                if self.hand is not None:
                    return
                dish = target["dish"]
                self.hand = dict(dish)
                target["state"] = "idle"
                target["dish"] = None
                target["cook_ticks_left"] = 0
                target["ready_ticks"] = 0
                events.append((
                    "dish_picked",
                    {"stove_id": target["id"], "order_id": dish["order_id"], "dish_id": dish["dish_id"]},
                ))
        else:  # table
            if self.hand is None:
                return
            cust = next((c for c in self.customers if c["table_id"] == target["id"]), None)
            if (
                cust is None
                or cust["state"] != "waiting"
                or cust["order_status"] != "assigned"
                or cust["id"] != self.hand["order_id"]
            ):
                return
            base_price = self.hand["base_price"]
            tip = compute_tip(base_price, cust["patience_ticks_left"], self.t)
            cust["state"] = "eating"
            cust["order_status"] = "served"
            cust["eat_ticks_left"] = ticks_from_s(self.t["eat_s"])
            cust["base_price"] = base_price
            cust["tip"] = tip
            self.hand = None
            events.append((
                "served",
                {
                    "order_id": cust["id"],
                    "table_id": target["id"],
                    "dish_id": cust["dish_id"],
                    "patience_ticks_left": cust["patience_ticks_left"],
                    "base_price": base_price,
                    "tip": tip,
                },
            ))

    def _collect_eating_payments(self, events, only_finished: bool, reason: str):
        by_table = {c["table_id"]: c for c in self.customers}
        for tb in sort_by_id(self.tables):
            c = by_table.get(tb["id"])
            if c is None or c["state"] != "eating":
                continue
            if only_finished and c["eat_ticks_left"] > 0:
                continue
            base_price = c["base_price"]
            tip = c["tip"]
            amount = base_price + tip
            self.money += amount
            self.earned += amount
            self.shift_earned += amount
            if tip > 0:
                self.reputation = clamp_reputation(self.reputation + self.t["tip_reputation"], self.t)
            self.customers.remove(c)
            events.append((
                "paid",
                {
                    "order_id": c["id"],
                    "table_id": c["table_id"],
                    "base_price": base_price,
                    "tip": tip,
                    "amount": amount,
                    "reason": reason,
                },
            ))

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
