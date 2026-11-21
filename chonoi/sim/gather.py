"""Buổi sáng — Lặn & Hái (`gather`) đầy đủ theo Test Contract v1.2.

Bao gồm:
  - Di chuyển `[x, d]`, ramp, chặn biên, mặt nước (`d <= surface_depth`), `dive` / `surface`.
  - Độ tươi nguyên liệu cá thể v1.2 (`{id, kind, fresh}`): cấp `I1, I2, ...` tăng liên tục xuyên pha/Ngày,
    hao 0.5/s (1/120 mỗi tick) ở đầu bước cho hàng sẵn có, phát `spoiled` đúng 1 lần theo id khi `< 30`.
  - Oxy, ngạt (`oxygen_empty`, `choke`), ngất (`faint` với `cause` & `lost` mảng cá thể LIFO), hỗ trợ nâng cấp `oxygen`/`hp`.
  - Hái nút mặt nước (`gather` với `amount`, `hold_full`, `node_regrown`) & bắt cá dưới nước (`fish_caught` với `yield`).
  - Đàn cá bơi `1.5 m/s` phản xạ mép, đổi hướng mỗi `fish_turn_ticks` (120) và sinh thêm ở `phase_tick = 360*k` (`fish_spawned`).
  - Cá Sấu Năm Chèo (`M1` từ Ngày 1, `M2` từ Ngày 3): `patrol`, `chase`, `recoil`, `monster_hit` (mất 1 HP + bỏ `floor(giỏ/2)` LIFO + bất tử 90 tick) và `faint(cause="monster")`.
"""

import math

