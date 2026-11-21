"""Bộ test cho Lát 3 (Người 3 — khách, giữ chỗ nguyên liệu, kiên nhẫn, dựng fixture & kiểm mâu thuẫn).

Bao gồm:
  - N3-01: Sinh khách theo `phase_tick`, chọn bàn trống id nhỏ nhất, `random_customers: false`, không sinh khi hết ca/hết bàn.
  - N3-02: Kho khả dụng = tồn vật lý - giữ chỗ, không giữ trùng, `no_dish`, chọn món tất định qua `Streams`, helper tiêu nguyên liệu cho Người 4.
  - N3-03: Các trạng thái đơn `reserved/assigned/unfulfillable/served`, đếm ngược kiên nhẫn, rời bàn (`patience` / `closing`) & nhả giữ / dọn món.
  - N3-04: Dựng fixture hợp lệ và từ chối mọi mâu thuẫn mức luật với mã thoát 2 TRƯỚC khi ghi JSONL.
"""

import copy
import os
import unittest

from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.runner import Session
from chonoi.sim.quan_orders import consume_order_for_cooking, oldest_reserved_order

from helpers import Workdir, events, read_jsonl, run_headless, snapshots, write_json


def idle_inp():
    return InputState((0.0, 0.0), {}, set())


class QuanCustomerSpawnAndReservation(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_n3_01_spawn_schedule_and_first_tick_patience(self):
        """Khách đến đúng `first_customer_tick`, `order_tick == phase_tick`, kiên nhẫn bắt đầu giảm ở bước SAU."""
        s = Session("quan", self.t, {"stock": {"ca_loc": 2}}, 7)
        first = self.t["quan"]["first_customer_tick"]
        patience_max = int(round(self.t["quan"]["patience_s"] * 60))

        for _ in range(first - 1):
            self.assertEqual(s.step(idle_inp()), [])
        self.assertEqual(s.sim.customers, [])

        evs = s.step(idle_inp())
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["tick"], first)
        self.assertEqual(evs[0]["name"], "customer_arrived")
        self.assertEqual(evs[0]["data"], {"order_id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"})

        c = s.snapshot()["customers"][0]
        self.assertEqual(c["id"], "C1")
        self.assertEqual(c["order_tick"], first)
        self.assertEqual(c["state"], "waiting")
        self.assertEqual(c["order_status"], "reserved")
        self.assertEqual(c["patience_ticks_left"], patience_max)
        self.assertEqual(c["eat_ticks_left"], 0)
        self.assertEqual(c["reserved"], {"ca_loc": 1})
        self.assertIsNone(c["base_price"])
        self.assertIsNone(c["tip"])
        # Tồn vật lý trong snapshot vẫn giữ nguyên (bao gồm phần giữ chỗ), kho khả dụng giảm đi 1
        self.assertEqual(s.snapshot()["stock"], {"ca_loc": 2})
        self.assertEqual(s.sim.available_stock(), {"ca_loc": 1})
        # Snapshot player phải có cả pos và vel (PRD mục D & E)
        self.assertIn("vel", s.snapshot()["player"])

        # Bước kế tiếp kiên nhẫn mới bắt đầu giảm
        s.step(idle_inp())
        self.assertEqual(s.sim.customers[0]["patience_ticks_left"], patience_max - 1)

    def test_n3_01_random_customers_false_disables_spawn(self):
        s = Session("quan", self.t, {"stock": {"ca_loc": 5}, "random_customers": False}, 1)
        first = self.t["quan"]["first_customer_tick"]
        for _ in range(first + 10):
            evs = s.step(idle_inp())
            self.assertEqual(evs, [])
        self.assertEqual(s.sim.customers, [])

    def test_n3_01_schedule_uses_phase_tick_even_when_shortened_and_no_spawn_at_closing(self):
        """`time_left_ticks` rút ngắn về đúng `first_customer_tick` -> đóng ca ở tick đó, KHÔNG sinh khách."""
        first = self.t["quan"]["first_customer_tick"]
        s = Session("quan", self.t, {"stock": {"ca_loc": 2}, "time_left_ticks": first}, 1)
        all_evs = []
        for _ in range(first):
            all_evs.extend(s.step(idle_inp()))
        names = [e["name"] for e in all_evs]
        self.assertEqual(names, ["quan_end"])
        self.assertTrue(s.done)

        # Còn dư 1 tick sau first_customer_tick -> sinh khách tại first, rồi đóng ca ở first + 1 (closing)
        s2 = Session("quan", self.t, {"stock": {"ca_loc": 2}, "time_left_ticks": first + 1}, 1)
        evs_all = []
        for _ in range(first + 1):
            evs_all.extend(s2.step(idle_inp()))
        self.assertEqual([e["name"] for e in evs_all], ["customer_arrived", "customer_left", "quan_end"])
        self.assertEqual(evs_all[1]["data"]["reason"], "closing")
        self.assertEqual(evs_all[1]["data"]["reputation"], self.t["quan"]["reputation_initial"])

    def test_n3_01_full_tables_skip_without_no_dish(self):
        """Không còn bàn trống thì bỏ lượt, không phát `no_dish` dù kho trống."""
        first = self.t["quan"]["first_customer_tick"]
        sc = {
            "stock": {},
            "customers": [
                {"id": f"C{i + 1}", "table_id": tb["id"], "dish_id": "ca_loc_nuong_trui", "order_status": "unfulfillable"}
                for i, tb in enumerate(self.t["quan"]["tables"])
            ],
        }
        s = Session("quan", self.t, sc, 1)
        for _ in range(first):
            evs = s.step(idle_inp())
            self.assertNotIn("no_dish", [e["name"] for e in evs])
            self.assertNotIn("customer_arrived", [e["name"] for e in evs])

    def test_n3_01_smallest_free_table_and_no_double_reservation(self):
        """Nhiều bàn: chọn bàn trống id nhỏ nhất (T2 trước T10) và không giữ trùng cùng 1 nguyên liệu."""
        t2 = copy.deepcopy(self.t)
        t2["quan"]["tables"] = [
            {"id": "T10", "pos": [10, 2]},
            {"id": "T2", "pos": [6, 2]},
            {"id": "T1", "pos": [2, 2]},
        ]
        # Chỉ có 1 cá lóc -> khách đầu giữ hết, khách thứ hai gặp no_dish vì không giữ trùng
        first = t2["quan"]["first_customer_tick"]
        interval = int(round(t2["quan"]["customer_interval_s"] * 60))
        sc = {
            "stock": {"ca_loc": 1},
            "customers": [{"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "unfulfillable"}],
        }
        s = Session("quan", t2, sc, 3)
        for _ in range(first - 1):
            s.step(idle_inp())
        ev1 = s.step(idle_inp())
        # T1 đang có C2, nên chọn T2 (nhỏ hơn T10); id mới là C3 nối tiếp C2
        self.assertEqual(ev1[0]["name"], "customer_arrived")
        self.assertEqual(ev1[0]["data"], {"order_id": "C3", "table_id": "T2", "dish_id": "ca_loc_nuong_trui"})
        self.assertEqual(s.sim.available_stock(), {})

        # Đến lượt kế tiếp: T10 còn trống nhưng kho khả dụng rỗng -> no_dish
        for _ in range(interval - 1):
            s.step(idle_inp())
        ev2 = s.step(idle_inp())
        self.assertEqual([e["name"] for e in ev2], ["no_dish"])
        self.assertEqual(ev2[0]["data"], {})

    def test_n3_02_no_dish_when_stock_empty_and_deterministic_choice(self):
        """Kho rỗng phát `no_dish`; cùng seed chọn món và xuất JSONL giống nhau từng byte."""
        with Workdir() as w:
            sc_empty = write_json(w.path("empty.json"), {"quan": {"stock": {}}})
            out_empty = w.path("empty.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "120",
                                     "--scenario", sc_empty, "--out", out_empty)
            self.assertEqual(code, 0, err)
            no_dish_evs = events(read_jsonl(out_empty), "no_dish")
            self.assertEqual(len(no_dish_evs), 1)
            self.assertEqual(no_dish_evs[0]["tick"], 120)
            self.assertEqual(no_dish_evs[0]["data"], {})

            # Đủ cả 3 món -> cùng seed cho 2 lần chạy giống từng byte
            sc_all = write_json(w.path("all.json"), {
                "quan": {"stock": {"ca_loc": 2, "bong_sung": 4, "ca_linh": 6, "bong_dien_dien": 2}}
            })
            for i in (1, 2):
                code, err = run_headless("--mode", "quan", "--seed", "99", "--ticks", "200",
                                         "--scenario", sc_all, "--out", w.path(f"det{i}.jsonl"))
                self.assertEqual(code, 0, err)
            with open(w.path("det1.jsonl"), "rb") as a, open(w.path("det2.jsonl"), "rb") as b:
                self.assertEqual(a.read(), b.read())

    def test_n3_02_helper_oldest_order_and_consume_for_cooking(self):
        """Kiểm tra interface Người 3 -> Người 4: chọn đơn cũ nhất theo (order_tick, table_id) và tiêu nguyên liệu."""
        t2 = copy.deepcopy(self.t)
        t2["quan"]["tables"] = [{"id": "T1", "pos": [2, 2]}, {"id": "T2", "pos": [6, 2]}]
        sc = {
            "stock": {"ca_linh": 3, "bong_dien_dien": 1, "ca_loc": 1},
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 10},
                {"id": "C2", "table_id": "T1", "dish_id": "lau_ca_linh_dien_dien", "order_tick": 10},
            ],
        }
        s = Session("quan", t2, sc, 1)
        picked = oldest_reserved_order(s.sim.customers)
        self.assertEqual(picked["id"], "C2")  # cùng order_tick=10 -> hòa theo id bàn (T1 < T2)

        items, price = consume_order_for_cooking(s.sim.stock, picked, s.sim.menu)
        self.assertEqual(items, ["bong_dien_dien", "ca_linh", "ca_linh", "ca_linh"])
        self.assertEqual(price, self.t["menu"]["lau_ca_linh_dien_dien"]["price"])
        self.assertEqual(picked["order_status"], "assigned")
        self.assertEqual(picked["reserved"], {})
        self.assertEqual(picked["base_price"], price)
        self.assertEqual(s.sim.stock, {"ca_loc": 1})


