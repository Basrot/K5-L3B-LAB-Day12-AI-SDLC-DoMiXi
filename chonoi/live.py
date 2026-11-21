"""Cửa sổ chơi trực tiếp bằng TRÌNH DUYỆT, chỉ dùng thư viện chuẩn Python.

    python3 -m chonoi.live --mode gather|quan [--seed N] [--port 8000]

Máy chủ HTTP nhỏ (ThreadingHTTPServer) phục vụ `chonoi/web/index.html` và hai API:
    GET  /state  -> snapshot JSON hiện tại (cùng trường như dòng snapshot của headless) + `meta` + `events`
    POST /input  -> {"move": [a, b], "interact": bool, "catch": bool}   (trạng thái phím đang giữ)
    POST /restart -> chơi lại từ đầu (cùng seed, cùng scenario)

Mô phỏng chạy 60 tick/s trong một luồng nền, dùng CÙNG lớp sim như headless (qua `runner.Session`).
Client chỉ ĐỌC snapshot và tự bỏ qua trường chưa có, nên luật do nhóm viết thêm trường nào cũng không vỡ.
Ngẫu nhiên vẫn đi qua `Streams` (seed); chỉ nhịp chạy theo đồng hồ thật, không đi vào luật.
"""

import argparse
import json
import os
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .contract import load_contract
from .errors import BadInput
from .inputs import LiveInputs
from .inventory import read_inventory
from .runner import Session
from .scenario import load_scenario
from .sim.live_gather import LiveGatherSim
from .sim.live_quan import LiveQuanSim
from .live_world import live_tuning
from .inventory import hold_to_items
from .progression import load_progression, settle_day, buy_upgrade
from pathlib import Path
from urllib.parse import unquote

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
TICK_S = 1.0 / 60.0
MAX_BODY = 4096
RECENT_EVENTS = 40


