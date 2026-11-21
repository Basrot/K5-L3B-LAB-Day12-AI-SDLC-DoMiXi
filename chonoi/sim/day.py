"""Vòng ngày (`--mode day`) và cửa hàng nâng cấp (`Shop`) theo Test Contract v1.2.

Luồng mỗi ngày: `gather` -> `quan` -> `shop` -> Ngày kế tiếp (hoặc kết thúc `days_complete` khi đóng Shop Ngày cuối).
  - Đổi pha diễn ra CÙNG tick: event kết thúc mang pha cũ, `phase_start` mang pha mới, snapshot ghi pha mới với `phase_tick: 0`.
  - Bàn giao `gather -> quan` giữ nguyên cá thể `{id, kind, fresh(Fraction)}` (kể cả hàng ươn) và KHÔNG hao thêm.
  - Hàng thô ở `Shop` giữ mảng cá thể theo id và KHÔNG hao tươi; bỏ khi đóng Shop.
  - Ngày đầu giữ nguyên id trong `scenario.gather.hold`; Ngày 2+ cấp id mới `I<n>` theo thứ tự mảng.
  - Nâng cấp mua trong Shop (`upgrades`) hiển thị ngay và CHỈ sao sang `active_upgrades` khi dựng Ngày mới.
"""

from ..contract import compute_plan_ingredients
from ..freshness_v12 import get_freshness_cfg, serialize_items_sorted
from .gather import GatherSim
from .quan import QuanSim


