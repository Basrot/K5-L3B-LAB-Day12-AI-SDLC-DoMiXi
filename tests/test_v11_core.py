"""Bộ test đầy đủ cho các tính năng lõi Contract v1.1/v1.2 (Gather cá bơi/sinh, Cá Sấu, --mode day, Shop, pause).

Đã cập nhật fixture `hold`, `lost` LIFO và `gather_end.data.inventory` sang kho cá thể `{id, kind, fresh}` của Contract v1.2.
"""

import time
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.runner import Session

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def inp(*edges, move=(0.0, 0.0), buy=None):
    return InputState(move, {}, set(edges), buy=buy)


def mk_hold(kinds: list, fresh=100, start_idx=1) -> list:
    return [{"id": f"I{start_idx + i}", "kind": k, "fresh": fresh} for i, k in enumerate(kinds)]


class GatherV11PayloadsFishAndMonsters(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_gather_event_payloads_match_prd_section_e(self):
        """Rà chuẩn payload gather/fish_caught/hold_full/oxygen_empty/faint LIFO v1.2."""
        cap = self.t["gather"]["hold_capacity"]
        sc = {
            "player": {"pos": [12, 0]},
            "hold": mk_hold(["ca_loc"] * (cap - 1)),
            "random_fish": False,
            "monsters": [],
        }
        s = Session("gather", self.t, sc, 1)
        ev1 = s.step(inp("interact"))
        self.assertEqual(ev1[0]["name"], "gather")
        self.assertEqual(ev1[0]["data"], {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})
        # Cá thể mới hái có id tiếp nối (I12) và fresh=100 chưa hao ở bước hái
        self.assertEqual(s.sim.hold[-1]["id"], f"I{cap}")
        self.assertEqual(s.sim.hold[-1]["fresh"], 100)

        # Giờ giỏ đã đầy -> hái nút N2 phát hold_full đủ action/node_id/required/free
        s.sim.pos = [28.0, 0.0]
        ev2 = s.step(inp("interact"))
        self.assertEqual(ev2[0]["name"], "hold_full")
        self.assertEqual(ev2[0]["data"], {"action": "gather", "node_id": "N2", "required": 1, "free": 0})

        # fish_caught (yield) & hold_full (catch)
        sc_f = {
            "player": {"pos": [15, 5]},
            "hold": mk_hold(["ca_loc"] * (cap - 2)),
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15, 5]}],
            "random_fish": False,
            "monsters": [],
        }
        sf = Session("gather", self.t, sc_f, 1)
        ev_full = sf.step(inp("catch"))
        self.assertEqual(ev_full[0]["name"], "hold_full")
        self.assertEqual(ev_full[0]["data"], {"action": "catch", "fish_id": "F1", "required": 3, "free": 2})
        self.assertEqual(sf.sim.catch_cd_ticks, 0)

        sf.sim.hold.pop()  # chừa đủ 3 ô
        ev_caught = sf.step(inp("catch"))
        self.assertEqual(ev_caught[0]["name"], "fish_caught")
        self.assertEqual(ev_caught[0]["data"], {"fish_id": "F1", "kind": "ca_linh", "yield": 3})

        # oxygen_empty + choke + faint (lost là mảng cá thể theo thứ tự LIFO)
        sc_oxy = {
            "player": {"pos": [20, 5], "oxygen_ticks": 1, "hp": 1},
            "hold": mk_hold(["ca_loc", "bong_sung", "keo_neo"]),
            "random_fish": False,
            "monsters": [],
        }
        so = Session("gather", self.t, sc_oxy, 1)
        ev_empty = so.step(inp())
        self.assertEqual(ev_empty[0]["name"], "oxygen_empty")
        self.assertEqual(ev_empty[0]["data"], {"oxygen_ticks": 0})
        # Oxy chạm 0 ở bước 1 -> ngạt lần đầu ở bước 60 (60 bước hao 60 * 0.5/60 = 0.5 -> fresh = 99.5 chính xác!)
        for _ in range(58):
            self.assertEqual(so.step(inp()), [])
        ev_faint = so.step(inp())
        self.assertEqual([e["name"] for e in ev_faint], ["choke", "faint", "gather_end"])
        self.assertEqual(ev_faint[1]["data"], {
            "cause": "choke",
            "lost": [
                {"id": "I3", "kind": "keo_neo", "fresh": 99.5},
                {"id": "I2", "kind": "bong_sung", "fresh": 99.5},
                {"id": "I1", "kind": "ca_loc", "fresh": 99.5},
            ],
            "hp": 0,
        })
        self.assertEqual(ev_faint[2]["data"], {"reason": "fainted", "inventory": {"items": []}})

    def test_fish_swim_reflection_turn_and_scheduled_spawn(self):
        """Cá bơi 1.5 m/s, phản xạ mép, đổi hướng ở bước bơi 120 và sinh thêm ở phase_tick=360."""
        sc = {
            "player": {"pos": [2, 0]},
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [95.99, 5.0], "heading_deg": 0.0, "age_ticks": 0}],
            "random_fish": True,
            "monsters": [],
        }
        s = Session("gather", self.t, sc, 11)
        s.step(inp())
        f = s.sim.fish[0]
        self.assertAlmostEqual(f["pos"][0], 95.985, places=3)
        self.assertAlmostEqual(f["heading_deg"], 180.0, places=3)
        self.assertEqual(f["age_ticks"], 1)

        spawned = []
        for _ in range(359):
            for e in s.step(inp()):
                if e["name"] == "fish_spawned":
                    spawned.append(e)
        self.assertEqual(len(spawned), 1)
        self.assertEqual(spawned[0]["tick"], 360)
        self.assertEqual(len(s.sim.fish), 2)

        sc_static = {
            "player": {"pos": [2, 0]},
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [50.0, 5.0], "heading_deg": 0.0}],
            "random_fish": False,
            "monsters": [],
        }
        s2 = Session("gather", self.t, sc_static, 11)
        for _ in range(360):
            self.assertEqual(s2.step(inp()), [])
        self.assertEqual(s2.sim.fish[0]["pos"], [50.0, 5.0])
        self.assertEqual(len(s2.sim.fish), 1)

    def test_crocodile_patrol_chase_hit_lifo_loss_recoil_and_monster_faint(self):
        """Cá Sấu M1 tuần tra, đuổi ở d>=10, chạm mất 1 HP + rớt floor(giỏ/2) cá thể LIFO + recoil + ngất monster."""
        sc = {
            "player": {"pos": [60.0, 24.0], "hp": 2},
            "hold": mk_hold(["ca_loc", "bong_sung", "ca_keo", "keo_neo", "ca_linh"]),  # 5 ô -> rớt floor(5/2)=2 (LIFO)
            "random_fish": False,
            "monsters": [{
                "id": "M1", "kind": "ca_sau", "pos": [60.0, 24.0],
                "waypoints": [[60.0, 24.0], [64.0, 24.0]], "target_idx": 1, "state": "patrol",
            }],
        }
        s = Session("gather", self.t, sc, 1)
        ev1 = s.step(inp())
        self.assertEqual([e["name"] for e in ev1], ["monster_hit"])
        self.assertEqual(ev1[0]["data"]["monster_id"], "M1")
        self.assertEqual(ev1[0]["data"]["hp"], 1)
        self.assertEqual(ev1[0]["data"]["lost"], [
            {"id": "I5", "kind": "ca_linh", "fresh": 99.992},
            {"id": "I4", "kind": "keo_neo", "fresh": 99.992},
        ])
        self.assertEqual([it["id"] for it in s.sim.hold], ["I1", "I2", "I3"])
        self.assertEqual(s.sim.invuln_ticks, 90)
        self.assertEqual(s.sim.monsters[0]["state"], "recoil")
        self.assertEqual(s.sim.monsters[0]["state_ticks_left"], 60)
        self.assertEqual(s.sim.monsters[0]["recoil_dir"], [1.0, 0.0])

        x_before = s.sim.monsters[0]["pos"][0]
        for _ in range(60):
            evs = s.step(inp())
            self.assertNotIn("monster_hit", [e["name"] for e in evs])
        self.assertAlmostEqual(s.sim.monsters[0]["pos"][0], x_before + 2.0, places=3)
        self.assertEqual(s.sim.monsters[0]["state"], "patrol")

        # Chờ hết bất tử rồi để Cá Sấu chạm lần 2 (bước 62: 62/120 = 0.51666 -> 99.483)
        s.sim.invuln_ticks = 0
        s.sim.pos = list(s.sim.monsters[0]["pos"])
        ev2 = s.step(inp())
        self.assertEqual([e["name"] for e in ev2], ["monster_hit", "faint", "gather_end"])
        self.assertEqual(ev2[0]["data"]["lost"], [{"id": "I3", "kind": "ca_keo", "fresh": 99.483}])
        self.assertEqual(ev2[1]["data"], {
            "cause": "monster",
            "lost": [
                {"id": "I2", "kind": "bong_sung", "fresh": 99.483},
                {"id": "I1", "kind": "ca_loc", "fresh": 99.483},
            ],
            "hp": 0,
        })
        self.assertEqual(ev2[2]["data"], {"reason": "fainted", "inventory": {"items": []}})


