"""Bộ test đầy đủ cho Quán (2 bếp B1–B2, 4 bàn T1–T4, 6 món, day_plan và trọn vòng bếp→phục vụ→tiền→đóng ca).

Đã cập nhật lên Test Contract v1.2:
  - Kho & giữ chỗ dùng mảng cá thể `{id, kind, fresh}` / mảng id.
  - Giá món chốt theo độ tươi `floor(giá_niêm_yết * trung_bình_fresh / 100)` sau bước hao tươi.
"""

import copy
import time
import unittest

from chonoi.contract import compute_plan_ingredients, load_contract
from chonoi.errors import BadInput
from chonoi.ids import IdAllocator
from chonoi.inputs import InputState
from chonoi.rng import Streams
from chonoi.runner import Session
from chonoi.sim.quan import QuanSim
from chonoi.sim.quan_orders import validate_quan_scenario_block

from helpers import Workdir, events, frames, read_jsonl, run_headless, write_json


def inp(*edges, move=(0.0, 0.0)):
    return InputState(move, {}, set(edges))


def mk_items(counts: dict, fresh=100, start_idx=1) -> list:
    out = []
    idx = start_idx
    for kind in sorted(counts):
        for _ in range(counts[kind]):
            out.append({"id": f"I{idx}", "kind": kind, "fresh": fresh})
            idx += 1
    return out