class LiveGame:
    """Một lượt chơi + luồng nền bước 60 tick/s. Mọi truy cập trạng thái đi qua khóa."""

    def __init__(self, mode, tuning, scenario, seed, inventory=None, inventory_out=None):
        tuning = live_tuning(tuning)
        self._args = (mode, tuning, scenario, seed, inventory)
        self.mode = mode
        self.tuning = tuning
        self.inventory_out = inventory_out
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._sessions = {}
        self._demo_mode = False
        self._reset()

    def _reset(self):
        self.session = Session(*self._args)
        if self.mode == 'gather':
            old = self.session.sim
            self.session.sim = LiveGatherSim(self.tuning, self._args[2], old.rng, old.ids)
        else:
            old = self.session.sim
            self.session.sim = LiveQuanSim(self.tuning, self._args[2], old.rng, old.ids, self._args[4])
        self._sessions['quan-demo' if self._demo_mode else self.mode] = self.session
        self.inputs = LiveInputs()
        self.events = []
        self._saved = False
        self.error = None

    # --- luồng nền ----------------------------------------------------------------
    def start(self):
        self._thread = threading.Thread(target=self._loop, name="chonoi-sim", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        nxt = time.perf_counter()
        while not self._stop.is_set():
            nxt += TICK_S
            with self._lock:
                try:
                    self._tick_once()
                except Exception:  # luật của nhóm lỗi: báo ra terminal + client, dừng bước (restart để chơi lại)
                    self.error = traceback.format_exc()
                    sys.stderr.write(self.error)
                    self.session.sim.done = True
                    self.session.sim.reason = "error"
            delay = nxt - time.perf_counter()
            if delay > 0:
                self._stop.wait(delay)
            elif delay < -0.25:  # chạy chậm quá thì bỏ bù, tránh chạy dồn
                nxt = time.perf_counter()

    def _tick_once(self):
        s = self.session
        if s.done:
            return
        for row in s.step(self.inputs.advance()):
            self.events.append(row)
            if getattr(self, 'campaign', False) and row['name'] == 'paid':
                dish = row['data'].get('dish_id')
                if dish:
                    self.paid_by_dish[dish] = self.paid_by_dish.get(dish, 0) + 1
        del self.events[:-RECENT_EVENTS]
        if s.done and not self._saved:
            self._saved = True
            if getattr(self, 'campaign', False):
                if self.mode == 'quan':
                    self.result = settle_day(self.contract, self.progression, self.day,
                        paid_by_dish=self.paid_by_dish, earned=s.sim.shift_earned,
                        reputation=s.sim.reputation, money_after_shift=s.sim.money,
                        wallet_before_shift=self.wallet)
                    self.wallet = self.result['money_after_reward']
                    self.reputation = s.sim.reputation
                    self.stars[str(self.day)] = max(self.stars.get(str(self.day), 0), self.result['stars'])
                    self.screen = 'results'
                    self._save_progress()
                elif s.sim.reason == 'fainted':
                    self.result = {'day': self.day, 'stars': 0, 'earned_from_customers': 0,
                                   'bonus': 0, 'total_earned_this_day': 0, 'reputation': self.reputation,
                                   'paid_count': 0, 'fulfilled_count': 0}
                    self.screen = 'results'
            if self.inventory_out:
                try:
                    s.write_inventory_if_done(self.inventory_out)
                except OSError as e:
                    sys.stderr.write(f"lỗi ghi kho: {e}\n")

    # --- API cho handler -----------------------------------------------------------
    def state_json(self) -> bytes:
        with self._lock:
            snap = self.session.snapshot()
            snap["meta"] = self.session.sim.t
            snap["events"] = list(self.events)
            snap["finished"] = self.session.done
            snap["reason"] = self.session.sim.reason if self.session.done else None
            snap["error"] = self.error
            if getattr(self, 'campaign', False):
                snap['campaign'] = {
                    'screen': self.screen, 'day': self.day, 'wallet': self.wallet,
                    'reputation': self.reputation, 'stars': self.stars, 'result': self.result,
                    'intro_seen': self.intro_seen, 'upgrades': self.upgrades,
                    'upgrade_catalog': self.progression['upgrades'],
                    'day_count': len(self.contract['tuning']['day_plan']),
                }
            return json.dumps(snap, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def set_input(self, body: dict):
        move = body.get("move")
        if move is not None:
            ok = (isinstance(move, list) and len(move) == 2 and
                  all(isinstance(c, (int, float)) and not isinstance(c, bool) and abs(c) <= 1 for c in move))
            if not ok:
                raise ValueError("move phải là [a, b] trong [-1, 1]")
        buttons = {}
        for b in ("interact", "catch"):
            if b in body:
                if not isinstance(body[b], bool):
                    raise ValueError(f"{b} phải là boolean")
                buttons[b] = body[b]
        with self._lock:
            self.inputs.set(move, **buttons)

    def restart(self):
        with self._lock:
            if self.mode == 'quan' and not self._demo_mode:
                # Restart the shift using its unspent stock, not just the last delivery.
                self._args = (self.mode, self.tuning, {}, self._args[3], dict(self.session.sim.stock))
            self._reset()

    def switch_mode(self, mode, demo=False):
        if getattr(self, 'campaign', False):
            raise ValueError('Dùng màn chọn level để chuyển cảnh')
        if mode not in ('gather', 'quan'):
            raise ValueError('mode phải là gather hoặc quan')
        if demo and mode != 'quan':
            raise ValueError('demo chỉ dành cho quan')
        with self._lock:
            if mode == self.mode and self._demo_mode == demo:
                return
            stock = None
            if self.mode == 'gather' and mode == 'quan' and not demo:
                stock = hold_to_items(self.session.sim.hold)
                self.session.sim.hold.clear()
            self.mode = mode
            self._demo_mode = demo
            key = 'quan-demo' if demo else mode
            cached = self._sessions.get(key)
            if cached is not None and mode == 'quan' and cached.done:
                remaining = dict(cached.sim.stock)
                for k, v in (stock or {}).items():
                    remaining[k] = remaining.get(k, 0) + v
                stock = remaining
                cached = None
            if cached is not None:
                self.session = cached
                if stock is not None:
                    for k, v in stock.items():
                        self.session.sim.stock[k] = self.session.sim.stock.get(k, 0) + v
            else:
                self.session = Session(mode, self.tuning, {}, self._args[3], stock)
                old = self.session.sim
                self.session.sim = (LiveGatherSim(self.tuning, {}, old.rng, old.ids) if mode == 'gather'
                                    else LiveQuanSim(self.tuning, {}, old.rng, old.ids, stock))
                self._sessions[key] = self.session
            self._args = (mode, self.tuning, {}, self._args[3], stock)
            self.inputs = LiveInputs()
            self.events = []
            self.error = None
            self._saved = False


class CampaignLiveGame(LiveGame):
    """Luồng nhiều ngày chỉ chạy trong Live; không can thiệp runner headless."""

    def __init__(self, tuning, seed):
        super().__init__('gather', tuning, {}, seed)
        self.campaign = True
        self.contract = {'tuning': tuning}
        self.progression = load_progression()
        self.screen = 'title'
        self.day = 1
        self.wallet = 0
        self.reputation = tuning['quan']['reputation_initial']
        self.stars = {}
        self.upgrades = {name: 0 for name in self.progression['upgrades']}
        self.intro_seen = False
        self.result = None
        self.paid_by_dish = {}
        self.day_stock = None
        self.save_path = Path(__file__).resolve().parent.parent / '.chonoi-save.json'
        self._load_progress()

    def _load_progress(self):
        try:
            saved = json.loads(self.save_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        self.wallet = max(0, int(saved.get('wallet', 0)))
        self.reputation = max(0.0, min(5.0, float(saved.get('reputation', self.reputation))))
        self.stars = {str(k): max(0, min(3, int(v))) for k, v in saved.get('stars', {}).items()}
        self.intro_seen = bool(saved.get('intro_seen', False))
        for item, level in saved.get('upgrades', {}).items():
            if item in self.upgrades:
                self.upgrades[item] = max(0, min(len(self.progression['upgrades'][item]['levels']) - 1, int(level)))

    def _save_progress(self):
        data = {'wallet': self.wallet, 'reputation': self.reputation, 'stars': self.stars,
                'intro_seen': self.intro_seen, 'upgrades': self.upgrades}
        temp = self.save_path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, self.save_path)

    def _tick_once(self):
        if self.screen == 'playing':
            super()._tick_once()

    def _new_phase(self, mode, stock=None):
        tuned = live_tuning(self.contract['tuning'])
        if mode == 'gather':
            for name, level in self.upgrades.items():
                stats = self.progression['upgrades'][name]['levels'][level]
                if name == 'oxygen': tuned['gather']['oxygen_max_s'] = stats['oxygen_max_s']
                elif name == 'hp': tuned['gather']['hp_max'] = stats['hp_max']
                elif name == 'fins': tuned['gather']['swim_speed'] *= stats['swim_speed_multiplier']
                elif name == 'helmet': tuned['gather']['max_depth'] = stats['max_depth']
                elif name == 'lamp': tuned['gather']['reveal_radius'] = stats['reveal_radius']
            scenario = {}
        else:
            plan = next(p for p in self.contract['tuning']['day_plan'] if p['day'] == self.day)
            scenario = {'reputation': self.reputation}
            tuned['menu'] = {k: v for k, v in tuned['menu'].items() if k in plan['dishes']}
            tuned['quan']['customer_interval_s'] = self.progression['days'][str(self.day)]['customer_interval_s']
        self.mode = mode
        self.tuning = tuned
        self.session = Session(mode, tuned, scenario, self._args[3], stock)
        old = self.session.sim
        if mode == 'gather':
            self.session.sim = LiveGatherSim(tuned, scenario, old.rng, old.ids)
        else:
            self.session.sim = LiveQuanSim(tuned, scenario, old.rng, old.ids, stock)
            self.session.sim.money = self.wallet
            self.session.sim.order_plan = dict(plan['dishes'])
            self.session.sim.extra_customer_limit = self.progression['days'][str(self.day)]['extra_customers']
        self.inputs = LiveInputs()
        self.events = []
        self._saved = False
        self.error = None
        self.screen = 'playing'

    def restart(self):
        with self._lock:
            if self.screen != 'playing':
                return
            if self.mode == 'quan':
                self.paid_by_dish = {}
                self._new_phase('quan', dict(self.day_stock or {}))
            else:
                self._new_phase('gather')

    def action(self, body):
        action = body.get('action')
        with self._lock:
            if action == 'start' and self.screen == 'title':
                self.screen = 'intro' if not self.intro_seen else 'map'
            elif action == 'intro_done' and self.screen == 'intro':
                self.intro_seen = True
                self.screen = 'map'
                self._save_progress()
            elif action == 'select_day' and self.screen in ('map', 'shop', 'results'):
                day = body.get('day')
                if type(day) is not int or day not in range(1, len(self.contract['tuning']['day_plan']) + 1):
                    raise ValueError('Màn không hợp lệ')
                if day > 1 and self.stars.get(str(day - 1), 0) < 1:
                    raise ValueError('Cần ít nhất 1 sao ở màn trước')
                self.day = day
                self.result = None
                self.paid_by_dish = {}
                self._new_phase('gather')
            elif action == 'evening' and self.screen == 'playing' and self.mode == 'gather':
                stock = hold_to_items(self.session.sim.hold)
                self.session.sim.hold.clear()
                self.day_stock = dict(stock)
                self._new_phase('quan', stock)
            elif action == 'shop' and self.screen in ('results', 'map'):
                self.screen = 'shop'
            elif action == 'map' and self.screen in ('shop', 'results'):
                self.screen = 'map'
            elif action == 'buy' and self.screen == 'shop':
                item = body.get('item')
                if item not in self.upgrades:
                    raise ValueError('Đồ nâng cấp không hợp lệ')
                purchase = buy_upgrade(self.progression, item, self.upgrades[item], self.wallet)
                self.wallet = purchase['money_left']
                self.upgrades[item] = purchase['level']
                self._save_progress()
            else:
                raise ValueError('Thao tác không hợp lệ ở màn hiện tại')


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    game: LiveGame = None  # gán trên lớp con trong make_server

    def log_message(self, fmt, *args):  # yên lặng
        pass

    def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/state":
            self._send(200, self.game.state_json())
        elif path in ("/", "/index.html"):
            try:
                with open(os.path.join(WEB_DIR, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._send(404, b'{"error":"thieu index.html"}')
        elif path.startswith('/art/'):
            name = unquote(path[len('/art/'):])
            allowed = {'01-ut-sen.png', '02-items-food.png', '03-props-npcs.png', '04-river-scene.png',
                       '05-restaurant-scene.png', '10-underwater-animation.png', '11-rain-pursuer.png',
                       '12-river-life.png', '13-dining-cast.png', '14-dishes.png', '15-quan-cho-noi.jpg',
                       '16-seated-waiting.png', '16-upgrade-shop.png', '22-upgrade-detail-template.png',
                       '24-title-screen.png', '25-level-select.png', '26-day-to-night.png',
                       '27-level-results.png', '29-intro-father-teaches-text.png',
                       '30-intro-father-injured-text.png', '31-intro-ut-sen-decides-text.png',
                       '32-intro-first-departure-text.png', '17-kha-banh.png', '18-cong-an.png',
                       'chieu-troi-mua.mp3'}
            if name not in allowed:
                self._send(404, b'{}')
                return
            asset = os.path.join(os.path.dirname(WEB_DIR), '..', 'assets', 'art-pack', name)
            ctype = 'audio/mpeg' if name.endswith('.mp3') else ('image/jpeg' if name.endswith(('.jpg', '.jpeg')) else 'image/png')
            try:
                with open(asset, 'rb') as f:
                    self._send(200, f.read(), ctype)
            except OSError:
                self._send(404, b'{}')
        elif path == '/audio/lobby.mp3':
            audio = os.path.join(os.path.dirname(WEB_DIR), '..', 'assets', 'audio', 'lobby-music.mp3')
            try:
                with open(audio, 'rb') as f:
                    self._send(200, f.read(), 'audio/mpeg')
            except OSError:
                self._send(404, b'{}')
        else:
            self._send(404, b'{"error":"khong co"}')

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > MAX_BODY:
            self._send(400, b'{"error":"body sai"}')
            return
        raw = self.rfile.read(n) if n else b""
        try:
            if path == "/input":
                body = json.loads(raw.decode("utf-8") or "{}")
                if not isinstance(body, dict):
                    raise ValueError("body phải là object")
                self.game.set_input(body)
            elif path == "/restart":
                self.game.restart()
            elif path == '/mode':
                body = json.loads(raw.decode('utf-8') or '{}')
                if not isinstance(body, dict) or not isinstance(body.get('demo', False), bool):
                    raise ValueError('body sai')
                self.game.switch_mode(body.get('mode'), body.get('demo', False))
            elif path == '/campaign' and isinstance(self.game, CampaignLiveGame):
                body = json.loads(raw.decode('utf-8') or '{}')
                if not isinstance(body, dict):
                    raise ValueError('body sai')
                self.game.action(body)
            else:
                self._send(404, b'{"error":"khong co"}')
                return
        except (ValueError, UnicodeDecodeError) as e:
            self._send(400, json.dumps({"error": str(e)}).encode("utf-8"))
            return
        self._send(200, b'{"ok":true}')


class LiveServer:
    """Máy chủ + mô phỏng. port=0 -> cổng ngẫu nhiên (đọc `.port`)."""

    def __init__(self, game: LiveGame, host="127.0.0.1", port=8000):
        handler = type("Handler", (_Handler,), {"game": game})
        self.game = game
        self.httpd = ThreadingHTTPServer((host, port), handler)
        self.httpd.daemon_threads = True
        self.host = host
        self.port = self.httpd.server_address[1]
        self._thread = None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/"

    def start(self):
        self.game.start()
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="chonoi-http", daemon=True)
        self._thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2)
        self.game.stop()


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="chonoi.live", description="Chơi trực tiếp trên trình duyệt (starter).")
    p.add_argument("--mode", default="campaign", choices=["gather", "quan", "campaign"])
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--port", type=int, default=8000, help="0 = cổng ngẫu nhiên")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--scenario")
    p.add_argument("--inventory", help="chỉ với quan: nạp kho từ file")
    p.add_argument("--inventory-out", dest="inventory_out", help="chỉ với gather: ghi kho khi kết thúc buổi")
    a = p.parse_args(argv)
    try:
        if a.inventory and a.mode != "quan":
            raise BadInput("--inventory chỉ dùng với quan")
        if a.inventory_out and a.mode != "gather":
            raise BadInput("--inventory-out chỉ dùng với gather")
        tuning = load_contract()["tuning"]
        scenario = load_scenario(a.scenario, a.mode, tuning) if a.mode != 'campaign' else {}
        inventory = read_inventory(a.inventory) if a.inventory else None
        if inventory is not None and "stock" in scenario:
            raise BadInput("vừa có quan.stock vừa có --inventory")
        game = (CampaignLiveGame(tuning, a.seed) if a.mode == 'campaign'
                else LiveGame(a.mode, tuning, scenario, a.seed, inventory, a.inventory_out))
        server = LiveServer(game, a.host, a.port)
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except OSError as e:
        sys.stderr.write(f"không mở được cổng {a.port}: {e}\n")
        return 1
    server.start()
    print(f"Mở trình duyệt tại {server.url}  (chế độ {a.mode}, seed {a.seed}). Ctrl+C để dừng.", flush=True)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
