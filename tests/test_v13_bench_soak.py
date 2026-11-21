"""Kiểm thử Test Contract v1.3 (Phase 4): bench_cmd, soak_cmd, cảnh báo & tương phản cao."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chonoi.bench import compute_bench_metrics
from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.rng import Streams
from chonoi.sim.day import DaySim

ROOT = Path(__file__).resolve().parent.parent


def _run(module: str, *args: str, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )


class TestContractV13(unittest.TestCase):
    def test_contract_declares_v13_bench_and_soak(self):
        c = load_contract()
        self.assertEqual(c["contract_version"], "1.3")
        self.assertTrue(c.get("bench_cmd"))
        self.assertTrue(c.get("soak_cmd"))
        self.assertIn("chonoi.bench", c["bench_cmd"])
        self.assertIn("chonoi.soak", c["soak_cmd"])

    def test_compute_bench_metrics_formula(self):
        # 100 khung: 99 khung 0.01s (100 FPS), 1 khung chậm nhất 0.05s (20 FPS)
        # k = max(1, ceil(0.01 * 100)) = 1 -> p1_low_fps = 1 / 0.05 = 20.0
        times = [0.01] * 99 + [0.05]
        m = compute_bench_metrics(times, measured_s=1.04, load_ms=123.45)
        self.assertEqual(set(m.keys()), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
        self.assertEqual(m["frames"], 100)
        self.assertAlmostEqual(m["avg_fps"], round(100 / 1.04, 2), places=2)
        self.assertAlmostEqual(m["p1_low_fps"], 20.0, places=2)
        self.assertAlmostEqual(m["load_ms"], 123.45, places=2)

        # 250 khung: k = ceil(2.5) = 3 khung chậm nhất [0.04, 0.03, 0.02] -> avg = 0.03 -> 33.33 FPS
        times2 = [0.008] * 247 + [0.02, 0.03, 0.04]
        m2 = compute_bench_metrics(times2, measured_s=2.066, load_ms=50.0)
        self.assertAlmostEqual(m2["p1_low_fps"], round(1.0 / 0.03, 2), places=2)

    def test_bench_cli_outputs_exact_schema_and_validates_args(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "bench.json"
            p = _run(
                "chonoi.bench",
                "--seed", "42",
                "--warmup", "0.05",
                "--duration", "0.25",
                "--out", str(out),
                env_extra={"CHONOI_BENCH_OFFSCREEN": "1"},
            )
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(out.exists())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(set(data.keys()), {"avg_fps", "p1_low_fps", "frames", "measured_s", "load_ms"})
            self.assertGreater(data["frames"], 0)
            self.assertGreater(data["measured_s"], 0)
            self.assertGreater(data["avg_fps"], 0)
            self.assertGreater(data["p1_low_fps"], 0)
            self.assertGreaterEqual(data["avg_fps"], data["p1_low_fps"])
            self.assertGreaterEqual(data["load_ms"], 0)

            bad = Path(td) / "bad.json"
            p_bad = _run("chonoi.bench", "--seed", "42", "--duration", "0", "--out", str(bad))
            self.assertEqual(p_bad.returncode, 2)
            self.assertFalse(bad.exists())

    def test_day_plan_repeats_d1_d5_on_days_6_to_10(self):
        tuning = load_contract()["tuning"]
        d = DaySim(tuning, {}, Streams(7), IdAllocator(), days=10)
        mapped = []
        for day_num in range(1, 11):
            d.day = day_num
            mapped.append(d._plan_day_key())
        self.assertEqual(mapped, [1, 2, 3, 4, 5, 1, 2, 3, 4, 5])

    def test_soak_10_days_completes_without_crash_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            out1 = Path(td) / "soak1.json"
            out2 = Path(td) / "soak2.json"
            p1 = _run("chonoi.soak", "--seed", "7", "--days", "10", "--out", str(out1))
            p2 = _run("chonoi.soak", "--seed", "7", "--days", "10", "--out", str(out2))
            self.assertEqual(p1.returncode, 0, p1.stderr)
            self.assertEqual(p2.returncode, 0, p2.stderr)

            d1 = json.loads(out1.read_text(encoding="utf-8"))
            d2 = json.loads(out2.read_text(encoding="utf-8"))
            for d in (d1, d2):
                self.assertEqual(set(d.keys()), {"days", "days_completed", "crashes", "results", "duration_s"})
                self.assertEqual(d["days"], 10)
                self.assertEqual(d["days_completed"], 10)
                self.assertEqual(d["crashes"], 0)
                self.assertEqual(len(d["results"]), 10)
                self.assertEqual([r["day"] for r in d["results"]], list(range(1, 11)))
                for r in d["results"]:
                    self.assertEqual(set(r.keys()), {"day", "earned", "reputation", "score"})
                    self.assertIsInstance(r["earned"], int)
                    self.assertIsInstance(r["score"], int)

            # Kiểm tính lặp tuyệt đối ở các trường gameplay (bỏ duration_s)
            for key in ("days", "days_completed", "crashes", "results"):
                self.assertEqual(d1[key], d2[key])

            bad = Path(td) / "bad_soak.json"
            p_bad = _run("chonoi.soak", "--seed", "7", "--days", "0", "--out", str(bad))
            self.assertEqual(p_bad.returncode, 2)
            self.assertFalse(bad.exists())

    def test_ui_has_three_clear_warnings_and_high_contrast_mode(self):
        html = (ROOT / "chonoi" / "web" / "index.html").read_text(encoding="utf-8")
        # 3 cảnh báo có chữ / biểu tượng rõ ràng
        self.assertIn("THỦY QUÁI GẦN", html)
        self.assertIn("SẮP HẾT OXY!", html)
        self.assertIn("KHÁCH SẮP GIẬN", html)
        # Chế độ tương phản cao (nút bật/tắt + lớp CSS + phím H)
        self.assertIn("contrast-toggle", html)
        self.assertIn("high-contrast", html)
        self.assertIn("Tương phản cao", html)


if __name__ == "__main__":
    unittest.main()
