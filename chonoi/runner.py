"""Vòng tick (Contract B v1.0 / v1.1): hỗ trợ `gather`, `quan`, `day` và `pause`/`resumed`.

Thứ tự ghi: (tick 0 event nếu `day`) -> snapshot tick 0 -> mỗi bước: event theo thứ tự xử lý rồi snapshot
(nếu tới lượt hoặc buổi/lượt kết thúc) -> dòng `end`. Mỗi tick tối đa một snapshot.
"""

import math

from .ids import IdAllocator
from .inputs import InputPlayer
from .inventory import write_inventory
from .jsonl import JsonlWriter
from .rng import Streams
from .sim.day import DaySim
from .sim.gather import GatherSim
from .sim.quan import QuanSim


def build_sim(mode, tuning, scenario, seed, inventory, days=1):
    streams, ids = Streams(seed), IdAllocator()
    if mode == "gather":
        return GatherSim(tuning, scenario, streams, ids)
    if mode == "day":
        return DaySim(tuning, scenario, streams, ids, days=days)
    return QuanSim(tuning, scenario, streams, ids, inventory=inventory)


def _common(sim, tick, sim_tick, phase_tick, tuning, state):
    mult = tuning["score"]["reputation_multiplier"]
    return {
        "type": "snapshot",
        "tick": tick,
        "sim_tick": sim_tick,
        "mode": sim.mode,
        "phase": sim.phase,
        "phase_tick": phase_tick,
        "state": state,
        "time_left_ticks": sim.time_left_ticks,
        "money": sim.money,
        "earned": sim.earned,
        "reputation": sim.reputation,
        "score": sim.earned + mult * math.floor(sim.reputation),
    }


class Session:
    """Một lượt chơi: dựng sim, bước từng tick (hỗ trợ pause), lấy snapshot / dòng end."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, days=1):
        self.mode = mode
        self.tuning = tuning
        self.sim = build_sim(mode, tuning, scenario, seed, inventory, days=days)
        self.tick = 0
        self.sim_tick = 0
        self.paused = False

    @property
    def done(self) -> bool:
        return self.sim.done

    def _phase_tick(self) -> int:
        return getattr(self.sim, "phase_tick", self.sim_tick)

    def _event_row(self, tick, phase, name, data, day=None) -> dict:
        row = {"type": "event", "tick": tick, "phase": phase, "name": name, "data": data}
        if day is not None:
            row["day"] = day
        return row

    def pop_initial_events(self) -> list:
        if hasattr(self.sim, "pop_initial_events"):
            return [
                self._event_row(0, phase, name, data, day=day)
                for day, phase, name, data in self.sim.pop_initial_events()
            ]
        return []

    def snapshot(self) -> dict:
        state = "finished" if self.sim.done else ("paused" if self.paused else "playing")
        s = _common(self.sim, self.tick, self.sim_tick, self._phase_tick(), self.tuning, state)
        s.update(self.sim.snapshot())
        return s

    def step(self, inp) -> list:
        """Chạy một bước ngoài với `inp`; trả danh sách dòng event tại tick = k + 1."""
        self.tick += 1
        rows = []
        day_val = self.sim.day if self.mode == "day" else None

        # Xét cạnh `pause` trước (Contract v1.1 mục 4.2)
        if inp.pressed("pause"):
            if not self.paused:
                self.paused = True
                rows.append(self._event_row(self.tick, self.sim.phase, "paused", {}, day=day_val))
                return rows
            self.paused = False
            rows.append(self._event_row(self.tick, self.sim.phase, "resumed", {}, day=day_val))
        elif self.paused:
            return rows

        # Chạy một bước gameplay
        self.sim_tick += 1
        if self.mode == "day":
            for ev_day, ev_phase, name, data in self.sim.step(inp):
                rows.append(self._event_row(self.tick, ev_phase, name, data, day=ev_day))
        else:
            for name, data in self.sim.step(inp):
                rows.append(self._event_row(self.tick, self.sim.phase, name, data))
        return rows

    def end_row(self) -> dict:
        sim = self.sim
        state = "finished" if sim.done else ("paused" if self.paused else "playing")
        score = _common(sim, self.tick, self.sim_tick, self._phase_tick(), self.tuning, state)["score"]
        row = {
            "type": "end",
            "ticks": self.tick,
            "sim_tick": self.sim_tick,
            "mode": sim.mode,
            "state": state,
            "reason": sim.reason if sim.done else "tick_limit",
            "money": sim.money,
            "earned": sim.earned,
            "reputation": sim.reputation,
            "score": score,
        }
        if self.mode == "day":
            row["days_completed"] = sim.days_completed
        return row

    def write_inventory_if_done(self, inventory_out):
        """File kho: ghi MỘT lần khi có gather_end; chưa kết thúc thì giữ nguyên file đích."""
        if self.mode == "gather" and self.sim.done and inventory_out:
            write_inventory(inventory_out, self.sim.inventory_items())


def run(mode, tuning, scenario, seed, frames, ticks, out_path, snapshot_every, inventory=None, inventory_out=None, days=1):
    sess = Session(mode, tuning, scenario, seed, inventory, days=days)
    player = InputPlayer(frames)
    w = JsonlWriter(out_path)
    try:
        for row in sess.pop_initial_events():
            w.write(row)
        w.write(sess.snapshot())  # tick 0: sau khi dựng scenario, trước mọi input
        last_snapped = 0
        while sess.tick < ticks and not sess.done:
            prev_phase = (getattr(sess.sim, "day", None), sess.sim.phase)
            inp = player.advance(sess.tick)  # bước k đọc input có tick == k
            for row in sess.step(inp):
                w.write(row)
            cur_phase = (getattr(sess.sim, "day", None), sess.sim.phase)
            if sess.tick % snapshot_every == 0 or sess.done or cur_phase != prev_phase:
                w.write(sess.snapshot())
                last_snapped = sess.tick
        if last_snapped != sess.tick:
            w.write(sess.snapshot())
        w.write(sess.end_row())
    finally:
        w.close()
    sess.write_inventory_if_done(inventory_out)
    return sess.sim