class QuanV11ManifestAndMenu(unittest.TestCase):
    def setUp(self):
        self.contract = load_contract()
        self.t = self.contract["tuning"]

    def test_v11_contract_numbers_and_day_plan_totals(self):
        self.assertEqual(self.contract["contract_version"], "1.3")
        self.assertIn("bench_cmd", self.contract)
        self.assertIn("soak_cmd", self.contract)
        self.assertEqual(self.t["freshness"], {
            "initial": 100,
            "gather_decay_per_s": 0.5,
            "quan_decay_per_s": 0.25,
            "spoiled_below": 30,
        })
        self.assertEqual([s["id"] for s in self.t["quan"]["stoves"]], ["B1", "B2"])
        self.assertEqual([tb["id"] for tb in self.t["quan"]["tables"]], ["T1", "T2", "T3", "T4"])
        self.assertEqual(
            set(self.t["menu"]),
            {"ca_loc_nuong_trui", "goi_bong_sung", "lau_ca_linh_dien_dien",
             "canh_chua_ca_loc", "ca_keo_nuong", "lau_mam"},
        )
        self.assertEqual(len(self.t["day_plan"]), 5)
        for entry in self.t["day_plan"]:
            self.assertEqual(entry["ingredients"], compute_plan_ingredients(entry["dishes"], self.t["menu"]))

    def test_v11_two_process_inventory_with_new_kinds_and_lau_mam(self):
        """Liên thông 2 tiến trình v1.2 với nguyên liệu mới (`ca_keo`, `keo_neo`) và nấu `lau_mam` chốt giá theo tươi."""
        with Workdir() as w:
            sc_g = write_json(w.path("g.json"), {
                "gather": {
                    "hold": [
                        {"id": "I1", "kind": "ca_linh", "fresh": 100},
                        {"id": "I2", "kind": "ca_linh", "fresh": 100},
                        {"id": "I3", "kind": "ca_keo", "fresh": 100},
                        {"id": "I4", "kind": "keo_neo", "fresh": 100},
                        {"id": "I5", "kind": "bong_dien_dien", "fresh": 100},
                    ],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            in_g = write_json(w.path("ig.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "7", "--scenario", sc_g,
                                     "--inputs", in_g, "--ticks", "1", "--inventory-out", inv,
                                     "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)

            # Quán nhận kho đủ nấu đúng duy nhất 1 món `lau_mam` (không đủ các món khác)
            sc_q = write_json(w.path("q.json"), {"quan": {"player": {"pos": [2, 8]}}})
            in_q = write_json(w.path("iq.json"), frames({"tick": 120, "interact": True}, {"tick": 121, "interact": False}))
            q_out = w.path("q.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "7", "--inventory", inv,
                                     "--scenario", sc_q, "--inputs", in_q, "--ticks", "122",
                                     "--out", q_out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(q_out)
            arr = events(rows, "customer_arrived")
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["data"]["dish_id"], "lau_mam")
            cook = events(rows, "cook_started")
            self.assertEqual(len(cook), 1)
            # Sau 1 bước gather (99.992) + 121 bước quán (121/240 ≈ 0.504) -> fresh = 99.488
            # Giá niêm yết 200 * 99.487833 / 100 = 198.975 -> floor = 198; sắp theo (kind, id)
            self.assertEqual(cook[0]["data"], {
                "stove_id": "B1",
                "order_id": "C1",
                "dish_id": "lau_mam",
                "items": [
                    {"id": "I5", "kind": "bong_dien_dien", "fresh": 99.488},
                    {"id": "I3", "kind": "ca_keo", "fresh": 99.488},
                    {"id": "I1", "kind": "ca_linh", "fresh": 99.488},
                    {"id": "I2", "kind": "ca_linh", "fresh": 99.488},
                    {"id": "I4", "kind": "keo_neo", "fresh": 99.488},
                ],
                "base_price": 198,
            })


class QuanV11KitchenServePayLoop(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_full_loop_cook_ready_pick_serve_tip_and_pay(self):
        """Trọn vòng nấu (chốt giá theo fresh sau 1 tick hao) → chín → nhấc → phục vụ (boa) → ăn xong trả tiền."""
        sc = {
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
            "random_customers": False,
            "player": {"pos": [2, 8]},  # đúng vị trí bếp B1
            "customers": [{"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui"}],
        }
        s = Session("quan", self.t, sc, 1)

        # Tick 1: hao 1/240 (fresh=99.995833 -> 99.996), interact tại bếp B1 -> base_price = floor(60*23999/24000) = 59
        ev = s.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev], ["cook_started"])
        self.assertEqual(ev[0]["data"], {
            "stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui",
            "items": [{"id": "I1", "kind": "ca_loc", "fresh": 99.996}], "base_price": 59,
        })
        self.assertEqual(s.sim.stock, [])
        self.assertEqual(s.sim.customers[0]["order_status"], "assigned")
        self.assertEqual(s.sim.stoves[0]["cook_ticks_left"], 360)

        # Nấu 359 tick -> vẫn cooking (còn 1 tick)
        for _ in range(359):
            self.assertEqual(s.step(inp()), [])
        self.assertEqual(s.sim.stoves[0]["state"], "cooking")

        # Tick chín: dish_ready, ready_ticks == 0 (KHÔNG tăng ngay bước vừa chín!)
        ev_ready = s.step(inp())
        self.assertEqual([e["name"] for e in ev_ready], ["dish_ready"])
        self.assertEqual(ev_ready[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui"})
        self.assertEqual(s.sim.stoves[0]["state"], "ready")
        self.assertEqual(s.sim.stoves[0]["ready_ticks"], 0)

        # Thêm 1 bước không làm gì -> ready_ticks tăng lên 1
        self.assertEqual(s.step(inp()), [])
        self.assertEqual(s.sim.stoves[0]["ready_ticks"], 1)

        # Nhấc món khỏi bếp B1 -> dish_picked, bếp về idle
        ev_pick = s.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev_pick], ["dish_picked"])
        self.assertEqual(ev_pick[0]["data"], {"stove_id": "B1", "order_id": "C1", "dish_id": "ca_loc_nuong_trui"})
        self.assertEqual(s.sim.hand, {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 59})
        self.assertEqual(s.sim.stoves[0]["state"], "idle")

        # Đi tới bàn T1 và phục vụ (kiên nhẫn còn > 50% -> boa = floor(59 * 0.2) = 11)
        s.sim.pos = list(self.t["quan"]["tables"][0]["pos"])
        ev_serve = s.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev_serve], ["served"])
        self.assertEqual(ev_serve[0]["data"]["tip"], 11)
        self.assertEqual(ev_serve[0]["data"]["base_price"], 59)
        self.assertIsNone(s.sim.hand)
        self.assertEqual(s.sim.customers[0]["state"], "eating")
        self.assertEqual(s.sim.customers[0]["order_status"], "served")
        self.assertEqual(s.sim.customers[0]["eat_ticks_left"], 600)

        # Ăn 599 tick -> chưa trả tiền; tick 600 -> paid (59 + 11 = 70) + +0.2 uy tín
        for _ in range(599):
            self.assertEqual(s.step(inp()), [])
        ev_paid = s.step(inp())
        self.assertEqual([e["name"] for e in ev_paid], ["paid"])
        self.assertEqual(ev_paid[0]["data"], {
            "order_id": "C1", "table_id": "T1", "base_price": 59, "tip": 11,
            "amount": 70, "reason": "finished_eating",
        })
        self.assertEqual(s.sim.money, 70)
        self.assertEqual(s.sim.earned, 70)
        self.assertEqual(s.sim.shift_earned, 70)
        self.assertEqual(s.sim.reputation, 3.2)
        self.assertEqual(s.snapshot()["score"], 370)
        self.assertEqual(s.sim.customers, [])

    def test_tip_threshold_exact_boundary_and_no_tip_under_half(self):
        """Đúng 50% kiên nhẫn sau bước 1 (1800/3600) vẫn được boa; 1799/3600 thì boa 0 và không cộng uy tín."""
        sc_ok = {
            "random_customers": False,
            "player": {"pos": [9, 2]},
            "hand": {"order_id": "C1", "dish_id": "ca_keo_nuong", "base_price": 70},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_keo_nuong",
                "order_status": "assigned", "patience_ticks_left": 1801,
            }],
        }
        s1 = Session("quan", self.t, sc_ok, 1)
        ev1 = s1.step(inp("interact"))
        self.assertEqual(ev1[0]["data"]["patience_ticks_left"], 1800)
        self.assertEqual(ev1[0]["data"]["tip"], 14)

        sc_no = copy.deepcopy(sc_ok)
        sc_no["customers"][0]["patience_ticks_left"] = 1800
        s2 = Session("quan", self.t, sc_no, 1)
        ev2 = s2.step(inp("interact"))
        self.assertEqual(ev2[0]["data"]["patience_ticks_left"], 1799)
        self.assertEqual(ev2[0]["data"]["tip"], 0)
        for _ in range(600):
            s2.step(inp())
        self.assertEqual(s2.sim.money, 70)
        self.assertEqual(s2.sim.reputation, 3.0)

    def test_serve_at_exact_patience_zero_and_at_closing_tick(self):
        """Phục vụ đúng tick kiên nhẫn về 0 hoặc đúng tick đóng ca vẫn hợp lệ và thu tiền ngay khi đóng ca."""
        sc_pat0 = {
            "random_customers": False,
            "player": {"pos": [9, 2]},
            "hand": {"order_id": "C1", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "order_status": "assigned", "patience_ticks_left": 1,
            }],
        }
        s1 = Session("quan", self.t, sc_pat0, 1)
        ev1 = s1.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev1], ["served"])
        self.assertEqual(ev1[0]["data"]["patience_ticks_left"], 0)
        self.assertEqual(ev1[0]["data"]["tip"], 0)
        self.assertEqual(s1.sim.customers[0]["state"], "eating")

        sc_close = copy.deepcopy(sc_pat0)
        sc_close["time_left_ticks"] = 1
        sc_close["customers"][0]["patience_ticks_left"] = 2000
        s2 = Session("quan", self.t, sc_close, 1)
        ev2 = s2.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev2], ["served", "paid", "quan_end"])
        self.assertEqual(ev2[1]["data"]["reason"], "closing")
        self.assertEqual(ev2[1]["data"]["amount"], 72)
        self.assertEqual(ev2[2]["data"]["money"], 72)
        self.assertEqual(ev2[2]["data"]["reputation"], 3.2)

    def test_two_stoves_four_tables_tie_breaking_and_drop_turn(self):
        """Kiểm tra 2 bếp B1/B2, ưu tiên (khoảng cách, bếp trước bàn, id) và bỏ lượt khi mục tiêu chọn không tương tác được."""
        sc = {
            "stock": mk_items({"ca_loc": 2}),
            "random_customers": False,
            "player": {"pos": [3.5, 8.0]},  # cách B1 [2,8] đúng 1.5m và B2 [5,8] đúng 1.5m
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 20},
                {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 10},
            ],
        }
        s = Session("quan", self.t, sc, 1)
        ev1 = s.step(inp("interact"))
        self.assertEqual(ev1[0]["data"]["stove_id"], "B1")
        self.assertEqual(ev1[0]["data"]["order_id"], "C2")  # order_tick=10 cũ hơn 20

        ev2 = s.step(inp("interact"))
        self.assertEqual(ev2, [])
        self.assertEqual(s.sim.stoves[1]["state"], "idle")

        s.sim.pos = [4.5, 8.0]
        ev3 = s.step(inp("interact"))
        self.assertEqual(ev3[0]["data"]["stove_id"], "B2")
        self.assertEqual(ev3[0]["data"]["order_id"], "C1")

    def test_stove_priority_over_table_at_equal_distance_and_wrong_order_rejected(self):
        """Cùng khoảng cách: bếp ưu tiên hơn bàn; đưa sai món cho bàn thì không phục vụ."""
        t_custom = copy.deepcopy(self.t)
        t_custom["quan"]["stoves"] = [{"id": "B1", "pos": [4.0, 5.0]}]
        t_custom["quan"]["tables"] = [{"id": "T1", "pos": [6.0, 5.0]}, {"id": "T2", "pos": [8.0, 5.0]}]
        sc = {
            "stock": mk_items({"ca_loc": 1}),
            "random_customers": False,
            "player": {"pos": [5.0, 5.0]},
            "hand": {"order_id": "C2", "dish_id": "ca_loc_nuong_trui", "base_price": 60},
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_status": "reserved"},
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_status": "assigned"},
            ],
        }
        s = Session("quan", t_custom, sc, 1)
        ev = s.step(inp("interact"))
        self.assertEqual([e["name"] for e in ev], ["cook_started"])
        self.assertEqual(ev[0]["data"]["stove_id"], "B1")
        s.sim.pos = [6.0, 5.0]
        self.assertEqual(s.step(inp("interact")), [])
        self.assertIsNotNone(s.sim.hand)

    def test_closing_with_four_tables_mixed_states(self):
        """Đóng ca với đủ 4 bàn T1–T4: ăn xong trả finished_eating, đang ăn trả closing, chờ rời closing không trừ uy tín & dọn bếp."""
        sc = {
            "stock": mk_items({"ca_loc": 1}),
            "time_left_ticks": 1,
            "random_customers": False,
            "stoves": [{
                "id": "B1", "state": "cooking", "cook_ticks_left": 50,
                "dish": {"order_id": "C4", "dish_id": "goi_bong_sung", "base_price": 40},
            }],
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "state": "eating",
                 "order_status": "served", "eat_ticks_left": 1, "base_price": 60, "tip": 12},
                {"id": "C2", "table_id": "T2", "dish_id": "canh_chua_ca_loc", "state": "eating",
                 "order_status": "served", "eat_ticks_left": 200, "base_price": 90, "tip": 0},
                {"id": "C3", "table_id": "T3", "dish_id": "ca_loc_nuong_trui", "order_status": "reserved",
                 "patience_ticks_left": 1},
                {"id": "C4", "table_id": "T4", "dish_id": "goi_bong_sung", "order_status": "assigned",
                 "patience_ticks_left": 100},
            ],
        }
        s = Session("quan", self.t, sc, 1)
        evs = s.step(inp())
        self.assertEqual([e["name"] for e in evs], ["paid", "paid", "customer_left", "customer_left", "quan_end"])
        self.assertEqual(evs[0]["data"]["order_id"], "C1")
        self.assertEqual(evs[0]["data"]["reason"], "finished_eating")
        self.assertEqual(evs[1]["data"]["order_id"], "C2")
        self.assertEqual(evs[1]["data"]["reason"], "closing")
        self.assertEqual(evs[2]["data"], {"order_id": "C3", "table_id": "T3", "reason": "closing", "reputation": 3.2})
        self.assertEqual(evs[3]["data"], {"order_id": "C4", "table_id": "T4", "reason": "closing", "reputation": 3.2})
        self.assertEqual(evs[4]["data"], {
            "reason": "time", "money": 162, "earned": 162, "shift_earned": 162, "reputation": 3.2,
        })
        self.assertEqual(s.sim.stoves[0]["state"], "idle")
        self.assertIsNone(s.sim.stoves[0]["dish"])
        self.assertEqual(s.sim.customers, [])


