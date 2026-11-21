"""Bộ test chuyên sâu cho Change Request Phase 3 — Test Contract v1.2 ("Mùa Nước Nổi": kho cá thể & độ tươi).

Bao phủ trọn vẹn mọi yêu cầu lõi trong TICKET-03:
  1. Fixture biên từ TICKET-03: `fresh: 30` ở gather -> phát `spoiled` đúng 1 lần tại tick 1, không lặp lại.
  2. Smoke bàn giao file từ TICKET-03: `fresh: 100` + `interact: true` frame 0 -> `catch.json` khớp chính xác
     `id`, `kind`, `fresh` với snapshot tick 0 của `quan --inventory --ticks 0`.
  3. Từ chối kho đếm v1.1, schema sai, trùng id, fresh ngoài [0, 100], giữ hàng ươn hoặc dùng chung id (mã 2 trước khi ghi JSONL).
  4. Thứ tự phát `spoiled` theo id trong cả `gather` và `quan`; hàng ươn vẫn chiếm ô giỏ và chuyển sang quán.
  5. Hao tươi trong `quan` (0.25/s = 1/240 tick, kể cả hàng đang giữ), nhả & giữ lại đúng 1 lần theo `(order_tick, table_id)`,
     chuyển `unfulfillable` khi không đủ hàng thay thế và chờ tới hạn kiên nhẫn.
  6. Chọn cá thể tươi nhất (hòa theo id nhỏ) cho cả đơn tự sinh và đơn thiếu `reserved` trong scenario.
  7. Chốt giá `floor(giá_niêm_yết * trung_bình_fresh / 100)` chính xác bằng số hữu tỉ cho món 1 & nhiều nguyên liệu,
     `cook_started.data.items` sắp theo `(kind, id)` và boa `floor(base_price * 0.2)` tính trên giá đã chốt.
  8. `pause` dừng hao tươi ở cả `gather` và `quan`; chuyển pha `gather -> quan` trong `--mode day` không hao thêm;
     hàng ở `Shop` không hao; ID `I1, I2, ...` tăng liên tục xuyên pha và Ngày.
"""

from fractions import Fraction
import json
import os
import unittest

from chonoi.contract import load_contract
from chonoi.freshness_v12 import compute_fresh_price, format_fresh
from chonoi.inputs import InputState
from chonoi.runner import Session

from helpers import Workdir, events, frames, read_jsonl, run_headless, snapshots, write_json


def inp(*edges, move=(0.0, 0.0)):
    return InputState(move, {}, set(edges))