class DayModeShopAndPauseV11(unittest.TestCase):
    def test_day_cli_flags_and_multi_day_shop_upgrade_activation(self):
        """Chạy `--mode day --days 2` hộp đen: mua nâng cấp Shop + cấp id mới cho hold Ngày 2."""
        with Workdir() as w:
            self.assertEqual(run_headless("--mode", "gather", "--seed", "1", "--days", "1", "--ticks", "0", "--out", w.path("b1.jsonl"))[0], 2)
            self.assertEqual(run_headless("--mode", "day", "--seed", "1", "--days", "6", "--ticks", "0", "--out", w.path("b2.jsonl"))[0], 2)

            sc = write_json(w.path("day.json"), {
                "day": {"money": 450, "earned": 450},
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                    "random_fish": False,
                    "monsters": [],
                },
                "quan": {"time_left_ticks": 2, "random_customers": False},
            })
            inp_file = write_json(w.path("in.json"), frames(
                {"tick": 0, "interact": True},
                {"tick": 1, "interact": False},
                {"tick": 3, "buy": "oxygen"},
                {"tick": 4, "buy": "hp", "shop_done": True},
                {"tick": 5, "shop_done": False, "interact": True},
                {"tick": 6, "interact": False},
                {"tick": 8, "shop_done": True},
            ))
            out = w.path("day2.jsonl")
            code, err = run_headless("--mode", "day", "--days", "2", "--seed", "7",
                                     "--scenario", sc, "--inputs", inp_file, "--ticks", "20",
                                     "--snapshot-every", "1", "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)

            t0_evs = [r for r in rows if r["type"] == "event" and r["tick"] == 0]
            self.assertEqual([e["name"] for e in t0_evs], ["day_start", "day_plan", "phase_start"])
            self.assertEqual(t0_evs[1]["day"], 1)

            bought = events(rows, "bought")
            self.assertEqual(len(bought), 2)
            self.assertEqual(bought[0]["data"], {"upgrade": "oxygen", "level": 1, "price": 200, "money": 250})
            self.assertEqual(bought[1]["data"], {"upgrade": "hp", "level": 1, "price": 250, "money": 0})

            snaps = {s["tick"]: s for s in snapshots(rows)}
            # Ngày 1 tick 0 giữ nguyên id I1 từ scenario.gather.hold
            self.assertEqual(snaps[0]["hold"], [{"id": "I1", "kind": "ca_loc", "fresh": 100}])
            # Tick 3 (vào Shop) và tick 4 (sau 1 tick Shop): hàng ở Shop KHÔNG hao tươi!
            self.assertEqual(snaps[3]["phase"], "shop")
            self.assertEqual(snaps[4]["phase"], "shop")
            self.assertEqual(snaps[3]["stock"], snaps[4]["stock"])
            self.assertEqual(snaps[4]["upgrades"], {"oxygen": 1})
            self.assertEqual(snaps[4]["active_upgrades"], {})
            self.assertEqual(snaps[4]["earned"], 450)

            # Snapshot tick 5 (Ngày 2 gather): active_upgrades áp dụng & hold Ngày 2 được cấp id mới I2!
            self.assertEqual(snaps[5]["day"], 2)
            self.assertEqual(snaps[5]["phase"], "gather")
            self.assertEqual(snaps[5]["phase_tick"], 0)
            self.assertEqual(snaps[5]["hold"], [{"id": "I2", "kind": "ca_loc", "fresh": 100}])
            self.assertEqual(snaps[5]["active_upgrades"], {"hp": 1, "oxygen": 1})
            self.assertEqual(snaps[5]["player"]["oxygen_max_ticks"], 2700)
            self.assertEqual(snaps[5]["player"]["hp_max"], 4)

            end = rows[-1]
            self.assertEqual(end["type"], "end")
            self.assertEqual(end["reason"], "days_complete")
            self.assertEqual(end["days_completed"], 2)
            self.assertEqual(end["money"], 0)
            self.assertEqual(end["earned"], 450)

    def test_shop_buy_failed_reasons_and_pause_freezes_timers(self):
        """Kiểm buy_failed (funds/max_level/unknown) và pause đóng băng sim_tick/phase_tick/timer."""
        with Workdir() as w:
            sc = write_json(w.path("d.json"), {
                "day": {"money": 0, "earned": 0, "upgrades": {"oxygen": 2}},
                "gather": {"random_fish": False, "monsters": []},
                "quan": {"time_left_ticks": 1, "random_customers": False},
            })
            inp_file = write_json(w.path("in.json"), frames(
                {"tick": 0, "pause": True},
                {"tick": 1, "pause": False, "interact": True},
                {"tick": 2, "pause": True},
                {"tick": 3, "pause": False, "interact": False},
                {"tick": 4, "interact": True},
                {"tick": 5, "interact": False},
                {"tick": 6, "buy": "oxygen"},
                {"tick": 7, "buy": "hp"},
                {"tick": 8, "buy": "unknown_item"},
                {"tick": 9, "pause": True},
                {"tick": 10, "pause": False, "buy": "hp"},
                {"tick": 11, "pause": True, "shop_done": True},
            ))
            out = w.path("p.jsonl")
            code, err = run_headless("--mode", "day", "--days", "1", "--seed", "1",
                                     "--scenario", sc, "--inputs", inp_file, "--ticks", "20",
                                     "--snapshot-every", "1", "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            snaps = {s["tick"]: s for s in snapshots(rows)}

            self.assertEqual(snaps[1]["state"], "paused")
            self.assertEqual(snaps[1]["sim_tick"], 0)
            self.assertEqual(snaps[2]["state"], "paused")
            self.assertEqual(snaps[2]["sim_tick"], 0)
            self.assertEqual(snaps[3]["state"], "playing")
            self.assertEqual(snaps[3]["sim_tick"], 1)

            fails = [e["data"] for e in events(rows, "buy_failed")]
            self.assertEqual(fails, [
                {"action": "oxygen", "reason": "max_level"},
                {"action": "hp", "reason": "funds"},
                {"action": "unknown_item", "reason": "unknown"},
            ])
            self.assertEqual(rows[-1]["reason"], "days_complete")

    def test_full_day_22200_ticks_deterministic_and_under_performance_budget(self):
        """Một ngày trọn vẹn không pause (22.200 tick) chạy nhanh << 20s và tất định từng byte."""
        with Workdir() as w:
            t0 = time.perf_counter()
            for i in (1, 2):
                code, err = run_headless("--mode", "day", "--days", "1", "--seed", "42",
                                         "--ticks", "22200", "--snapshot-every", "1000",
                                         "--out", w.path(f"d{i}.jsonl"))
                self.assertEqual(code, 0, err)
            elapsed = (time.perf_counter() - t0) / 2.0
            self.assertLess(elapsed, 10.0, f"1 ngày headless quá chậm: {elapsed:.2f}s")
            with open(w.path("d1.jsonl"), "rb") as a, open(w.path("d2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())
            rows = read_jsonl(w.path("d1.jsonl"))
            self.assertEqual(rows[-1]["reason"], "days_complete")
            self.assertEqual(rows[-1]["days_completed"], 1)


if __name__ == "__main__":
    unittest.main()