class QuanV11DayPlanAndPerformance(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_day_plan_filters_menu_and_allows_exceeding_quota(self):
        """Trong chế độ `day`, khách chỉ gọi món thuộc `day_plan.dishes`, được gọi vượt số suất nếu còn nguyên liệu."""
        d1_dishes = set(self.t["day_plan"][0]["dishes"])  # {"ca_loc_nuong_trui", "goi_bong_sung"}
        stock = mk_items({"ca_loc": 5, "bong_dien_dien": 5, "ca_linh": 9})
        sim = QuanSim(self.t, {}, Streams(11), IdAllocator(), inventory=stock, allowed_dishes=d1_dishes)
        first = self.t["quan"]["first_customer_tick"]
        interval = int(round(self.t["quan"]["customer_interval_s"] * 60))
        arrived = []
        for _ in range(first + 3 * interval):
            for name, data in sim.step(inp()):
                if name == "customer_arrived":
                    arrived.append(data["dish_id"])
        self.assertEqual(arrived, ["ca_loc_nuong_trui"] * 4)

    def test_day_mode_scenario_validation_restrictions(self):
        """Trong `day`: cấm `quan.stock`, cấm `quan.reputation`, và từ chối khách gọi món ngoài kế hoạch ngày."""
        with self.assertRaises(BadInput):
            validate_quan_scenario_block({"stock": mk_items({"ca_loc": 1})}, self.t, in_day_mode=True)
        with self.assertRaises(BadInput):
            validate_quan_scenario_block({"reputation": 3.0}, self.t, in_day_mode=True)
        d1_dishes = set(self.t["day_plan"][0]["dishes"])
        with self.assertRaises(BadInput):
            QuanSim(
                self.t,
                {"customers": [{"id": "C1", "table_id": "T1", "dish_id": "lau_mam", "order_status": "unfulfillable"}]},
                Streams(1), IdAllocator(), inventory=[], allowed_dishes=d1_dishes,
            )

    def test_full_shift_10800_ticks_performance(self):
        """Một ca quán đầy đủ 10.800 tick chạy nhanh (<< ngân sách 20s cho cả ngày 22.200 tick)."""
        s = Session("quan", self.t, {"stock": mk_items({"ca_loc": 10, "bong_sung": 10, "ca_keo": 10})}, 5)
        t0 = time.perf_counter()
        while not s.done:
            s.step(inp())
        elapsed = time.perf_counter() - t0
        self.assertEqual(s.tick, 10800)
        self.assertLess(elapsed, 8.0, f"10800 ticks quá chậm: {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