class ShopSim:
    mode = "day"
    phase = "shop"

    def __init__(self, tuning, stock, money, earned, reputation, upgrades):
        self.t = tuning["shop"]
        self.spoiled_below = get_freshness_cfg(tuning)["spoiled_below"]
        self.stock = [dict(it) for it in stock]
        self.money = int(money)
        self.earned = int(earned)
        self.reputation = float(reputation)
        self.upgrades = upgrades  # tham chiếu chung để DaySim giữ trạng thái mua
        self.phase_tick = 0
        self.time_left_ticks = int(self.t["max_ticks"])
        self.done = False
        self.reason = None

    def snapshot(self) -> dict:
        return {"stock": serialize_items_sorted(self.stock, spoiled_below=self.spoiled_below)}

    def step(self, inp):
        events = []
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Xử lý một lệnh `buy` trước cạnh `shop_done`, kể cả bước cuối
        if inp.buy is not None:
            action = inp.buy
            up_cfg = self.t["upgrades"]
            if action not in up_cfg:
                events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            else:
                cur_lvl = self.upgrades.get(action, 0)
                tiers = up_cfg[action]
                if cur_lvl >= len(tiers):
                    events.append(("buy_failed", {"action": action, "reason": "max_level"}))
                else:
                    tier = tiers[cur_lvl]
                    price = int(tier["price"])
                    if self.money < price:
                        events.append(("buy_failed", {"action": action, "reason": "funds"}))
                    else:
                        self.money -= price
                        self.upgrades[action] = cur_lvl + 1
                        events.append((
                            "bought",
                            {"upgrade": action, "level": cur_lvl + 1, "price": price, "money": self.money},
                        ))

        # 2. Đóng Shop: ưu tiên nút `shop_done` hơn hết giờ ở cùng bước cuối
        if inp.pressed("shop_done"):
            self.done = True
            self.reason = "done"
            events.append(("shop_end", {"reason": "done"}))
        elif self.time_left_ticks == 0:
            self.done = True
            self.reason = "time"
            events.append(("shop_end", {"reason": "time"}))

        return events


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days: int = 1):
        self.tuning = tuning
        self.scenario = scenario or {}
        self.rng = streams
        self.ids = ids
        self.days_total = int(days)
        self.days_completed = 0

        day_sc = self.scenario.get("day", {})
        self.money = int(day_sc.get("money", 0))
        self.earned = int(day_sc.get("earned", 0))
        self.reputation = float(day_sc.get("reputation", tuning["quan"]["reputation_initial"]))
        self.upgrades = {k: int(v) for k, v in sorted(day_sc.get("upgrades", {}).items()) if int(v) > 0}
        self.active_upgrades = dict(self.upgrades)

        # Gộp day_plan mặc định với ghi đè từ scenario.day.day_plan
        self.day_plans = {}
        for entry in tuning["day_plan"]:
            self.day_plans[entry["day"]] = {
                "dishes": dict(entry["dishes"]),
                "ingredients": dict(entry["ingredients"]),
            }
        for ov in day_sc.get("day_plan", []):
            dishes = dict(ov["dishes"])
            self.day_plans[ov["day"]] = {
                "dishes": dishes,
                "ingredients": compute_plan_ingredients(dishes, tuning["menu"]),
            }

        self.day = 1
        self.done = False
        self.reason = None
        self.sub = None
        self._init_events = []
        self._start_day(1, self._init_events)

    @property
    def phase(self) -> str:
        return self.sub.phase

    @property
    def phase_tick(self) -> int:
        return self.sub.phase_tick

    @property
    def time_left_ticks(self) -> int:
        return self.sub.time_left_ticks

    def pop_initial_events(self) -> list:
        evs, self._init_events = self._init_events, []
        return evs

    def current_plan(self) -> dict:
        plan = self.day_plans[self.day]
        return {"dishes": dict(plan["dishes"]), "ingredients": dict(plan["ingredients"])}

    def _start_day(self, day_num: int, out_events: list):
        self.day = day_num
        self.active_upgrades = dict(self.upgrades)
        gather_sc = self.scenario.get("gather", {})
        self.sub = GatherSim(
            self.tuning,
            gather_sc,
            self.rng,
            self.ids,
            day=self.day,
            active_upgrades=self.active_upgrades,
            initial_money=self.money,
            initial_earned=self.earned,
            initial_reputation=self.reputation,
            realloc_hold_ids=(day_num > 1),
        )
        out_events.append((self.day, "gather", "day_start", {}))
        out_events.append((self.day, "gather", "day_plan", self.current_plan()))
        out_events.append((self.day, "gather", "phase_start", {}))

    def snapshot(self) -> dict:
        s = self.sub.snapshot()
        s["day"] = self.day
        s["day_plan"] = self.current_plan()
        s["upgrades"] = dict(self.upgrades)
        s["active_upgrades"] = dict(self.active_upgrades)
        return s

    def step(self, inp) -> list:
        """Trả danh sách tuple `(day, phase, name, data)` để Session gắn vỏ event chuẩn v1.2."""
        cur_day = self.day
        cur_phase = self.sub.phase
        raw_events = self.sub.step(inp)
        out = [(cur_day, cur_phase, name, data) for name, data in raw_events]

        if not self.sub.done:
            self.money = self.sub.money
            self.earned = self.sub.earned
            self.reputation = self.sub.reputation
            return out

        if cur_phase == "gather":
            # Bàn giao nguyên cá thể + độ tươi (Fraction chính xác), không hao thêm ở tick chuyển pha
            inv = self.sub.inventory_items()
            quan_sc = self.scenario.get("quan", {})
            plan = self.day_plans[self.day]
            self.sub = QuanSim(
                self.tuning,
                quan_sc,
                self.rng,
                self.ids,
                inventory=inv,
                allowed_dishes=set(plan["dishes"]),
                initial_money=self.money,
                initial_earned=self.earned,
                initial_reputation=self.reputation,
            )
            out.append((self.day, "quan", "phase_start", {}))
        elif cur_phase == "quan":
            self.money = self.sub.money
            self.earned = self.sub.earned
            self.reputation = self.sub.reputation
            leftover = [dict(it) for it in self.sub.stock]
            self.sub = ShopSim(
                self.tuning,
                leftover,
                self.money,
                self.earned,
                self.reputation,
                self.upgrades,
            )
            out.append((self.day, "shop", "phase_start", {}))
        else:  # shop ended
            self.money = self.sub.money
            self.earned = self.sub.earned
            self.reputation = self.sub.reputation
            self.days_completed += 1
            if self.days_completed >= self.days_total:
                self.done = True
                self.reason = "days_complete"
            else:
                self._start_day(self.day + 1, out)

        return out