class QuanPatienceAndDeparture(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_n3_03_patience_leave_releases_reservation_and_reduces_reputation(self):
        """Hết kiên nhẫn: rời bàn (`patience`), giảm uy tín theo tuning, nhả giữ chỗ để khách sau gọi được."""
        sc = {
            "stock": {"ca_loc": 1},
            "random_customers": False,
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "patience_ticks_left": 2,
            }],
        }
        s = Session("quan", self.t, sc, 1)
        self.assertEqual(s.sim.available_stock(), {})

        self.assertEqual(s.step(idle_inp()), [])
        self.assertEqual(s.sim.customers[0]["patience_ticks_left"], 1)

        evs = s.step(idle_inp())
        expected_rep = self.t["quan"]["reputation_initial"] + self.t["quan"]["left_reputation_delta"]
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["name"], "customer_left")
        self.assertEqual(evs[0]["data"], {
            "order_id": "C1", "table_id": "T1", "reason": "patience", "reputation": expected_rep,
        })
        self.assertEqual(s.sim.customers, [])
        self.assertEqual(s.sim.available_stock(), {"ca_loc": 1})

    def test_n3_03_assigned_customer_leaving_clears_stove_or_hand_without_refund(self):
        """Khách assigned rời bàn -> bỏ món trên bếp/tay, KHÔNG hoàn nguyên liệu đã tiêu."""
        # Case 1: món đang nấu trên bếp
        sc_stove = {
            "stock": {},
            "random_customers": False,
            "stoves": [{
                "id": "B1", "state": "cooking", "cook_ticks_left": 100,
                "dish": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            }],
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "order_status": "assigned", "patience_ticks_left": 1,
            }],
        }
        s1 = Session("quan", self.t, sc_stove, 1)
        evs1 = s1.step(idle_inp())
        self.assertEqual([e["name"] for e in evs1], ["customer_left"])
        self.assertEqual(s1.sim.stoves[0]["state"], "idle")
        self.assertIsNone(s1.sim.stoves[0]["dish"])
        self.assertEqual(s1.sim.stoves[0]["cook_ticks_left"], 0)
        self.assertEqual(s1.sim.stock, {})

        # Case 2: món đang trên tay
        sc_hand = {
            "stock": {},
            "random_customers": False,
            "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "order_status": "assigned", "patience_ticks_left": 1,
            }],
        }
        s2 = Session("quan", self.t, sc_hand, 1)
        evs2 = s2.step(idle_inp())
        self.assertEqual([e["name"] for e in evs2], ["customer_left"])
        self.assertIsNone(s2.sim.hand)
        self.assertEqual(s2.sim.stock, {})

    def test_n3_03_closing_overrides_patience_zero_without_reputation_penalty(self):
        """Tick đóng ca trùng tick kiên nhẫn về 0: khách chờ rời với `closing` và KHÔNG bị trừ uy tín."""
        sc = {
            "stock": {"ca_loc": 1},
            "time_left_ticks": 1,
            "random_customers": False,
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "patience_ticks_left": 1,
            }],
        }
        s = Session("quan", self.t, sc, 1)
        evs = s.step(idle_inp())
        self.assertEqual([e["name"] for e in evs], ["customer_left", "quan_end"])
        self.assertEqual(evs[0]["data"]["reason"], "closing")
        self.assertEqual(evs[0]["data"]["reputation"], self.t["quan"]["reputation_initial"])
        self.assertEqual(s.sim.reputation, self.t["quan"]["reputation_initial"])


