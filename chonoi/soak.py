"""Soak headless nhiều ngày (10 Ngày+) bằng bot tất định (Test Contract v1.3).

Cách chạy:
    python3 -m chonoi.soak --seed 7 --days 10 --out soak.json

Mỗi Ngày đi qua `gather -> quan -> shop` trong một tiến trình duy nhất.
Kế hoạch D1–D5 lặp ở Ngày 6–10; tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và id cá thể
tiếp tục xuyên suốt. Ghi nguyên tử `soak.json` gồm `days`, `days_completed`, `crashes`, `results`, `duration_s`.
"""

import argparse
import json
import math
import os
import sys
import tempfile
import time

from .contract import load_contract
from .errors import BadInput
from .ids import IdAllocator, id_key, sort_by_id
from .inputs import InputState
from .rng import Streams
from .sim.day import DaySim
from .sim.quan_orders import oldest_reserved_order


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _dir_toward(cur, target):
    dx = target[0] - cur[0]
    dy = target[1] - cur[1]
    dist = math.hypot(dx, dy)
    if dist <= 1e-6:
        return (0.0, 0.0), 0.0
    return (dx / dist, dy / dist), dist


def _bot_gather_input(sim) -> InputState:
    """Bot lặn & hái tất định: hái đủ 4+ nguyên liệu mặt nước rồi quay về bến cập bến."""
    dock = sim.t["dock_pos"]
    dock_r = sim.t["dock_radius"]
    inter_r = sim.t["interact_radius"]

    # Đủ 4 nguyên liệu hoặc quá 1.200 tick -> bơi về bến và bấm interact
    if len(sim.hold) >= 4 or sim.phase_tick >= 1200:
        mv, dist = _dir_toward(sim.pos, dock)
        if dist <= dock_r * 0.9:
            return InputState((0.0, 0.0), {"interact": True}, {"interact"})
        return InputState(mv, {}, set())

    # Ưu tiên nút hái sẵn sàng ở mặt nước (d=0) gần nhất (an toàn, không đụng Cá Sấu dưới sâu)
    ready_nodes = [n for n in sort_by_id(sim.nodes) if n["regrow_ticks"] == 0]
    if ready_nodes:
        target = min(ready_nodes, key=lambda n: (math.dist(sim.pos, n["pos"]), id_key(n["id"])))
        mv, dist = _dir_toward(sim.pos, target["pos"])
        if dist <= inter_r * 0.9:
            return InputState((0.0, 0.0), {"interact": True}, {"interact"})
        return InputState(mv, {}, set())

    # Không có nút sẵn sàng -> về bến nếu đã có hàng, ngược lại đứng chờ nút hồi
    if sim.hold:
        mv, dist = _dir_toward(sim.pos, dock)
        if dist <= dock_r * 0.9:
            return InputState((0.0, 0.0), {"interact": True}, {"interact"})
        return InputState(mv, {}, set())
    return InputState((0.0, 0.0), {}, set())


def _bot_quan_input(sim) -> InputState:
    """Bot mở quán tất định: giao món trên tay -> nhấc món chín -> nấu đơn cũ nhất."""
    inter_r = sim.t["interact_radius"]

    # 1. Đang bưng món -> đi tới đúng bàn của đơn để phục vụ
    if sim.hand is not None:
        oid = sim.hand["order_id"]
        cust = next((c for c in sim.customers if c["id"] == oid), None)
        if cust is not None:
            tb = next((t for t in sim.tables if t["id"] == cust["table_id"]), None)
            if tb is not None:
                mv, dist = _dir_toward(sim.pos, tb["pos"])
                if dist <= inter_r * 0.9:
                    return InputState((0.0, 0.0), {"interact": True}, {"interact"})
                return InputState(mv, {}, set())

    # 2. Tay trống & có bếp ready -> đi tới bếp ready gần nhất để nhấc món
    ready_stoves = [st for st in sort_by_id(sim.stoves) if st["state"] == "ready"]
    if sim.hand is None and ready_stoves:
        st = min(ready_stoves, key=lambda s: (math.dist(sim.pos, s["pos"]), id_key(s["id"])))
        mv, dist = _dir_toward(sim.pos, st["pos"])
        if dist <= inter_r * 0.9:
            return InputState((0.0, 0.0), {"interact": True}, {"interact"})
        return InputState(mv, {}, set())

    # 3. Có bếp idle & có đơn reserved -> đi tới bếp idle gần nhất để nấu
    idle_stoves = [st for st in sort_by_id(sim.stoves) if st["state"] == "idle"]
    if idle_stoves and oldest_reserved_order(sim.customers) is not None:
        st = min(idle_stoves, key=lambda s: (math.dist(sim.pos, s["pos"]), id_key(s["id"])))
        mv, dist = _dir_toward(sim.pos, st["pos"])
        if dist <= inter_r * 0.9:
            return InputState((0.0, 0.0), {"interact": True}, {"interact"})
        return InputState(mv, {}, set())

    return InputState((0.0, 0.0), {}, set())


def _bot_shop_input(sim) -> InputState:
    """Bot Shop tất định: mua nâng cấp oxygen/hp nếu đủ tiền, rồi đóng Shop."""
    up_cfg = sim.t["upgrades"]
    for key in ("oxygen", "hp"):
        tiers = up_cfg.get(key, [])
        cur = sim.upgrades.get(key, 0)
        if cur < len(tiers) and sim.money >= int(tiers[cur]["price"]):
            return InputState((0.0, 0.0), {"shop_done": True}, {"shop_done"}, buy=key)
    return InputState((0.0, 0.0), {"shop_done": True}, {"shop_done"})


def run_soak(seed: int, days: int) -> dict:
    t0 = time.perf_counter()
    tuning = load_contract()["tuning"]
    mult = tuning["score"]["reputation_multiplier"]
    day_sim = DaySim(tuning, {}, Streams(seed), IdAllocator(), days=days)

    results = []
    crashes = 0
    try:
        while not day_sim.done:
            phase = day_sim.phase
            if phase == "gather":
                inp = _bot_gather_input(day_sim.sub)
            elif phase == "quan":
                inp = _bot_quan_input(day_sim.sub)
            else:
                inp = _bot_shop_input(day_sim.sub)

            evs = day_sim.step(inp)
            for ev_day, ev_phase, ev_name, _ in evs:
                if ev_phase == "shop" and ev_name == "shop_end":
                    rep = round(float(day_sim.reputation), 3)
                    earned = int(day_sim.earned)
                    score = earned + mult * math.floor(day_sim.reputation)
                    results.append({
                        "day": ev_day,
                        "earned": earned,
                        "reputation": rep,
                        "score": score,
                    })
    except Exception:
        crashes += 1

    duration_s = round(time.perf_counter() - t0, 3)
    return {
        "days": days,
        "days_completed": day_sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": duration_s,
    }


def _write_json_atomic(path: str, data: dict):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".soak-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--days", required=True, type=int)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    try:
        if a.days < 1:
            raise BadInput("--days phải là số nguyên >= 1")
        result = run_soak(a.seed, a.days)
        _write_json_atomic(a.out, result)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0 if result["crashes"] == 0 and result["days_completed"] == a.days else 1


if __name__ == "__main__":
    sys.exit(main())
