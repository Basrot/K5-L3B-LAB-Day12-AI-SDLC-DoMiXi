"""Test cửa sổ chơi trực tiếp (chonoi.live). Chỉ dành cho starter Python: nhóm đổi ngôn ngữ thì xóa file này."""

import json
import io
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from chonoi.contract import load_contract
from chonoi.inventory import read_inventory
from chonoi.live import LiveGame, LiveServer, main


def _get(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        return r.status, r.read()


def _post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        e.close()
        return e.code


class LiveServerTest(unittest.TestCase):
    def test_main_starts_with_windows_legacy_console_encoding(self):
        output = io.BytesIO()
        console = io.TextIOWrapper(output, encoding="cp1252")
        with patch("chonoi.live.LiveServer") as server_type, \
             patch("chonoi.live.time.sleep", side_effect=KeyboardInterrupt), \
             patch("sys.stdout", console):
            server_type.return_value.url = "http://127.0.0.1:8000/"
            self.assertEqual(main(["--mode", "campaign", "--port", "0"]), 0)
            server_type.return_value.start.assert_called_once()
            server_type.return_value.stop.assert_called_once()

    def test_state_input_and_clean_stop(self):
        tuning = load_contract()["tuning"]
        server = LiveServer(LiveGame("gather", tuning, {}, 1), port=0)  # cổng ngẫu nhiên
        server.start()
        try:
            base = f"http://127.0.0.1:{server.port}"
            code, body = _get(base + "/state")
            self.assertEqual(code, 200)
            st = json.loads(body)
            self.assertIn("tick", st)
            self.assertEqual(st["mode"], "gather")
            self.assertEqual(st["player"]["pos"], [2, 0])
            self.assertEqual(_post(base + "/input", {"move": [1, 0], "interact": False, "catch": False}), 200)
            self.assertEqual(_post(base + "/input", {"move": [5, 0]}), 400)
            code, html = _get(base + "/")
            self.assertEqual(code, 200)
            self.assertIn(b"<canvas", html)
            deadline = time.time() + 3
            while time.time() < deadline:
                st2 = json.loads(_get(base + "/state")[1])
                if st2["tick"] > st["tick"] + 3 and st2["player"]["pos"][0] > st["player"]["pos"][0]:
                    break
                time.sleep(0.05)
            self.assertGreater(st2["tick"], st["tick"], "mô phỏng phải chạy nền")
            self.assertGreater(st2["player"]["pos"][0], st["player"]["pos"][0], "input phải tác động tới sim")
        finally:
            server.stop()
        self.assertFalse(server.game._thread.is_alive())
        self.assertFalse(server._thread.is_alive())

    def test_live_gather_inventory_out_writes_valid_v12_and_loads_in_quan(self):
        """Xuất --inventory-out từ bản live phải ghi đúng schema kho cá thể v1.2 (lọc nguyên liệu ngoài contract)."""
        tuning = load_contract()["tuning"]
        with tempfile.TemporaryDirectory() as d:
            inv_path = os.path.join(d, "live_catch.json")
            lg = LiveGame("gather", tuning, {}, 1, inventory_out=inv_path)
            lg.session.sim.hold = ["ca_loc", "ca_ro"]
            lg.inputs.set(interact=True)
            lg._tick_once()
            self.assertTrue(os.path.exists(inv_path))
            items = read_inventory(inv_path)
            self.assertEqual([it["kind"] for it in items], ["ca_loc"])
            lq = LiveGame("quan", tuning, {}, 1, inventory=items)
            lq._tick_once()
            self.assertIsNone(lq.error)
            self.assertEqual(lq.session.sim.stock, {"ca_loc": 1})


if __name__ == "__main__":
    unittest.main()