from ..freshness_v12 import (
    decay_items,
    get_freshness_cfg,
    make_item,
    parse_item_list,
    serialize_items_in_order,
    serialize_items_sorted,
)
from ..ids import id_key, sort_by_id
from ..inventory import KINDS_V11, hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"
    _live_mode = False

    def __init__(
        self,
        tuning,
        scenario,
        streams,
        ids,
        day: int = 1,
        active_upgrades=None,
        initial_money: int = 0,
        initial_earned: int = 0,
        initial_reputation=None,
        realloc_hold_ids: bool = False,
    ):
        t = tuning["gather"]
        self.t = t
        self.tuning = tuning
        self.fresh_cfg = get_freshness_cfg(tuning)
        self.rng = streams
        self.ids = ids
        self.day = int(day)
        self.phase_tick = 0

        # Áp nâng cấp đang có hiệu lực (chỉ có từ Ngày kế tiếp sau khi mua ở Shop)
        up = active_upgrades or {}
        oxy_max_s = t["oxygen_max_s"]
        hp_max = t["hp_max"]
        shop_up = tuning.get("shop", {}).get("upgrades", {})
        if up.get("oxygen", 0) > 0 and "oxygen" in shop_up:
            lvl = up["oxygen"]
            oxy_max_s = shop_up["oxygen"][lvl - 1]["oxygen_max_s"]
        if up.get("hp", 0) > 0 and "hp" in shop_up:
            lvl = up["hp"]
            hp_max = shop_up["hp"][lvl - 1]["hp_max"]

        self.oxygen_max = int(round(oxy_max_s * TICK))
        self.hp_max = int(hp_max)

        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", self.hp_max)
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)

        # Giỏ v1.2: mảng cá thể {id, kind, fresh(Fraction)} theo thứ tự nhặt (cuối mảng là mới nhất).
        # Bản live (_live_mode=True) giữ mảng chuỗi kind vì LiveGatherSim tự chạy freshness.py riêng.
        raw_hold = scenario.get("hold", [])
        if self._live_mode:
            self.hold = [it["kind"] if isinstance(it, dict) else it for it in raw_hold]
        else:
            parsed_hold = parse_item_list(raw_hold, allowed_kinds=KINDS_V11, label="gather.hold")
            if realloc_hold_ids:
                # Ngày 2+ trong --mode day: cấp id mới theo thứ tự mảng, giữ nguyên kind và fresh ban đầu
                self.hold = [make_item(ids.new("I"), it["kind"], it["fresh"]) for it in parsed_hold]
            else:
                self.hold = parsed_hold
                for it in self.hold:
                    ids.reserve(it["id"])

        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))

        # Nút hái
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [
            {
                "id": n["id"],
                "kind": n["kind"],
                "pos": [float(c) for c in n["pos"]],
                "regrow_ticks": n.get("regrow_ticks", 0),
            }
            for n in src_nodes
        ]

        # Đàn cá (v1.1/v1.2: random_fish=false tắt cá mặc định, bơi và sinh; khai fish khi random_fish=true vẫn bơi/sinh)
        self.random_fish = scenario.get("random_fish", True)
        if "fish" in scenario:
            src_fish = scenario["fish"]
        elif self.random_fish:
            fi = t["fish_initial"]
            src_fish = self._spawn_initial_fish(t, streams, ids) if isinstance(fi, int) else fi
        else:
            src_fish = []
        self.fish = [
            {
                "id": f["id"],
                "kind": f["kind"],
                "pos": [float(c) for c in f["pos"]],
                "heading_deg": float(f.get("heading_deg", 0.0)),
                "age_ticks": int(f.get("age_ticks", 0)),
            }
            for f in src_fish
        ]

        # Thủy quái (Cá Sấu Năm Chèo M1 từ Ngày 1, M2 từ Ngày 3)
        m_cfg = t.get("monsters", {})
        if "monsters" in scenario:
            src_monsters = scenario["monsters"]
        else:
            src_monsters = [s for s in m_cfg.get("spawns", []) if s.get("from_day", 1) <= self.day]
        self.monsters = [
            {
                "id": m["id"],
                "kind": m["kind"],
                "pos": [float(c) for c in m["pos"]],
                "waypoints": [[float(c) for c in wp] for wp in m["waypoints"]],
                "target_idx": int(m.get("target_idx", 1)),
                "state": m.get("state", "patrol"),
                "state_ticks_left": int(m.get("state_ticks_left", 0)),
                "recoil_dir": [float(c) for c in m["recoil_dir"]] if m.get("recoil_dir") is not None else None,
            }
            for m in src_monsters
        ]

        for coll in (self.nodes, self.fish, self.monsters):
            for e in coll:
                ids.reserve(e["id"])

        self.money = int(initial_money)
        self.earned = int(initial_earned)
        self.reputation = float(
            tuning["quan"]["reputation_initial"] if initial_reputation is None else initial_reputation
        )
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self):
        if self._live_mode:
            return hold_to_items(self.hold)
        return [dict(it) for it in sort_by_id(self.hold)]

    def _serialize_hold(self) -> list:
        if self._live_mode:
            return list(self.hold)
        return serialize_items_in_order(self.hold, spoiled_below=self.fresh_cfg["spoiled_below"])

    def _serialize_lost(self, dropped: list) -> list:
        if self._live_mode:
            return list(dropped)
        return serialize_items_in_order(dropped, spoiled_below=self.fresh_cfg["spoiled_below"])

    def snapshot(self) -> dict:
        return {
            "player": {
                "pos": list(self.pos),
                "vel": list(self.vel),
                "heading_deg": self.heading,
                "oxygen_ticks": self.oxygen_ticks,
                "oxygen_max_ticks": self.oxygen_max,
                "hp": self.hp,
                "hp_max": self.hp_max,
                "zero_oxy_ticks": self.zero_oxy_ticks,
                "invuln_ticks": self.invuln_ticks,
                "catch_cd_ticks": self.catch_cd_ticks,
                "at_surface": self._at_surface(),
            },
            "hold": self._serialize_hold(),
            "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [
                {
                    "id": n["id"],
                    "pos": list(n["pos"]),
                    "kind": n["kind"],
                    "ready": n["regrow_ticks"] == 0,
                    "regrow_ticks": n["regrow_ticks"],
                }
                for n in sort_by_id(self.nodes)
            ],
            "fish": [
                {
                    "id": f["id"],
                    "pos": list(f["pos"]),
                    "kind": f["kind"],
                    "heading_deg": f["heading_deg"],
                    "age_ticks": f.get("age_ticks", 0),
                }
                for f in sort_by_id(self.fish)
            ],
            "monsters": [
                {
                    "id": m["id"],
                    "kind": m["kind"],
                    "pos": list(m["pos"]),
                    "waypoints": [list(wp) for wp in m["waypoints"]],
                    "target_idx": m["target_idx"],
                    "state": m["state"],
                    "state_ticks_left": m["state_ticks_left"],
                    "recoil_dir": list(m["recoil_dir"]) if m["recoil_dir"] is not None else None,
                }
                for m in sort_by_id(self.monsters)
            ],
        }

    # --- một bước (thứ tự chính xác theo Contract v1.2) -----------------------
    def step(self, inp):
        events = []
        # 1. Đồng hồ, cooldown, giảm bất tử, hồi nút và hao tươi hàng có sẵn ở ĐẦU bước
        self.phase_tick += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        if not self._live_mode:
            decay_items(
                self.hold,
                self.fresh_cfg["gather_decay_per_s"],
                self.fresh_cfg["spoiled_below"],
                "hold",
                events,
            )

        # 2. Bơi, chặn mép, dive/surface, oxy và ngạt
        was_surface = self._at_surface()
        self._move(inp)
        at_surface = self._at_surface()
        if was_surface != at_surface:
            events.append(("surface" if at_surface else "dive", {"pos": list(self.pos)}))

        old_oxygen = self.oxygen_ticks
        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + self.t["oxygen_refill_per_tick"])
            self.zero_oxy_ticks = 0
        else:
            self.oxygen_ticks = max(0, self.oxygen_ticks - 1)
            if old_oxygen > 0 and self.oxygen_ticks == 0:
                events.append(("oxygen_empty", {"oxygen_ticks": 0}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= self.t["choke_interval_ticks"]:
                    self.zero_oxy_ticks = 0
                    self.hp = max(0, self.hp - 1)
                    events.append(("choke", {"hp": self.hp}))
                    if self.hp == 0:
                        self._faint("choke", events)
                        return events

        # 3. Cập nhật thủy quái theo id rồi xét tối đa một hit
        if self._step_monsters(events):
            return events

        # 4. Tương tác: bến trước, rồi hái nút ở mặt nước
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                candidates = [
                    n for n in sort_by_id(self.nodes)
                    if n["regrow_ticks"] == 0 and math.dist(self.pos, n["pos"]) <= self.t["interact_radius"]
                ]
                if candidates:
                    node = min(candidates, key=lambda n: (math.dist(self.pos, n["pos"]), id_key(n["id"])))
                    amount = self.t["node_yield"]
                    if self._collect("gather", "node_id", node["id"], node["kind"], amount, events):
                        node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {"node_id": node["id"], "kind": node["kind"], "amount": amount}))

        # 5. Bắt cá (dùng vị trí cá TRƯỚC khi cá bơi)
        if inp.pressed("catch"):
            if not self._at_surface() and self.catch_cd_ticks == 0:
                candidates = [
                    f for f in sort_by_id(self.fish)
                    if math.dist(self.pos, f["pos"]) <= self.t["catch_radius"]
                ]
                if candidates:
                    fish = min(candidates, key=lambda f: (math.dist(self.pos, f["pos"]), id_key(f["id"])))
                    count = self.t["fish_yield"][fish["kind"]]
                    if self._collect("catch", "fish_id", fish["id"], fish["kind"], count, events):
                        self.fish.remove(fish)
                        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                        events.append(("fish_caught", {"fish_id": fish["id"], "kind": fish["kind"], "yield": count}))

        # 6. Hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events

        # 7. Nếu còn giờ và bật random_fish: đàn cá bơi rồi sinh cá theo lịch
        if self.random_fish and "fish_speed" in self.t:
            self._swim_fish()
            self._spawn_fish_if_due(events)

        return events

    # --- thủy quái (TICKET-02 mục 1.2) ----------------------------------------
    def _step_monsters(self, events) -> bool:
        m_cfg = self.t.get("monsters")
        if not m_cfg or not self.monsters:
            return False
        species_map = m_cfg["species"]
        x_lo, x_hi = self.t["bounds"]["x"]
        eligible = []

        for m in sort_by_id(self.monsters):
            spec = species_map[m["kind"]]
            d_lo, d_hi = spec["depths"]
            if m["state"] == "recoil":
                rdir = m["recoil_dir"] or [1.0, 0.0]
                step_d = spec["recoil_dist"] / TICK
                m["pos"][0] = min(x_hi, max(x_lo, m["pos"][0] + rdir[0] * step_d))
                m["pos"][1] = min(d_hi, max(d_lo, m["pos"][1] + rdir[1] * step_d))
                m["state_ticks_left"] = max(0, m["state_ticks_left"] - 1)
                if m["state_ticks_left"] == 0:
                    m["state"] = "patrol"
                    m["recoil_dir"] = None
                continue

            dist_p = math.dist(m["pos"], self.pos)
            in_depth = self.pos[1] >= d_lo
            if m["state"] == "patrol":
                if in_depth and dist_p <= spec["detect_radius"]:
                    m["state"] = "chase"
            elif m["state"] == "chase":
                if (not in_depth) or dist_p > spec["exit_radius"]:
                    m["state"] = "patrol"

            if m["state"] == "chase":
                dx, dd = self.pos[0] - m["pos"][0], self.pos[1] - m["pos"][1]
                dist = math.hypot(dx, dd)
                if dist > 0:
                    step_d = min(dist, spec["chase_speed"] / TICK)
                    m["pos"][0] += (dx / dist) * step_d
                    m["pos"][1] += (dd / dist) * step_d
            else:  # patrol
                wp = m["waypoints"][m["target_idx"]]
                dx, dd = wp[0] - m["pos"][0], wp[1] - m["pos"][1]
                dist = math.hypot(dx, dd)
                step_d = spec["patrol_speed"] / TICK
                if dist <= step_d:
                    m["pos"][0], m["pos"][1] = float(wp[0]), float(wp[1])
                    m["target_idx"] = 1 - m["target_idx"]
                else:
                    m["pos"][0] += (dx / dist) * step_d
                    m["pos"][1] += (dd / dist) * step_d

            m["pos"][0] = min(x_hi, max(x_lo, m["pos"][0]))
            m["pos"][1] = min(d_hi, max(d_lo, m["pos"][1]))
            eligible.append((m, spec))

        # Xét tối đa một hit nếu hết bất tử
        if self.invuln_ticks > 0:
            return False
        hits = []
        for m, spec in eligible:
            if self.pos[1] >= spec["depths"][0]:
                dist = math.dist(self.pos, m["pos"])
                if dist <= spec["hit_radius"]:
                    hits.append((dist, id_key(m["id"]), m, spec))
        if not hits:
            return False

        _, _, m, spec = min(hits, key=lambda item: item[:2])
        self.hp = max(0, self.hp - 1)
        drop_count = math.floor(len(self.hold) * m_cfg.get("loss_ratio", 0.5))
        dropped = [self.hold.pop() for _ in range(drop_count)]
        lost = self._serialize_lost(dropped)
        self.invuln_ticks = int(m_cfg.get("invuln_ticks", 90))

        rx, rd = m["pos"][0] - self.pos[0], m["pos"][1] - self.pos[1]
        rn = math.hypot(rx, rd)
        m["recoil_dir"] = [rx / rn, rd / rn] if rn > 0 else [1.0, 0.0]
        m["state"] = "recoil"
        m["state_ticks_left"] = int(spec["recoil_ticks"])

        events.append(("monster_hit", {"monster_id": m["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp == 0:
            self._faint("monster", events)
            return True
        return False

    # --- cá bơi & sinh cá theo lịch (TICKET-02 mục 1.1) ----------------------
    def _swim_fish(self):
        step_dist = self.t["fish_speed"] / TICK
        turn_ticks = self.t["fish_turn_ticks"]
        x_lo, x_hi = self.t["fish_x"]
        depths_map = self.t["fish_depths"]
        default_d = [self.t["surface_depth"] + 0.5, self.t["bounds"]["d"][1]]
        turn_rng = self.rng.get("fish_turn")

        for f in sort_by_id(self.fish):
            f["age_ticks"] = f.get("age_ticks", 0) + 1
            if turn_ticks > 0 and f["age_ticks"] % turn_ticks == 0:
                f["heading_deg"] = turn_rng.uniform(0.0, 360.0)
            rad = math.radians(f["heading_deg"])
            vx, vd = math.cos(rad), math.sin(rad)
            d_lo, d_hi = depths_map.get(f["kind"], default_d)

            nx = f["pos"][0] + vx * step_dist
            nd = f["pos"][1] + vd * step_dist

            while nx < x_lo or nx > x_hi:
                if nx < x_lo:
                    nx = 2.0 * x_lo - nx
                    vx = -vx
                elif nx > x_hi:
                    nx = 2.0 * x_hi - nx
                    vx = -vx
            while nd < d_lo or nd > d_hi:
                if nd < d_lo:
                    nd = 2.0 * d_lo - nd
                    vd = -vd
                elif nd > d_hi:
                    nd = 2.0 * d_hi - nd
                    vd = -vd

            f["pos"][0], f["pos"][1] = nx, nd
            f["heading_deg"] = math.degrees(math.atan2(vd, vx)) % 360.0

    def _spawn_fish_if_due(self, events):
        spawn_ticks = self.t.get("fish_spawn_ticks")
        if not spawn_ticks or self.phase_tick % spawn_ticks != 0:
            return
        if len(self.fish) >= self.t.get("fish_max", 12):
            return
        clearance = self.t.get("fish_spawn_clearance", 1.0)
        spawn_x = self.t["fish_spawn_x"]
        spawn_depths = self.t["fish_spawn_depths"]
        weights = self.t["fish_weights"]
        avail = {}
        for kind in sorted(spawn_depths):
            pts = [
                (x, d)
                for x in spawn_x
                for d in spawn_depths[kind]
                if all(math.dist((x, d), other["pos"]) > clearance for other in self.fish)
            ]
            if pts:
                avail[kind] = pts
        if not avail:
            return
        rng = self.rng.get("fish_spawn")
        picked = self._weighted_choice(sorted(avail), weights, rng)
        x, d = rng.choice(avail[picked])
        fid = self.ids.new("F")
        new_fish = {
            "id": fid,
            "kind": picked,
            "pos": [float(x), float(d)],
            "heading_deg": rng.uniform(0.0, 360.0),
            "age_ticks": 0,
        }
        self.fish.append(new_fish)
        events.append(("fish_spawned", {"id": fid, "kind": picked, "pos": [float(x), float(d)]}))

    # --- tiện ích -------------------------------------------------------------
    @staticmethod
    def _weighted_choice(species, weights, rng):
        total = sum(weights[k] for k in species)
        r = rng.random() * total
        acc = 0.0
        for k in species:
            acc += weights[k]
            if r <= acc:
                return k
        return species[-1]

    @classmethod
    def _spawn_initial_fish(cls, t, streams, ids):
        rng = streams.get("fish_spawn")
        spawn_x = t["fish_spawn_x"]
        spawn_depths = t["fish_spawn_depths"]
        weights = t["fish_weights"]
        used_pos = set()
        out = []
        for _ in range(t["fish_initial"]):
            avail = {}
            for kind in sorted(spawn_depths):
                pts = [(x, d) for x in spawn_x for d in spawn_depths[kind] if (x, d) not in used_pos]
                if pts:
                    avail[kind] = pts
            if not avail:
                break
            picked = cls._weighted_choice(sorted(avail), weights, rng)
            x, d = rng.choice(avail[picked])
            used_pos.add((x, d))
            out.append({
                "id": ids.new("F"),
                "kind": picked,
                "pos": [float(x), float(d)],
                "heading_deg": rng.uniform(0.0, 360.0),
                "age_ticks": 0,
            })
        return out

    def _faint(self, cause: str, events):
        dropped = list(reversed(self.hold))
        self.hold.clear()
        lost = self._serialize_lost(dropped)
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    def _collect(self, action: str, id_field: str, entity_id: str, kind: str, count: int, events) -> bool:
        free = self.t["hold_capacity"] - len(self.hold)
        if count > free:
            events.append(("hold_full", {"action": action, id_field: entity_id, "required": count, "free": free}))
            return False
        if self._live_mode:
            self.hold.extend([kind] * count)
        else:
            init_fresh = self.fresh_cfg["initial"]
            for _ in range(count):
                self.hold.append(make_item(self.ids.new("I"), kind, init_fresh))
        return True

    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        if self._live_mode:
            inv_payload = self.inventory_items()
        else:
            inv_payload = serialize_items_sorted(self.hold, spoiled_below=self.fresh_cfg["spoiled_below"])
        events.append(("gather_end", {"reason": reason, "inventory": {"items": inv_payload}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])
