"""Benchmark có render 1280×720 cho cảnh buổi sáng lõi (Test Contract v1.3).

Cách chạy:
    python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json

Cảnh đo:
  - Buổi sáng lõi (`GatherSim` v1.2): độ tươi, cá bơi, Cá Sấu Năm Chèo, nút hái và hiệu ứng mặc định;
    Út Sen đứng yên ở bến (`[2, 0]`).
  - Cửa sổ 1280×720 (dùng `tkinter.Canvas` khi có màn hình; tự chuyển sang bộ đệm RGB 1280×720 nếu chạy
    trong môi trường Linux không có X11/DISPLAY).
  - Làm nóng 3 giây mặc định, sau đó đo trong `--duration` giây và ghi nguyên tử 5 trường JSON:
    `avg_fps`, `p1_low_fps`, `frames`, `measured_s`, `load_ms`.
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
from .ids import IdAllocator
from .inputs import InputState
from .rng import Streams
from .sim.gather import GatherSim

WIDTH = 1280
HEIGHT = 720
STEP_DT = 1.0 / 60.0
IDLE_INPUT = InputState((0.0, 0.0), {}, set())


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


class _TkRiverRenderer:
    """Renderer cửa sổ thật 1280×720 chỉ dùng thư viện chuẩn `tkinter`."""

    def __init__(self, tuning):
        import tkinter as tk

        self.tk = tk
        self.t = tuning["gather"]
        self.root = tk.Tk()
        self.root.title("Quán Ăn Chợ Nổi — Benchmark 1280×720 (Contract v1.3)")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="#0b2239", highlightthickness=0)
        self.canvas.pack()

        b = self.t["bounds"]
        self.X = float(b["x"][1])
        self.D = float(b["d"][1])
        self.top = 72.0
        self.bottom = 52.0
        self.sky_h = 108.0
        self.water_y = self.top + self.sky_h
        self.water_h = HEIGHT - self.water_y - self.bottom
        self.sx = (WIDTH - 40.0) / self.X
        self.sy = self.water_h / self.D
        self.ox = 20.0

        # Nền tĩnh: trời, nước nhiều dải độ sâu, bến gỗ, vạch độ sâu
        self.canvas.create_rectangle(0, 0, WIDTH, self.top, fill="#101820", outline="")
        self.canvas.create_rectangle(0, self.top, WIDTH, self.water_y, fill="#bfe4f5", outline="")
        bands = ("#3ea9d8", "#2d8ec0", "#1e6fa0", "#124d78", "#0a3254", "#062038")
        bh = self.water_h / len(bands)
        for i, col in enumerate(bands):
            y0 = self.water_y + i * bh
            self.canvas.create_rectangle(0, y0, WIDTH, y0 + bh + 1, fill=col, outline="")
        self.canvas.create_line(0, self.water_y, WIDTH, self.water_y, fill="#eaf8ff", width=2)
        for d in range(5, int(self.D) + 1, 5):
            yd = self.water_y + d * self.sy
            self.canvas.create_line(self.ox, yd, WIDTH - self.ox, yd, fill="#2c6082", dash=(4, 6))
            self.canvas.create_text(self.ox + 4, yd - 8, text=f"{d}m", fill="#a8d4eb", anchor="w", font=("Segoe UI", 9))

        # Bến gỗ + mái chòi
        dp = self.t["dock_pos"]
        dx = self._x(dp[0])
        self.canvas.create_rectangle(dx - 26, self.water_y - 12, dx + 26, self.water_y + 4, fill="#8d5e34", outline="#4e3015")
        self.canvas.create_polygon(dx - 30, self.water_y - 12, dx, self.water_y - 42, dx + 30, self.water_y - 12, fill="#b9503a", outline="#6e281a")
        self.canvas.create_text(dx, self.water_y - 52, text="Bến (E)", fill="#3b2210", font=("Segoe UI", 10, "bold"))

        # Tia nắng động (dùng đường nét mảnh thay vì polygon stipple để tránh nghẽn GDI trên Tk)
        self.rays = []
        for i in range(5):
            rx = 160 + i * 240
            rid = self.canvas.create_line(
                rx, self.water_y, rx + 70, self.water_y + 240,
                fill="#76d2f0", width=3,
            )
            self.rays.append((rid, rx))

        # Thực thể động (tái sử dụng item id để không rò bộ nhớ)
        self.node_items = {}
        self.fish_items = {}
        self.monster_items = {}
        self.player_item = self.canvas.create_oval(0, 0, 18, 18, fill="#ff9f43", outline="#fff3d1", width=2)
        self.hud_text = self.canvas.create_text(16, 22, text="", fill="#f8fafc", anchor="w", font=("Segoe UI", 12, "bold"))
        self.sub_text = self.canvas.create_text(16, 48, text="", fill="#bae6fd", anchor="w", font=("Segoe UI", 10))
        self.fps_text = self.canvas.create_text(WIDTH - 16, 22, text="", fill="#fde047", anchor="e", font=("Segoe UI", 11, "bold"))

    def _x(self, x: float) -> float:
        return self.ox + x * self.sx

    def _y(self, d: float) -> float:
        return self.water_y + d * self.sy

    def render(self, sim: GatherSim, frame_idx: int):
        if frame_idx % 2 == 0:
            phase = frame_idx * 0.04
            for idx, (rid, base_x) in enumerate(self.rays):
                shift = math.sin(phase + idx * 1.1) * 12.0
                rx = base_x + shift
                self.canvas.coords(rid, rx, self.water_y, rx + 68, self.water_y + 230)

        # Nút hái (vị trí tĩnh trên mặt nước, chỉ tạo mới nếu chưa có)
        for n in sim.nodes:
            nid = n["id"]
            if nid not in self.node_items:
                nx, ny = self._x(n["pos"][0]), self._y(n["pos"][1])
                col = "#f2c230" if n["kind"] == "bong_dien_dien" else ("#e8799c" if n["kind"] == "bong_sung" else "#8fcf6b")
                self.node_items[nid] = self.canvas.create_oval(nx - 9, ny - 6, nx + 9, ny + 6, fill=col, outline="#ffffff")

        # Đàn cá
        alive_fish = set()
        for f in sim.fish:
            fid = f["id"]
            alive_fish.add(fid)
            fx, fy = self._x(f["pos"][0]), self._y(f["pos"][1])
            if fid not in self.fish_items:
                col = "#d6e6f2" if f["kind"] == "ca_linh" else ("#7c9a52" if f["kind"] == "ca_loc" else "#d9a066")
                self.fish_items[fid] = self.canvas.create_oval(fx - 10, fy - 5, fx + 10, fy + 5, fill=col, outline="#0e2a42")
            else:
                self.canvas.coords(self.fish_items[fid], fx - 10, fy - 5, fx + 10, fy + 5)
        for fid in list(self.fish_items):
            if fid not in alive_fish:
                self.canvas.delete(self.fish_items.pop(fid))

        # Cá Sấu Năm Chèo
        for m in sim.monsters:
            mid = m["id"]
            mx, my = self._x(m["pos"][0]), self._y(m["pos"][1])
            if mid not in self.monster_items:
                self.monster_items[mid] = self.canvas.create_rectangle(mx - 18, my - 8, mx + 18, my + 8, fill="#dc2626", outline="#fef08a", width=2)
            else:
                self.canvas.coords(self.monster_items[mid], mx - 18, my - 8, mx + 18, my + 8)

        # Út Sen
        px, py = self._x(sim.pos[0]), self._y(sim.pos[1])
        self.canvas.coords(self.player_item, px - 10, py - 10, px + 10, py + 10)

        # HUD
        if frame_idx % 8 == 0:
            self.canvas.itemconfigure(
                self.hud_text,
                text=f"Cảnh đo v1.3 (1280×720) · Thời gian {math.ceil(sim.time_left_ticks / 60)}s · Oxy {math.ceil(sim.oxygen_ticks / 60)}s · HP {sim.hp}/{sim.hp_max}",
            )
            self.canvas.itemconfigure(
                self.sub_text,
                text=f"Cá đang bơi: {len(sim.fish)} · Thủy quái: {len(sim.monsters)} · Giỏ: {len(sim.hold)}/{sim.t['hold_capacity']} · Tick: {sim.phase_tick}",
            )
            self.canvas.itemconfigure(self.fps_text, text=f"Frame #{frame_idx}")

        self.root.update()

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class _OffscreenRGBRenderer:
    """Bộ đệm RGB 1280×720 dự phòng cho môi trường Linux không có X11/DISPLAY."""

    def __init__(self, tuning):
        self.t = tuning["gather"]
        b = self.t["bounds"]
        self.X = float(b["x"][1])
        self.D = float(b["d"][1])
        self.stride = WIDTH * 3
        self.bg = bytearray(WIDTH * HEIGHT * 3)
        # Dựng sẵn nền bầu trời + mặt nước theo từng dòng scanline (C-speed slice copy)
        sky_row = bytes((191, 228, 245)) * WIDTH
        water_top = bytes((62, 169, 216)) * WIDTH
        water_deep = bytes((8, 36, 63)) * WIDTH
        for y in range(HEIGHT):
            off = y * self.stride
            if y < 180:
                self.bg[off:off + self.stride] = sky_row
            elif y < 440:
                self.bg[off:off + self.stride] = water_top
            else:
                self.bg[off:off + self.stride] = water_deep
        self.frame = bytearray(self.bg)

    def _fill_rect(self, x0: int, y0: int, w: int, h: int, rgb: bytes):
        x0 = max(0, min(WIDTH - 1, x0))
        y0 = max(0, min(HEIGHT - 1, y0))
        x1 = max(x0 + 1, min(WIDTH, x0 + w))
        y1 = max(y0 + 1, min(HEIGHT, y0 + h))
        row = rgb * (x1 - x0)
        rw = len(row)
        for y in range(y0, y1):
            off = y * self.stride + x0 * 3
            self.frame[off:off + rw] = row

    def render(self, sim: GatherSim, frame_idx: int):
        # Sao chép nền 1280×720 ở tốc độ C memcpy rồi vẽ toàn bộ thực thể đang hoạt động
        self.frame[:] = self.bg
        for n in sim.nodes:
            nx = int((n["pos"][0] / self.X) * (WIDTH - 40)) + 20
            self._fill_rect(nx - 6, 174, 12, 12, b"\xf2\xc2\x30")
        for f in sim.fish:
            fx = int((f["pos"][0] / self.X) * (WIDTH - 40)) + 20
            fy = int(180 + (f["pos"][1] / self.D) * (HEIGHT - 220))
            self._fill_rect(fx - 8, fy - 4, 16, 8, b"\xd6\xe6\xf2")
        for m in sim.monsters:
            mx = int((m["pos"][0] / self.X) * (WIDTH - 40)) + 20
            my = int(180 + (m["pos"][1] / self.D) * (HEIGHT - 220))
            self._fill_rect(mx - 14, my - 6, 28, 12, b"\xdc\x26\x26")
        px = int((sim.pos[0] / self.X) * (WIDTH - 40)) + 20
        py = int(180 + (sim.pos[1] / self.D) * (HEIGHT - 220))
        self._fill_rect(px - 8, py - 8, 16, 16, b"\xff\x9f\x43")

    def close(self):
        pass


def _create_renderer(tuning):
    if os.environ.get("CHONOI_BENCH_OFFSCREEN") == "1":
        return _OffscreenRGBRenderer(tuning)
    try:
        return _TkRiverRenderer(tuning)
    except Exception:
        return _OffscreenRGBRenderer(tuning)


def compute_bench_metrics(frame_times: list, measured_s: float, load_ms: float) -> dict:
    frames = len(frame_times)
    if frames <= 0 or measured_s <= 0:
        raise ValueError("cần ít nhất 1 khung hình và measured_s > 0")
    avg_fps = frames / measured_s
    k = max(1, math.ceil(0.01 * frames))
    slowest = sorted(frame_times, reverse=True)[:k]
    avg_slow_dt = sum(slowest) / len(slowest)
    p1_low_fps = (1.0 / avg_slow_dt) if avg_slow_dt > 0 else avg_fps
    return {
        "avg_fps": round(avg_fps, 2),
        "p1_low_fps": round(p1_low_fps, 2),
        "frames": frames,
        "measured_s": round(measured_s, 3),
        "load_ms": round(load_ms, 2),
    }


def _write_json_atomic(path: str, data: dict):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".bench-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def run_benchmark(seed: int, duration_s: float, warmup_s: float = 3.0) -> dict:
    t_launch = time.perf_counter()
    tuning = load_contract()["tuning"]
    sim = GatherSim(tuning, {}, Streams(seed), IdAllocator(), day=1)
    renderer = _create_renderer(tuning)
    try:
        # Khung hình đầu tiên của cảnh đo -> chốt load_ms
        renderer.render(sim, 0)
        load_ms = (time.perf_counter() - t_launch) * 1000.0

        frame_idx = 1
        acc = 0.0
        prev = time.perf_counter()

        # Giai đoạn làm nóng (mặc định 3 s)
        warm_end = prev + max(0.0, warmup_s)
        while True:
            now = time.perf_counter()
            if now >= warm_end:
                break
            dt = min(0.1, now - prev)
            prev = now
            acc += dt
            while acc >= STEP_DT:
                sim.step(IDLE_INPUT)
                if sim.done:
                    sim = GatherSim(tuning, {}, Streams(seed), IdAllocator(), day=1)
                acc -= STEP_DT
            renderer.render(sim, frame_idx)
            frame_idx += 1

        # Giai đoạn đo chính thức (--duration giây)
        frame_times = []
        meas_start = time.perf_counter()
        prev = meas_start
        meas_end = meas_start + duration_s
        while True:
            f_start = time.perf_counter()
            if f_start >= meas_end and frame_times:
                break
            dt = min(0.1, f_start - prev)
            prev = f_start
            acc += dt
            while acc >= STEP_DT:
                sim.step(IDLE_INPUT)
                if sim.done:
                    sim = GatherSim(tuning, {}, Streams(seed), IdAllocator(), day=1)
                acc -= STEP_DT
            renderer.render(sim, frame_idx)
            f_end = time.perf_counter()
            frame_times.append(max(1e-6, f_end - f_start))
            frame_idx += 1
            if f_end >= meas_end:
                break

        measured_s = time.perf_counter() - meas_start
        return compute_bench_metrics(frame_times, measured_s, load_ms)
    finally:
        renderer.close()


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.bench")
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--duration", required=True, type=float)
    p.add_argument("--out", required=True)
    p.add_argument("--warmup", type=float, default=3.0)
    a = p.parse_args(argv)
    try:
        if not math.isfinite(a.duration) or a.duration <= 0:
            raise BadInput("--duration phải là số dương")
        if not math.isfinite(a.warmup) or a.warmup < 0:
            raise BadInput("--warmup phải >= 0")
        result = run_benchmark(a.seed, a.duration, warmup_s=a.warmup)
        _write_json_atomic(a.out, result)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"lỗi ghi: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