class QuanFixtureValidation(unittest.TestCase):
    def _expect_exit_2(self, w, name, scenario_quan, extra_args=()):
        sc = write_json(w.path(f"{name}.json"), {"quan": scenario_quan})
        out = w.path(f"{name}.jsonl")
        code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                               "--scenario", sc, "--out", out, *extra_args)
        self.assertEqual(code, 2, f"phải trả mã 2 cho case {name}: {scenario_quan}")
        self.assertFalse(os.path.exists(out), f"không được ghi output khi lỗi ở case {name}")

    def test_n3_04_valid_fixtures_for_all_order_statuses(self):
        """Fixture hợp lệ cho cả 4 trạng thái đơn + auto-reserve hoạt động đúng ở tick 0."""
        with Workdir() as w:
            valid_cases = [
                # reserved tự động cấp giữ chỗ
                {"stock": {"ca_loc": 1}, "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
                # assigned với món trên bếp ready
                {
                    "stoves": [{"id": "B1", "state": "ready", "ready_ticks": 5,
                                "dish": {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40}}],
                    "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_status": "assigned"}],
                },
                # unfulfillable chờ không giữ chỗ
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung", "order_status": "unfulfillable"}]},
                # eating (served) đầy đủ base_price, tip, eat_ticks_left > 0
                {"customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "state": "eating", "order_status": "served", "eat_ticks_left": 120,
                    "base_price": 60, "tip": 12,
                }]},
            ]
            for i, block in enumerate(valid_cases):
                sc = write_json(w.path(f"ok_{i}.json"), {"quan": block})
                out = w.path(f"ok_{i}.jsonl")
                code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                         "--scenario", sc, "--out", out)
                self.assertEqual(code, 0, f"case {i} lỗi: {err}")
                snap = snapshots(read_jsonl(out))[0]
                self.assertEqual(len(snap["customers"]), 1)

    def test_n3_04_contradictory_fixtures_exit_2_before_output(self):
        """Mọi mâu thuẫn mức luật theo PRD-0 mục D đều trả mã 2 trước khi ghi JSONL."""
        dish_c1 = {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60}
        dish_wrong = {"order_id": "C1", "dish_id": "goi_bong_sung", "base_price": 40}
        bad_cases = {
            "unknown_stove_id": {"stoves": [{"id": "B9"}]},
            "unknown_table_id": {"tables": [{"id": "T9"}]},
            "stove_pos_oob": {"stoves": [{"id": "B1", "pos": [99, 1]}]},
            "table_pos_oob": {"tables": [{"id": "T1", "pos": [1, -1]}]},
            "rep_too_high": {"reputation": 6.0},
            "rep_bool": {"reputation": True},
            "random_customers_str": {"random_customers": "false"},
            "missing_dish_id": {"customers": [{"id": "C1", "table_id": "T1"}]},
            "unknown_dish_id": {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "bun_bo"}]},
            "reserved_exceeds_stock": {
                "stock": {"ca_loc": 0},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
            },
            "reserved_wrong_recipe": {
                "stock": {"ca_loc": 2},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": {"ca_loc": 2}}],
            },
            "reserved_explicit_empty": {
                "stock": {"ca_loc": 1},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": {}}],
            },
            "reserved_explicit_null": {
                "stock": {"ca_loc": 1},
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "reserved": None}],
            },
            "assigned_without_dish": {
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            "assigned_with_reserved": {
                "stock": {"ca_loc": 1},
                "hand": dish_c1,
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "order_status": "assigned", "reserved": {"ca_loc": 1},
                }],
            },
            "dish_on_both_stove_and_hand": {
                "stoves": [{"id": "B1", "state": "ready", "dish": dish_c1}],
                "hand": dish_c1,
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            "dish_mismatch_order_dish": {
                "hand": dish_wrong,
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            "orphan_hand_reference": {"hand": dish_c1},
            "cooking_zero_timer": {
                "stoves": [{"id": "B1", "state": "cooking", "cook_ticks_left": 0, "dish": dish_c1}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            "idle_stove_with_dish": {
                "stoves": [{"id": "B1", "state": "idle", "dish": dish_c1}],
                "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"}],
            },
            "eating_not_served": {
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "state": "eating", "order_status": "reserved", "eat_ticks_left": 10,
                    "base_price": 60, "tip": 0,
                }],
            },
            "eating_zero_timer": {
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "state": "eating", "order_status": "served", "eat_ticks_left": 0,
                    "base_price": 60, "tip": 0,
                }],
            },
            "eating_missing_price_or_tip": {
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "state": "eating", "order_status": "served", "eat_ticks_left": 10,
                }],
            },
            "waiting_with_eat_timer": {
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "order_status": "unfulfillable", "eat_ticks_left": 5,
                }],
            },
            "unfulfillable_with_reserved": {
                "stock": {"ca_loc": 1},
                "customers": [{
                    "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                    "order_status": "unfulfillable", "reserved": {"ca_loc": 1},
                }],
            },
        }
        with Workdir() as w:
            for name, block in bad_cases.items():
                self._expect_exit_2(w, name, block)

            # Kiểm tra giữ chỗ vượt tồn kho đến từ --inventory (không có quan.stock trong scenario)
            inv = write_json(w.path("empty_inv.json"), {"items": {}})
            self._expect_exit_2(
                w,
                "reserved_exceeds_inventory_flag",
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}]},
                extra_args=("--inventory", inv),
            )


if __name__ == "__main__":
    unittest.main()
