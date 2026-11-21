"""Buổi tối — Mở Quán (`quan`).

Phân công song song (PRD-0 mục F):
  - Lát 3 (Người 3 — đã nối từ `quan_orders.py`): dựng fixture & kiểm mâu thuẫn mức luật,
    sinh khách theo `phase_tick`, chọn bàn trống id nhỏ nhất, kho khả dụng & giữ chỗ nguyên liệu,
    giảm kiên nhẫn, khách chờ rời bàn (`patience` / `closing`) và dọn liên kết giữ chỗ / bếp / tay.
  - Lát 4 (Người 4 — tìm `TODO(Người 4)`): bếp nấu / chín / `ready_ticks`, `interact` tại bếp/bàn
    (`cook_started`, `dish_ready`, `dish_picked`, `served`), ăn xong trả tiền (`paid`), boa & uy tín,
    thanh toán khách còn ăn khi đóng ca (`closing`).
"""

from ..ids import sort_by_id
from .quan_orders import (
    available_stock,
    consume_order_for_cooking,
    init_quan_entities,
    oldest_reserved_order,
    process_waiting_departures,
    spawn_customer_if_due,
    tick_customer_timers,
)
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        src_stock = inventory if inventory is not None else scenario.get("stock", {})
        self.stock = {k: v for k, v in src_stock.items() if v > 0}
        self.phase_tick = 0
        self.random_customers = scenario.get("random_customers", True)
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = float(scenario.get("reputation", t["reputation_initial"]))

        raw_stoves = self._merge(t["stoves"], scenario.get("stoves", []))
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        for tb in self.tables:
            tb["pos"] = [float(c) for c in tb["pos"]]

        self.stoves, self.hand, self.customers = init_quan_entities(
            t_quan=t,
            menu=self.menu,
            stock=self.stock,
            stoves=raw_stoves,
            tables=self.tables,
            raw_customers=scenario.get("customers", []),
            raw_hand=scenario.get("hand"),
            ids=ids,
        )

        self.money = 0
        self.earned = 0
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
        """Kho khả dụng = tồn vật lý − phần giữ chỗ (dùng cho chọn món và HUD)."""
        return available_stock(self.stock, self.customers)

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": list(self.pos), "vel": list(self.vel)},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
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
            "customers": [
                dict(c, reserved=dict(c["reserved"])) if "reserved" in c else dict(c)
                for c in sort_by_id(self.customers)
            ],
        }

    def step(self, inp):
        events = []
        # 1. Tăng đồng hồ, giảm timer ca, nấu, ăn và kiên nhẫn.
        #    Chỉ tăng ready_ticks cho món đã ready ở đầu bước.
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        tick_customer_timers(self.customers)
        # TODO(Người 4, N4-01/N4-03): giảm cook_ticks_left cho bếp cooking;
        #   tăng ready_ticks cho bếp đã ready từ đầu bước.

        # 2. Xét bếp theo id: món nấu xong chuyển ready (ready_ticks = 0, phát dish_ready).
        # TODO(Người 4, N4-03): duyệt sort_by_id(self.stoves) và phát dish_ready.

        # 3. Di chuyển rồi xét tối đa một interact theo (khoảng cách, bếp trước bàn, id).
        self._move(inp)
        # TODO(Người 4, N4-02/N4-03/N4-04/N4-05):
        #   - Bếp idle lấy đơn: c = oldest_reserved_order(self.customers)
        #     items, base_price = consume_order_for_cooking(self.stock, c, self.menu)
        #   - Bếp ready giao món cho tay trống -> dish_picked.
        #   - Bàn nhận đúng order_id -> served (chốt boa bằng floor theo patience sau bước 1).

        # 4. Thanh toán, khách rời & đóng ca (theo id bàn).
        # TODO(Người 4, N4-06/N4-07):
        #   - Khách eating có eat_ticks_left == 0 -> paid (finished_eating), cộng tip_reputation, rời bàn.
        #   - Khi hết ca (time_left_ticks == 0): khách còn ăn trả ngay (reason="closing").
        closing = self.time_left_ticks == 0
        self.hand, self.reputation, leave_events = process_waiting_departures(
            self.customers, self.tables, self.stoves, self.hand,
            self.t, self.reputation, closing=closing,
        )
        events.extend(leave_events)
        if closing:
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

        # 5. Nếu còn giờ, sinh khách mới theo phase_tick (tôn trọng random_customers).
        events.extend(spawn_customer_if_due(
            self.phase_tick, self.t, self.menu, self.stock,
            self.tables, self.customers, self.rng, self.ids,
            random_customers=self.random_customers,
        ))
        return events

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