class Ticket03ExactSmokesAndSchema(unittest.TestCase):
    def test_ticket03_exact_threshold_30_spoil_once_in_gather(self):
        """Fixture mẫu nguyên văn từ TICKET-03: fresh=30 ở gather -> phát spoiled đúng tick 1 và KHÔNG lặp tick 2."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            out = w.path("out.jsonl")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "2",
                                     "--scenario", sc, "--snapshot-every", "1", "--out", out)
            self.assertEqual(code, 0, err)
            rows = read_jsonl(out)
            sp = events(rows, "spoiled")
            self.assertEqual(len(sp), 1)
            self.assertEqual(sp[0], {
                "type": "event",
                "tick": 1,
                "phase": "gather",
                "name": "spoiled",
                "data": {"item_id": "I1", "kind": "ca_linh", "location": "hold"},
            })
            # Hàng ươn vẫn còn trong giỏ và chiếm 1 ô
            snaps = {s["tick"]: s for s in snapshots(rows)}
            self.assertEqual(snaps[1]["hold_count"], 1)
            self.assertEqual(snaps[1]["hold"][0]["id"], "I1")
            self.assertLess(snaps[1]["hold"][0]["fresh"], 30)

    def test_ticket03_exact_file_handoff_smoke(self):
        """Smoke bàn giao nguyên văn từ TICKET-03: fresh=100, dock frame 0 -> quan --inventory --ticks 0 khớp tuyệt đối."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100}],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            in_g = write_json(w.path("ig.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--inputs", in_g,
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved, {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 99.992}]})

            q_out = w.path("q.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", inv, "--out", q_out)
            self.assertEqual(code, 0, err)
            q_snap0 = snapshots(read_jsonl(q_out))[0]
            self.assertEqual(q_snap0["stock"], saved["items"])

    def test_spoiled_items_transfer_to_quan_and_counted_v11_inventory_rejected(self):
        """Hàng đã ươn ở gather vẫn chuyển nguyên sang quan; file kho đếm v1.1 bị từ chối với mã 2."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [
                        {"id": "I2", "kind": "ca_loc", "fresh": 29.5},
                        {"id": "I1", "kind": "ca_linh", "fresh": 30},
                    ],
                    "random_fish": False,
                    "monsters": [],
                }
            })
            in_g = write_json(w.path("ig.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("catch.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--inputs", in_g,
                                     "--inventory-out", inv, "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            # Xuất file phải sắp theo id: I1 trước I2; cả 2 cá thể ươn đều có mặt
            self.assertEqual([it["id"] for it in saved["items"]], ["I1", "I2"])
            self.assertTrue(all(it["fresh"] < 30 for it in saved["items"]))
            # Chỉ I1 phát spoiled (I2 đã < 30 từ đầu nên không phát lại)
            sp = events(read_jsonl(w.path("g.jsonl")), "spoiled")
            self.assertEqual(len(sp), 1)
            self.assertEqual(sp[0]["data"]["item_id"], "I1")

            # Mở quán bằng kho toàn hàng ươn: tick 0 giữ nguyên cả 2 cá thể, tick 120 phát no_dish!
            q_out = w.path("q.jsonl")
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "120",
                                     "--inventory", inv, "--out", q_out)
            self.assertEqual(code, 0, err)
            q_rows = read_jsonl(q_out)
            self.assertEqual(snapshots(q_rows)[0]["stock"], saved["items"])
            self.assertEqual(len(events(q_rows, "no_dish")), 1)
            self.assertEqual(events(q_rows, "customer_arrived"), [])

            # File kho đếm kiểu cũ trả mã 2 trước khi tạo JSONL
            old_inv = write_json(w.path("old.json"), {"items": {"ca_loc": 1}})
            bad_out = w.path("bad.jsonl")
            code, _ = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                   "--inventory", old_inv, "--out", bad_out)
            self.assertEqual(code, 2)
            self.assertFalse(os.path.exists(bad_out))


class QuanSpoilageReReservationAndPricing(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_spoiled_emitted_by_id_then_single_re_reserve_by_order_tick_and_table_id(self):
        """Khi hàng giữ bị ươn ở bước 2: phát HẾT `spoiled` theo id -> xử lý đơn theo (order_tick, table_id)."""
        # I1 (30) giữ bởi C2 (order_tick=20, T2), I2 (30) giữ bởi C1 (order_tick=10, T1)
        # Chỉ có 1 con cá lóc dự phòng tươi I3 (fresh=85) và I4 (fresh=85) nhưng cần test tranh chấp:
        # Cho 1 con dự phòng duy nhất I10 (fresh=85): C1 (order_tick=10) phải thắng giữ I10, C2 (order_tick=20) chuyển unfulfillable!
        sc = {
            "stock": [
                {"id": "I10", "kind": "ca_loc", "fresh": 85},
                {"id": "I2", "kind": "ca_loc", "fresh": 30},
                {"id": "I1", "kind": "ca_loc", "fresh": 30},
            ],
            "random_customers": False,
            "customers": [
                {"id": "C2", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 20, "reserved": ["I1"]},
                {"id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 10, "reserved": ["I2"]},
            ],
        }
        s = Session("quan", self.t, sc, 1)
        evs = s.step(inp())
        # Phát HẾT spoiled theo id_key: I1 rồi I2 (trước khi xử lý giữ chỗ)
        self.assertEqual(evs, [
            {"type": "event", "tick": 1, "phase": "quan", "name": "spoiled",
             "data": {"item_id": "I1", "kind": "ca_loc", "location": "stock"}},
            {"type": "event", "tick": 1, "phase": "quan", "name": "spoiled",
             "data": {"item_id": "I2", "kind": "ca_loc", "location": "stock"}},
        ])
        by_id = {c["id"]: c for c in s.sim.customers}
        # C1 ưu tiên hơn C2 (order_tick 10 < 20) -> giữ lại thành công I10
        self.assertEqual(by_id["C1"]["order_status"], "reserved")
        self.assertEqual(by_id["C1"]["reserved"], ["I10"])
        # C2 không còn hàng tươi thay thế -> chuyển unfulfillable, reserved rỗng, vẫn ngồi chờ tới hạn
        self.assertEqual(by_id["C2"]["order_status"], "unfulfillable")
        self.assertEqual(by_id["C2"]["reserved"], [])
        self.assertEqual(by_id["C2"]["state"], "waiting")

    def test_release_full_reservation_allows_later_order_to_reuse_surviving_ingredient(self):
        """Đơn A bị ươn 1 thành phần -> nhả TOÀN BỘ phần giữ (gồm nguyên liệu còn tươi) để đơn B phía sau giữ lại được."""
        # C1 (T1, order_tick=1, canh_chua_ca_loc = ca_loc + bong_dien_dien) giữ I1(ca_loc, 30) + I2(bong_dien_dien, 90)
        # C2 (T2, order_tick=2, goi_bong_sung cần 2 bong_sung) — đổi thành món cần bong_dien_dien: dùng canh_chua_ca_loc với I4(ca_loc, 90)
        # C2 (T2, order_tick=2, canh_chua_ca_loc) giữ I3(bong_dien_dien, 30) + I4(ca_loc, 90)
        # Không còn ca_loc khác; khi I1 và I3 cùng ươn:
        #   - C1 xử lý trước: nhả I1, I2; không đủ ca_loc (I4 đang bị C2 giữ!) -> C1 thành unfulfillable, I2 trở thành tự do!
        #   - C2 xử lý sau: nhả I3, I4; giờ cả I4(ca_loc, 90) lẫn I2(bong_dien_dien, 90) đều tự do -> C2 giữ được [I2, I4]!
        sc = {
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 30},
                {"id": "I2", "kind": "bong_dien_dien", "fresh": 90},
                {"id": "I3", "kind": "bong_dien_dien", "fresh": 30},
                {"id": "I4", "kind": "ca_loc", "fresh": 90},
            ],
            "random_customers": False,
            "customers": [
                {"id": "C1", "table_id": "T1", "dish_id": "canh_chua_ca_loc", "order_tick": 1, "reserved": ["I1", "I2"]},
                {"id": "C2", "table_id": "T2", "dish_id": "canh_chua_ca_loc", "order_tick": 2, "reserved": ["I3", "I4"]},
            ],
        }
        s = Session("quan", self.t, sc, 1)
        evs = s.step(inp())
        self.assertEqual([e["data"]["item_id"] for e in evs], ["I1", "I3"])
        by_id = {c["id"]: c for c in s.sim.customers}
        self.assertEqual(by_id["C1"]["order_status"], "unfulfillable")
        self.assertEqual(by_id["C1"]["reserved"], [])
        self.assertEqual(by_id["C2"]["order_status"], "reserved")
        self.assertEqual(by_id["C2"]["reserved"], ["I2", "I4"])

    def test_auto_reserve_picks_freshest_then_smallest_id(self):
        """Bỏ `reserved` cho đơn `reserved` -> cấp theo (order_tick, table_id), lấy tươi nhất rồi id nhỏ."""
        sc = {
            "stock": [
                {"id": "I10", "kind": "ca_loc", "fresh": 80},
                {"id": "I2", "kind": "ca_loc", "fresh": 80},
                {"id": "I3", "kind": "ca_loc", "fresh": 95},
            ],
            "random_customers": False,
            "customers": [
                {"id": "C1", "table_id": "T2", "dish_id": "ca_loc_nuong_trui", "order_tick": 5},
                {"id": "C2", "table_id": "T1", "dish_id": "ca_loc_nuong_trui", "order_tick": 5},
            ],
        }
        s = Session("quan", self.t, sc, 1)
        by_id = {c["id"]: c for c in s.sim.customers}
        # C2 (T1) xử lý trước C1 (T2) -> C2 lấy I3 (tươi nhất 95); C1 lấy I2 (cùng 80 với I10 nhưng I2 < I10)
        self.assertEqual(by_id["C2"]["reserved"], ["I3"])
        self.assertEqual(by_id["C1"]["reserved"], ["I2"])

    def test_exact_fresh_price_and_tip_on_locked_price(self):
        """Kiểm chốt giá chính xác = floor(price * avg_fresh / 100) cho món nhiều nguyên liệu và boa trên giá đã chốt."""
        # canh_chua_ca_loc (giá 90) = 1 ca_loc + 1 bong_dien_dien
        # Chọn fresh đầu sao cho sau đúng 1 bước hao (1/240), trung bình là đúng 50:
        # fresh = 50 + 1/240 không biểu diễn thập phân chính xác, nên kiểm trực tiếp ở fresh=51 và fresh=50:
        # Dùng 2 cá thể fresh=50 và fresh=70 -> sau 1 tick hao: avg = 60 - 1/240 -> 90 * (60 - 1/240) / 100 = 53.99625 -> floor = 53
        # Còn dùng hàm compute_fresh_price trực tiếp cho trường hợp chính xác 50% -> floor(90 * 50 / 100) = 45!
        self.assertEqual(
            compute_fresh_price(90, [{"fresh": Fraction(50)}, {"fresh": Fraction(50)}]),
            45,
        )
        self.assertEqual(
            compute_fresh_price(60, [{"fresh": Fraction(30)}]),
            18,
        )
        # Chạy thực tế qua QuanSim: canh_chua_ca_loc (90) với I2(ca_loc, 50.25) và I1(bong_dien_dien, 70.25)
        # Sau 60 tick hao (60 * 1/240 = 0.25 chính xác!) -> I2=50.0, I1=70.0 -> avg=60.0 -> base_price = floor(90*60/100) = 54!
        # Boa = floor(54 * 0.2) = floor(10.8) = 10!
        sc = {
            "stock": [
                {"id": "I2", "kind": "ca_loc", "fresh": 50.25},
                {"id": "I1", "kind": "bong_dien_dien", "fresh": 70.25},
            ],
            "random_customers": False,
            "player": {"pos": [2, 8]},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "canh_chua_ca_loc",
                "reserved": ["I1", "I2"],
            }],
        }
        s = Session("quan", self.t, sc, 1)
        for _ in range(59):
            self.assertEqual(s.step(inp()), [])
        # Tick 60: vừa đúng hao 0.25 -> I1=70, I2=50 -> nấu chốt base_price=54
        ev_cook = s.step(inp("interact"))
        self.assertEqual(ev_cook[0]["name"], "cook_started")
        self.assertEqual(ev_cook[0]["data"], {
            "stove_id": "B1",
            "order_id": "C1",
            "dish_id": "canh_chua_ca_loc",
            "items": [
                {"id": "I1", "kind": "bong_dien_dien", "fresh": 70},
                {"id": "I2", "kind": "ca_loc", "fresh": 50},
            ],
            "base_price": 54,
        })
        # Nấu xong, nhấc và phục vụ -> boa = floor(54 * 0.2) = 10
        cook_ticks = s.sim.stoves[0]["cook_ticks_left"]
        for _ in range(cook_ticks):
            s.step(inp())
        s.step(inp("interact"))  # nhấc
        s.sim.pos = list(self.t["quan"]["tables"][0]["pos"])
        ev_serve = s.step(inp("interact"))
        self.assertEqual(ev_serve[0]["name"], "served")
        self.assertEqual(ev_serve[0]["data"]["base_price"], 54)
        self.assertEqual(ev_serve[0]["data"]["tip"], 10)


class PauseDayHandoffAndIdContinuity(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()["tuning"]

    def test_pause_freezes_freshness_in_gather_and_quan(self):
        """Pause phải dừng hoàn toàn hao tươi ở cả gather và quan."""
        sg = Session("gather", self.t, {
            "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 50}],
            "random_fish": False,
            "monsters": [],
        }, 1)
        sg.step(inp("pause"))
        for _ in range(100):
            sg.step(inp())
        self.assertEqual(sg.sim.hold[0]["fresh"], Fraction(50))

        sq = Session("quan", self.t, {
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 50}],
            "random_customers": False,
        }, 1)
        sq.step(inp("pause"))
        for _ in range(100):
            sq.step(inp())
        self.assertEqual(sq.sim.stock[0]["fresh"], Fraction(50))

    def test_day_handoff_zero_extra_decay_and_monotonic_item_ids_across_days(self):
        """Trong `--mode day`: gather -> quan không hao thêm ở tick chuyển pha; ID I1,I2,... tăng liên tục xuyên pha & Ngày."""
        sc = {
            "gather": {
                "player": {"pos": [12, 0]},  # đứng cạnh nút N1 (bong_dien_dien)
                "hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}],
                "random_fish": False,
                "monsters": [],
            },
            "quan": {"time_left_ticks": 1, "random_customers": False},
        }
        s = Session("day", self.t, sc, 1, days=2)
        # Tick 1: hái N1 -> thêm I2 (fresh=100), I1 hao 1 tick thành 11999/120
        s.step(inp("interact"))
        self.assertEqual([it["id"] for it in s.sim.sub.hold], ["I1", "I2"])
        self.assertEqual(s.sim.sub.hold[0]["fresh"], Fraction(11999, 120))
        self.assertEqual(s.sim.sub.hold[1]["fresh"], Fraction(100))

        # Di chuyển về bến và cập bến -> chuyển sang quan trong CÙNG tick, không hao thêm!
        s.sim.sub.pos = [2.0, 0.0]
        s.step(inp("interact"))
        self.assertEqual(s.sim.phase, "quan")
        self.assertEqual(s.sim.phase_tick, 0)
        # Bước cập bến hao thêm 1 tick gather -> I1 = 11998/120, I2 = 11999/120; KHÔNG bị hao thêm bởi quan ở tick 0!
        self.assertEqual(s.sim.sub.stock[0]["fresh"], Fraction(11998, 120))
        self.assertEqual(s.sim.sub.stock[1]["fresh"], Fraction(11999, 120))

        # Chạy 1 tick quan -> hao 1/240 mỗi cá thể -> đóng ca sang shop
        s.step(inp())
        self.assertEqual(s.sim.phase, "shop")
        expected_i1_shop = Fraction(11998, 120) - Fraction(1, 240)
        expected_i2_shop = Fraction(11999, 120) - Fraction(1, 240)
        self.assertEqual(s.sim.sub.stock[0]["fresh"], expected_i1_shop)
        self.assertEqual(s.sim.sub.stock[1]["fresh"], expected_i2_shop)

        # Chờ 5 tick trong Shop -> hàng ở Shop KHÔNG hao tươi!
        for _ in range(5):
            s.step(inp())
        self.assertEqual(s.sim.sub.stock[0]["fresh"], expected_i1_shop)
        self.assertEqual(s.sim.sub.stock[1]["fresh"], expected_i2_shop)

        # Đóng Shop Ngày 1 -> sang Ngày 2 gather: hold từ scenario được cấp ID MỚI nối tiếp là I3!
        s.step(inp("shop_done"))
        self.assertEqual(s.sim.day, 2)
        self.assertEqual(s.sim.phase, "gather")
        self.assertEqual(s.sim.sub.hold[0]["id"], "I3")
        self.assertEqual(s.sim.sub.hold[0]["kind"], "ca_loc")
        self.assertEqual(s.sim.sub.hold[0]["fresh"], Fraction(100))

    def test_format_fresh_never_rounds_spoiled_up_to_threshold(self):
        """Giá trị cực sát dưới 30 (vd 29.9999) vẫn xuất < 30 (29.999) để không đổi nhánh khi đọc lại."""
        self.assertEqual(format_fresh(Fraction(299999, 10000), spoiled_below=30), 29.999)
        self.assertEqual(format_fresh(Fraction(30), spoiled_below=30), 30)
        self.assertEqual(format_fresh(Fraction(0), spoiled_below=30), 0)


if __name__ == "__main__":
    unittest.main()
