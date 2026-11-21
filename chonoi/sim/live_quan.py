"""Playable restaurant extension, deliberately isolated from contract QuanSim."""
import math
from .quan import QuanSim, TICK
from .ramp import ramp_velocity
from ..ids import sort_by_id, id_key
from ..live_world import load_world
from ..inventory import hold_to_items
from .freshness import new_item, decay, snapshot_items
from .reservations import Reservations, make_reservations


class LiveQuanSim(Reservations, QuanSim):
    _live_mode = True
    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        self.world = load_world()
        self.demo_stock = inventory is None and 'stock' not in scenario
        v12_items = None
        if self.demo_stock:
            live_stock = dict(self.world['demo_stock'])
        elif inventory is not None:
            if isinstance(inventory, list):
                v12_items = list(inventory)
                live_stock = hold_to_items(inventory)
            else:
                live_stock = {k: v for k, v in inventory.items() if v > 0}
        elif 'stock' in scenario:
            raw_s = scenario['stock']
            if isinstance(raw_s, list):
                v12_items = list(raw_s)
                live_stock = hold_to_items(raw_s)
            else:
                live_stock = {k: v for k, v in raw_s.items() if v > 0}
        else:
            live_stock = {}
        clean_scenario = {k: v for k, v in scenario.items() if k != 'stock'}
        super().__init__(tuning, clean_scenario, streams, ids, inventory=live_stock)
        self.stock = {k: v for k, v in live_stock.items() if v > 0}
        self.elapsed = 0
        self.seat_counter = 0
        if v12_items is not None:
            scale = self.world['freshness']['maximum'] / 100
            self.fresh_items = []
            for it in v12_items:
                entry = new_item(self, it['kind'])
                entry['id'] = it['id']
                self.ids.reserve(it['id'])
                entry['fresh_units'] = int(round(float(it['fresh']) * scale))
                self.fresh_items.append(entry)
        else:
            self.fresh_items = [new_item(self, kind) for kind, count in self.stock.items() for _ in range(count)]
        self.order_plan = None
        self.orders_spawned = {}
        self.extra_customer_limit = 0

        # Khá Bảnh configuration and state machine
        self.kb_cfg = self.world.get('kha_banh', {
            'label': 'Khá Bảnh', 'speed': 2.2, 'hit_radius': 1.4,
            'tax_amount': 50, 'invuln_ticks': 180,
            'quote': 'Bảnh xin nhẹ 50k bảo kê rồi lượn nhé!',
            'entrance_pos': [8.0, 0.5], 'spawn_cooldown_s': 15,
            'roam_duration_s': 20, 'patrol_bounds': {'x': [3.0, 14.0], 'z': [2.0, 8.5]}
        })
        self.kha_banh = {
            'active': False,
            'state': 'inactive',
            'pos': list(self.kb_cfg.get('entrance_pos', [8.0, 0.5])),
            'target': [8.0, 4.5],
            'facing_left': False,
            'timer': int(round(self.kb_cfg.get('spawn_cooldown_s', 15) * 60)),
            'action_ticks': 0
        }

        # Chú Công An configuration and state machine
        self.ca_cfg = self.world.get('cong_an', {
            'label': 'Chú Công An', 'speed': 2.0, 'chase_speed': 4.2,
            'interact_radius': 1.6, 'entrance_pos': [8.0, 0.5],
            'patrol_cooldown_s': 25, 'patrol_duration_s': 15,
            'reward_money': 50, 'reward_reputation': 0.5
        })
        self.cong_an = {
            'active': False,
            'state': 'inactive',
            'pos': list(self.ca_cfg.get('entrance_pos', [8.0, 0.5])),
            'target': [8.0, 5.0],
            'facing_left': False,
            'timer': int(round(self.ca_cfg.get('patrol_cooldown_s', 25) * 60)),
            'action_ticks': 0
        }

        # Ca Sĩ Jack (J97) configuration and state machine
        self.jack_cfg = self.world.get('jack', {
            'label': 'Ca Sĩ Jack (J97)', 'song_title': 'Thiên Lý Ơi', 'speed': 2.2,
            'entrance_pos': [8.0, 0.5], 'stage_pos': [5.6, 3.9],
            'first_spawn_s': 35, 'cooldown_s': 45, 'sing_duration_s': 26,
            'tip_bonus': 20, 'fan_donation': 40,
            'quote_arrive': 'Jack chào cả nhà quán Út Sen! Nay tặng quán bài Thiên Lý Ơi nha!',
            'quote_singing': 'Thiên lý ơi, em có nghe chăng lời ru chiều nay... 🎵',
            'quote_leave': 'Cảm ơn quý khán giả quán Út Sen rất nhiều! Hẹn gặp lại nhé!'
        })
        self.jack = {
            'active': False,
            'state': 'inactive',
            'pos': list(self.jack_cfg.get('entrance_pos', [8.0, 0.5])),
            'target': list(self.jack_cfg.get('stage_pos', [5.6, 3.9])),
            'facing_left': True,
            'timer': int(round(self.jack_cfg.get('first_spawn_s', 35) * 60)),
            'action_ticks': 0,
            'fan_donated': False
        }
        self.walk_area = dict(self.t.get('walk_area', {}))
        self.obstacles = [dict(ob) for ob in self.t.get('obstacles', [])]
        self.invuln_ticks = 0
        self.reservations = make_reservations(self, self.menu)
        for reservation in self.reservations:
            if reservation['arrival_tick'] <= round(self.world['reservations']['table_hold_s']*60):
                reservation['state'] = 'holding'

    def _reserve_fresh(self):
        threshold = self.world['freshness']['spoiled_below']
        used = set()
        for c in sorted(self.customers, key=lambda c: (c.get('order_tick', 0), id_key(c['table_id']))):
            if c['state'] != 'waiting':
                continue
            if c.get('order_status') == 'unfulfillable':
                continue
            old = c.get('reserved_ids', [])
            available = {i['id']: i for i in self.fresh_items if i['fresh_units'] >= threshold and i['id'] not in used}
            if old and all(ident in available for ident in old):
                used.update(old)
                continue
            selected = []
            for kind, count in self.menu[c['dish_id']]['recipe'].items():
                choices = sort_by_id([i for i in available.values() if i['kind'] == kind])
                choices.sort(key=lambda i: -i['fresh_units'])
                if len(choices) < count:
                    selected = []
                    break
                selected.extend(i['id'] for i in choices[:count])
            c['reserved_ids'] = selected
            c['reserved'] = dict(self.menu[c['dish_id']]['recipe']) if selected else {}
            c['order_status'] = 'reserved' if selected else 'unfulfillable'
            used.update(selected)

    def _order(self, events):
        occupied = {c['table_id'] for c in self.customers}
        held = {r['table_id'] for r in self.reservations if r['state'] in ('holding', 'waiting')}
        tables = [t for t in sort_by_id(self.tables) if t['id'] not in occupied and t['id'] not in held]
        if not tables:
            return
        available = {}
        for item in self.fresh_items:
            if item['fresh_units'] >= self.world['freshness']['spoiled_below']:
                available[item['kind']] = available.get(item['kind'], 0) + 1
        for c in self.customers:
            for k, amount in c.get('reserved', {}).items():
                available[k] = available.get(k, 0) - amount
        dishes = [k for k, dish in sorted(self.menu.items())
                  if all(available.get(i, 0) >= n for i, n in dish['recipe'].items())]
        planned = [k for k in dishes if self.order_plan is not None
                   and self.orders_spawned.get(k, 0) < self.order_plan.get(k, 0)]
        if self.order_plan is not None:
            if planned:
                dishes = planned
            elif sum(self.orders_spawned.values()) < sum(self.order_plan.values()) + self.extra_customer_limit:
                pass  # khách gọi thêm món còn làm được từ kho hiện có
            else:
                dishes = []
        if not dishes:
            events.append(('no_dish', {}))
            return
        dish = self.rng.get('live_orders').choice(dishes)
        self.orders_spawned[dish] = self.orders_spawned.get(dish, 0) + 1
        person = self.world['diners'][self.seat_counter % len(self.world['diners'])]
        self.seat_counter += 1
        c = dict(person, id=self.ids.new('C'), table_id=tables[0]['id'], state='waiting',
                 dish_id=dish, reserved=dict(self.menu[dish]['recipe']),
                 order_tick=self.elapsed, patience_ticks_left=round(self.t['patience_s'] * 60))
        self.customers.append(c)
        self._reserve_fresh()
        events.append(('customer_arrived', {'customer_id': c['id'], 'dish_id': dish}))

    def step(self, inp):
        if self.done:
            return []
        events = []
        self.elapsed += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        decay(self, self.fresh_items, self.world['freshness']['quan_decay'], events)
        self._reserve_fresh()
        self._step_reservations(events)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)

        # Xử lý hành vi Khá Bảnh & Chú Công An & Ca Sĩ Jack
        self._step_kha_banh(events)
        self._step_cong_an(events)
        self._step_jack(events)

        for st in self.stoves:
            if st['state'] == 'cooking':
                st['cook_ticks_left'] = max(0, st['cook_ticks_left'] - 1)
                if st['cook_ticks_left'] == 0:
                    st['state'] = 'ready'
                    st['ready_ticks'] = 0
                    events.append(('dish_ready', {'stove_id': st['id']}))
            elif st['state'] == 'ready' and self.t.get('burn_s') is not None:
                st['ready_ticks'] = st.get('ready_ticks', 0) + 1
                if st['ready_ticks'] >= round(self.t['burn_s']*60):
                    customer = next((c for c in self.customers if c['id'] == st.get('customer_id')), None)
                    events.append(('dish_burnt', {'stove_id':st['id'], 'order_status':'failed'}))
                    if customer and customer.get('reservation_id'):
                        reservation = next(r for r in self.reservations if r['id'] == customer['reservation_id'])
                        self._fail_reservation(reservation, 'burnt', events)
                    else:
                        st.update(state='idle', dish=None, customer_id=None, ready_ticks=0)
                        if customer:
                            customer['state'] = 'waiting'
                            customer['order_status'] = 'unfulfillable'
        for c in sort_by_id(list(self.customers)):
            if c['state'] == 'eating':
                c['eat_ticks_left'] -= 1
                if c['eat_ticks_left'] <= 0:
                    price = c.get('base_price', self.menu[c['dish_id']]['price'])
                    base_tip = c.get('tip', 0)
                    jack_bonus = self.jack_cfg.get('tip_bonus', 20) if (self.jack['active'] and self.jack['state'] == 'singing') else 0
                    amount = price + base_tip + jack_bonus
                    self.money += amount
                    self.earned += amount
                    self.shift_earned += amount
                    self.reputation = min(self.t['reputation_max'], self.reputation + (self.t['tip_reputation'] if base_tip else 0))
                    self.customers.remove(c)
                    ev_data = {'customer_id': c['id'], 'dish_id': c['dish_id'], 'amount': amount}
                    if jack_bonus:
                        ev_data['jack_bonus'] = jack_bonus
                    events.append(('paid', ev_data))
            else:
                # Khi Jack đang hát, khách say sưa nghe nhạc nên kiên nhẫn giảm chậm hơn 50%
                if not (self.jack['active'] and self.jack['state'] == 'singing' and self.elapsed % 2 == 0):
                    c['patience_ticks_left'] = max(0, c['patience_ticks_left'] - 1)
                if c['patience_ticks_left'] == 0:
                    if c.get('reservation_id'):
                        reservation = next(r for r in self.reservations if r['id'] == c['reservation_id'])
                        self._fail_reservation(reservation, 'patience', events)
                        continue
                    self.customers.remove(c)
                    self.reputation = max(self.t['reputation_min'], self.reputation + self.t['left_reputation_delta'])
                    for st in self.stoves:
                        if st.get('customer_id') == c['id']:
                            st.update(state='idle', dish=None, customer_id=None, cook_ticks_left=0)
                    if self.hand and self.hand['customer_id'] == c['id']:
                        self.hand = None
                    events.append(('customer_left', {'customer_id': c['id']}))

        self._move(inp)

        if inp.pressed('interact'):
            # Kiểm tra tương tác với Chú Công An trước
            if self._interact_police(events):
                pass
            else:
                targets = [(self._interact_dist(x), rank, x['id'], x)
                           for rank, group in enumerate((self.stoves, self.tables)) for x in group
                           if self._interact_dist(x) <= self.t['interact_radius']]
                if targets:
                    _, rank, _, target = min(targets, key=lambda v: v[:3])
                    self._interact(target, rank, events)

        interval = round(self.t['customer_interval_s'] * 60)
        if self.elapsed >= self.t['first_customer_tick'] and (self.elapsed - self.t['first_customer_tick']) % interval == 0:
            self._order(events)
        if self.time_left_ticks == 0:
            for reservation in self.reservations:
                self._fail_reservation(reservation, 'closing', events)
            self.done = True
            self.reason = 'time'
            events.append(('quan_end', {'money': self.money, 'earned': self.earned, 'reputation': self.reputation}))
        elif not self.customers and self.elapsed > self.t['first_customer_tick']:
            usable = {}
            for item in self.fresh_items:
                if item['fresh_units'] >= self.world['freshness']['spoiled_below']:
                    usable[item['kind']] = usable.get(item['kind'],0)+1
            if not any(all(usable.get(kind,0)>=count for kind,count in dish['recipe'].items()) for dish in self.menu.values()):
                # Close through the regular final-tick path, including reservation cleanup.
                self.time_left_ticks = 1
        return events

    def _interact_police(self, events) -> bool:
        ca = self.cong_an
        if not ca['active'] or ca['state'] not in ('patrolling', 'leaving'):
            return False
        dist = math.dist(self.pos, ca['pos'])
        if dist > self.ca_cfg.get('interact_radius', 1.6):
            return False

        kb = self.kha_banh
        if kb['active'] and kb['state'] in ('entering', 'patrolling', 'leaving'):
            # Có Khá Bảnh trong quán -> Báo công an đuổi bắt!
            ca['state'] = 'chasing'
            ca['action_ticks'] = 60
            events.append(('police_alerted', {
                'quote': 'Có đối tượng Khá Bảnh quấy rối! Đồng chí đứng yên để tôi xử lý!'
            }))
        else:
            # Không có Khá Bảnh -> Công an khen ngợi và thưởng uy tín
            self.reputation = min(self.t['reputation_max'], self.reputation + 0.1)
            ca['action_ticks'] = 60
            events.append(('police_friendly', {
                'quote': 'Quán chấp hành an ninh trật tự rất tốt! Tiếp tục phát huy nhé!'
            }))
        return True

    def _step_kha_banh(self, events):
        kb = self.kha_banh
        if kb['action_ticks'] > 0:
            kb['action_ticks'] -= 1

        ent = self.kb_cfg.get('entrance_pos', [8.0, 0.5])

        if kb['state'] == 'inactive':
            kb['timer'] -= 1
            if kb['timer'] <= 0:
                kb['active'] = True
                kb['state'] = 'entering'
                kb['pos'] = list(ent)
                kb['target'] = [8.0, 4.5]
                kb['timer'] = int(round(self.kb_cfg.get('roam_duration_s', 20) * 60))
                events.append(('kha_banh_arrived', {
                    'quote': 'Bảnh đã đến đây, quán xá thế nào rồi anh em!'
                }))
            return

        pos = kb['pos']
        target = kb['target']
        dx = target[0] - pos[0]
        dz = target[1] - pos[1]
        dist = math.hypot(dx, dz)

        if kb['state'] == 'entering':
            if dist < 0.3:
                kb['state'] = 'patrolling'
            else:
                self._move_actor(kb, dx, dz, dist, self.kb_cfg['speed'], allow_bridge=True)

        elif kb['state'] == 'patrolling':
            kb['timer'] -= 1
            if dist < 0.4:
                bounds = self.kb_cfg.get('patrol_bounds', {'x': [4.3, 11.2], 'z': [2.6, 6.1]})
                bx0, bx1 = bounds['x']
                bz0, bz1 = bounds['z']
                r = float(self.walk_area.get('actor_radius', 0.28))
                chosen = [8.5, 4.0]
                for attempt in range(12):
                    rx = bx0 + (((self.elapsed + attempt * 13) * 17 + 23) % 100) / 100.0 * (bx1 - bx0)
                    rz = bz0 + (((self.elapsed + attempt * 19) * 31 + 47) % 100) / 100.0 * (bz1 - bz0)
                    if not self._hits_obstacle(rx, rz, r + 0.05):
                        chosen = [round(rx, 2), round(rz, 2)]
                        break
                kb['target'] = chosen
            else:
                self._move_actor(kb, dx, dz, dist, self.kb_cfg['speed'], allow_bridge=False)

            # Va chạm với người chơi: thu tiền và rời quán luôn
            if math.dist(self.pos, pos) <= self.kb_cfg['hit_radius'] and self.invuln_ticks == 0:
                tax = min(self.money, self.kb_cfg['tax_amount'])
                self.money = max(0, self.money - tax)
                self.invuln_ticks = self.kb_cfg['invuln_ticks']
                kb['state'] = 'leaving'
                kb['target'] = list(ent)
                kb['action_ticks'] = 60
                events.append(('bao_ke_hit', {
                    'label': self.kb_cfg['label'],
                    'amount': tax,
                    'quote': 'Bảnh xin nhẹ 50k bảo kê rồi lượn nhé!'
                }))

            # Hết thời gian lượn lờ mà không thu được gì -> tự rời đi
            elif kb['timer'] <= 0:
                kb['state'] = 'leaving'
                kb['target'] = list(ent)
                events.append(('kha_banh_left', {
                    'quote': 'Quán này né kinh quá, Bảnh lượn đây!'
                }))

        elif kb['state'] == 'leaving':
            if pos[1] <= 0.8 or dist < 0.4:
                kb['active'] = False
                kb['state'] = 'inactive'
                kb['timer'] = int(round(self.kb_cfg.get('spawn_cooldown_s', 15) * 60))
            else:
                speed = self.kb_cfg['speed'] * 1.2
                self._move_actor(kb, dx, dz, dist, speed, allow_bridge=True)

        elif kb['state'] == 'arrested':
            # Bị công an lôi đi
            pass

    def _step_cong_an(self, events):
        ca = self.cong_an
        if ca['action_ticks'] > 0:
            ca['action_ticks'] -= 1

        ent = self.ca_cfg.get('entrance_pos', [8.0, 0.5])

        if ca['state'] == 'inactive':
            ca['timer'] -= 1
            if ca['timer'] <= 0:
                ca['active'] = True
                ca['state'] = 'patrolling'
                ca['pos'] = list(ent)
                ca['target'] = [8.0, 5.0]
                ca['timer'] = int(round(self.ca_cfg.get('patrol_duration_s', 15) * 60))
                events.append(('police_patrol_start', {
                    'quote': 'Công an khu vực đi tuần tra an ninh trật tự!'
                }))
            return

        pos = ca['pos']

        if ca['state'] == 'patrolling':
            ca['timer'] -= 1
            dx = ca['target'][0] - pos[0]
            dz = ca['target'][1] - pos[1]
            dist = math.hypot(dx, dz)
            if dist < 0.4:
                points = [[5.5, 3.6], [10.8, 3.6], [10.6, 5.8], [8.2, 5.6]]
                idx = (self.elapsed // 180) % len(points)
                ca['target'] = points[idx]
            else:
                # Cho phép bước từ cầu gỗ vào sàn trong lúc vừa vào quán
                self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'], allow_bridge=(pos[1] < 2.4))

            if ca['timer'] <= 0:
                ca['state'] = 'leaving'
                ca['target'] = list(ent)

        elif ca['state'] == 'chasing':
            # Đuổi theo Khá Bảnh với tốc độ nhanh
            kb = self.kha_banh
            ca['target'] = list(kb['pos'])
            dx = ca['target'][0] - pos[0]
            dz = ca['target'][1] - pos[1]
            dist = math.hypot(dx, dz)
            self._move_actor(ca, dx, dz, dist, self.ca_cfg['chase_speed'], allow_bridge=(pos[1] < 2.4 or kb['pos'][1] < 2.4))

            if dist <= 1.2:
                # Bắt giữ thành công!
                ca['state'] = 'escorting'
                ca['target'] = list(ent)
                kb['state'] = 'arrested'
                kb['target'] = list(ent)
                rew_m = self.ca_cfg.get('reward_money', 50)
                rew_r = self.ca_cfg.get('reward_reputation', 0.5)
                self.money += rew_m
                self.earned += rew_m
                self.reputation = min(self.t['reputation_max'], self.reputation + rew_r)
                events.append(('kha_banh_arrested', {
                    'quote': 'Khá Bảnh! Đứng lại! Về đồn làm việc ngay, không được thu bảo kê!'
                }))

        elif ca['state'] == 'escorting':
            # Dẫn giải Khá Bảnh ra cửa
            dx = ca['target'][0] - pos[0]
            dz = ca['target'][1] - pos[1]
            dist = math.hypot(dx, dz)
            self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'] * 1.3, allow_bridge=True)
            kb_x, kb_z = self._clamp_and_slide(
                pos[0], pos[1], pos[0] + (0.45 if not ca['facing_left'] else -0.45), pos[1],
                float(self.walk_area.get('actor_radius', 0.28)), allow_bridge=True
            )
            self.kha_banh['pos'] = [kb_x, kb_z]
            self.kha_banh['facing_left'] = ca['facing_left']

            if pos[1] <= 0.8 or dist < 0.4:
                ca['active'] = False
                ca['state'] = 'inactive'
                ca['timer'] = int(round(self.ca_cfg.get('patrol_cooldown_s', 25) * 60))
                self.kha_banh['active'] = False
                self.kha_banh['state'] = 'inactive'
                self.kha_banh['timer'] = 1800

        elif ca['state'] == 'leaving':
            dx = ca['target'][0] - pos[0]
            dz = ca['target'][1] - pos[1]
            dist = math.hypot(dx, dz)
            if pos[1] <= 0.8 or dist < 0.4:
                ca['active'] = False
                ca['state'] = 'inactive'
                ca['timer'] = int(round(self.ca_cfg.get('patrol_cooldown_s', 25) * 60))
            else:
                self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'], allow_bridge=True)

    def _step_jack(self, events):
        jk = self.jack
        if jk['action_ticks'] > 0:
            jk['action_ticks'] -= 1

        ent = self.jack_cfg.get('entrance_pos', [8.0, 0.5])
        stage = self.jack_cfg.get('stage_pos', [5.5, 5.2])

        if jk['state'] == 'inactive':
            jk['timer'] -= 1
            if jk['timer'] <= 0:
                jk['active'] = True
                jk['state'] = 'entering'
                jk['pos'] = list(ent)
                jk['target'] = list(stage)
                jk['fan_donated'] = False
                events.append(('jack_arrived', {
                    'label': self.jack_cfg.get('label', 'Ca Sĩ Jack (J97)'),
                    'quote': self.jack_cfg.get('quote_arrive', 'Jack chào cả nhà quán Út Sen! Nay tặng quán bài Thiên Lý Ơi nha!')
                }))
            return

        pos = jk['pos']
        target = jk['target']
        dx = target[0] - pos[0]
        dz = target[1] - pos[1]
        dist = math.hypot(dx, dz)

        if jk['state'] == 'entering':
            if dist < 0.3:
                jk['state'] = 'singing'
                jk['timer'] = int(round(self.jack_cfg.get('sing_duration_s', 26) * 60))
                events.append(('jack_sing_start', {
                    'song': self.jack_cfg.get('song_title', 'Thiên Lý Ơi'),
                    'quote': self.jack_cfg.get('quote_singing', 'Thiên lý ơi, em có nghe chăng lời ru chiều nay... 🎵')
                }))
            else:
                self._move_actor(jk, dx, dz, dist, self.jack_cfg['speed'], allow_bridge=True)

        elif jk['state'] == 'singing':
            jk['timer'] -= 1
            # Hiệu ứng nhịp biểu diễn đổi hướng nhẹ nhàng
            jk['facing_left'] = (self.elapsed // 120) % 2 == 0

            # Điểm giữa bài hát: khán giả cổ vũ tặng tiền trực tiếp cho quán
            half_dur = int(round(self.jack_cfg.get('sing_duration_s', 26) * 30))
            if jk['timer'] <= half_dur and not jk.get('fan_donated'):
                donation = self.jack_cfg.get('fan_donation', 40)
                self.money += donation
                self.earned += donation
                self.shift_earned += donation
                self.reputation = min(self.t['reputation_max'], self.reputation + 0.2)
                jk['fan_donated'] = True
                events.append(('jack_fan_donation', {
                    'amount': donation,
                    'quote': 'Khán giả say sưa nghe Thiên Lý Ơi tặng thêm 40k cho quán!'
                }))

            if jk['timer'] <= 0:
                jk['state'] = 'leaving'
                jk['target'] = list(ent)
                events.append(('jack_left', {
                    'quote': self.jack_cfg.get('quote_leave', 'Cảm ơn quý khán giả quán Út Sen rất nhiều! Hẹn gặp lại nhé!')
                }))

        elif jk['state'] == 'leaving':
            if pos[1] <= 0.8 or dist < 0.4:
                jk['active'] = False
                jk['state'] = 'inactive'
                jk['timer'] = int(round(self.jack_cfg.get('cooldown_s', 45) * 60))
            else:
                self._move_actor(jk, dx, dz, dist, self.jack_cfg['speed'], allow_bridge=True)

    def _interact_dist(self, entity) -> float:
        d = math.dist(self.pos, entity['pos'])
        ip = entity.get('interact_pos')
        if ip is not None:
            d = min(d, math.dist(self.pos, ip))
        return d

    def _walk_x_bounds(self, z: float, r: float, allow_bridge: bool = False):
        wa = self.walk_area
        if not wa:
            b = self.t['bounds']
            return b['x'][0] + r, b['x'][1] - r
        z_min = float(wa.get('z_min', 2.25))
        z_max = float(wa.get('z_max', 6.6))
        if allow_bridge and z < z_min:
            bx0, bx1 = wa.get('bridge_x', [6.7, 8.8])
            return float(bx0) + r, float(bx1) - r
        t = 0.0 if z_max <= z_min else max(0.0, min(1.0, (z - z_min) / (z_max - z_min)))
        x_lo = float(wa.get('x_min_bottom', 1.25)) + t * (float(wa.get('x_min_top', 1.65)) - float(wa.get('x_min_bottom', 1.25)))
        x_hi = float(wa.get('x_max_bottom', 14.55)) + t * (float(wa.get('x_max_top', 13.85)) - float(wa.get('x_max_bottom', 14.55)))
        return x_lo + r, x_hi - r

    def _hits_obstacle(self, x: float, z: float, r: float):
        for ob in self.obstacles:
            x0, x1 = ob['x']
            z0, z1 = ob['z']
            if (x0 - r) < x < (x1 + r) and (z0 - r) < z < (z1 + r):
                return ob
        return None

    def _clamp_fence(self, x: float, z: float, r: float, allow_bridge: bool = False):
        wa = self.walk_area
        if not wa:
            b = self.t['bounds']
            return max(b['x'][0], min(b['x'][1], x)), max(b['z'][0], min(b['z'][1], z))
        z_min = float(wa.get('z_min', 2.25))
        z_max = float(wa.get('z_max', 6.6))
        bx0, bx1 = wa.get('bridge_x', [6.7, 8.8])
        on_bridge_lane = allow_bridge and (float(bx0) <= x <= float(bx1))
        lo_z = float(wa.get('bridge_z_min', 0.45)) if on_bridge_lane else (z_min + r)
        hi_z = z_max - r
        z = max(lo_z, min(hi_z, z))
        x_lo, x_hi = self._walk_x_bounds(z, r, allow_bridge=allow_bridge)
        x = max(x_lo, min(x_hi, x))
        return x, z

    def _clamp_and_slide(self, old_x: float, old_z: float, new_x: float, new_z: float, r: float, allow_bridge: bool = False):
        # Nếu điểm bắt đầu đang lỡ nằm trong vật cản, đẩy ra theo cạnh gần nhất trước khi trượt
        start_ob = self._hits_obstacle(old_x, old_z, r)
        if start_ob is not None:
            x0, x1 = start_ob['x']
            z0, z1 = start_ob['z']
            pushes = [
                (abs(old_x - (x0 - r)), x0 - r, old_z),
                (abs((x1 + r) - old_x), x1 + r, old_z),
                (abs(old_z - (z0 - r)), old_x, z0 - r),
                (abs((z1 + r) - old_z), old_x, z1 + r),
            ]
            pushes.sort(key=lambda item: item[0])
            _, tx, tz = pushes[0]
            return self._clamp_fence(tx, tz, r, allow_bridge=allow_bridge)
        # 1. Trượt theo trục X trước
        tx, tz = self._clamp_fence(new_x, old_z, r, allow_bridge=allow_bridge)
        ob_x = self._hits_obstacle(tx, tz, r)
        if ob_x is not None:
            x0, x1 = ob_x['x']
            if new_x > old_x:
                tx = max(old_x, x0 - r) if old_x <= x0 - r else old_x
            elif new_x < old_x:
                tx = min(old_x, x1 + r) if old_x >= x1 + r else old_x
            else:
                tx = old_x
        # 2. Trượt theo trục Z tiếp theo
        tx, tz = self._clamp_fence(tx, new_z, r, allow_bridge=allow_bridge)
        ob_z = self._hits_obstacle(tx, tz, r)
        if ob_z is not None:
            z0, z1 = ob_z['z']
            if new_z > old_z:
                tz = max(old_z, z0 - r) if old_z <= z0 - r else old_z
            elif new_z < old_z:
                tz = min(old_z, z1 + r) if old_z >= z1 + r else old_z
            else:
                tz = old_z
        # 3. Bảo đảm nằm gọn trong rào và đẩy nhẹ ra ngoài nếu chạm góc vật cản
        tx, tz = self._clamp_fence(tx, tz, r, allow_bridge=allow_bridge)
        ob = self._hits_obstacle(tx, tz, r)
        if ob is not None:
            x0, x1 = ob['x']
            z0, z1 = ob['z']
            pushes = [
                (abs(tx - (x0 - r)), x0 - r, tz),
                (abs((x1 + r) - tx), x1 + r, tz),
                (abs(tz - (z0 - r)), tx, z0 - r),
                (abs((z1 + r) - tz), tx, z1 + r),
            ]
            pushes.sort(key=lambda item: item[0])
            _, tx, tz = pushes[0]
            tx, tz = self._clamp_fence(tx, tz, r, allow_bridge=allow_bridge)
        return tx, tz

    def _move(self, inp):
        if not self.walk_area and not self.obstacles:
            return super()._move(inp)
        speed = self.t['walk_speed']
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get('ramp_max_ticks', 6)))
        if abs(self.vel[0]) < 1e-9 and abs(self.vel[1]) < 1e-9:
            return
        old_x, old_z = self.pos[0], self.pos[1]
        r = float(self.walk_area.get('actor_radius', 0.28))
        nx, nz = self._clamp_and_slide(old_x, old_z, old_x + self.vel[0] / TICK, old_z + self.vel[1] / TICK, r, allow_bridge=False)
        if abs(nx - old_x) < 1e-6 and abs(self.vel[0]) > 0:
            self.vel[0] = 0.0
        if abs(nz - old_z) < 1e-6 and abs(self.vel[1]) > 0:
            self.vel[1] = 0.0
        self.pos[0], self.pos[1] = nx, nz

    def _move_actor(self, actor, dx, dz, dist, speed, allow_bridge=False):
        if dist <= 0.001:
            return
        step_len = min(dist, speed / 60.0)
        old_x, old_z = actor['pos'][0], actor['pos'][1]
        r = float(self.walk_area.get('actor_radius', 0.28))
        ux, uz = dx / dist, dz / dist
        nx, nz = self._clamp_and_slide(old_x, old_z, old_x + ux * step_len, old_z + uz * step_len, r, allow_bridge=allow_bridge)
        # Nếu vướng góc quầy bếp/bàn: tự trượt vòng sang hướng thoáng gần tâm sàn (8.4, 3.8)
        moved = math.hypot(nx - old_x, nz - old_z)
        if moved < step_len * 0.25 and (self.obstacles or self.walk_area):
            cand = [(-uz, ux), (uz, -ux)]
            best = (nx, nz)
            best_score = -1e9
            for sx, sz in cand:
                cx, cz = self._clamp_and_slide(old_x, old_z, old_x + sx * step_len, old_z + sz * step_len, r, allow_bridge=allow_bridge)
                cm = math.hypot(cx - old_x, cz - old_z)
                if cm > moved + 1e-4:
                    score = cm - 0.05 * math.hypot(cx - 8.4, cz - 3.8)
                    if score > best_score:
                        best_score = score
                        best = (cx, cz)
            nx, nz = best
        actor['pos'][0], actor['pos'][1] = nx, nz
        if abs(nx - old_x) > 1e-4:
            actor['facing_left'] = (nx - old_x) < 0
        else:
            actor['facing_left'] = dx < 0

    def _interact(self, target, rank, events):
        if rank == 0:
            if self.hand:
                return
            if target['state'] == 'ready':
                self.hand = {'dish_id': target['dish'], 'customer_id': target['customer_id']}
                target.update(state='idle', dish=None, customer_id=None)
                events.append(('dish_picked', dict(self.hand)))
            elif target['state'] == 'idle':
                waiting = sorted(
                    [c for c in self.customers if c['state'] == 'waiting' and c.get('reserved_ids')],
                    key=lambda c: (c.get('order_tick', 0), id_key(c['table_id'])),
                )
                if waiting:
                    c = waiting[0]
                    selected = [i for i in self.fresh_items if i['id'] in c['reserved_ids']]
                    c['base_price'] = self.menu[c['dish_id']]['price'] * sum(i['fresh_units'] for i in selected) // (len(selected) * self.world['freshness']['maximum'])
                    if c.get('reservation_id'):
                        c['base_price'] = math.floor(c['base_price'] * self.world['reservations']['price_multiplier'])
                    self.fresh_items = [i for i in self.fresh_items if i['id'] not in c['reserved_ids']]
                    c['reserved_ids'] = []
                    for kind, count in c['reserved'].items():
                        left = max(0, self.stock.get(kind, 0) - count)
                        if left > 0:
                            self.stock[kind] = left
                        else:
                            self.stock.pop(kind, None)
                    c['reserved'] = {}
                    c['state'] = 'assigned'
                    target.update(state='cooking', dish=c['dish_id'], customer_id=c['id'],
                                  cook_ticks_left=round(self.menu[c['dish_id']]['cook_s'] * 60))
                    events.append(('cook_started', {'stove_id': target['id'], 'dish_id': c['dish_id']}))
        elif self.hand:
            c = next((c for c in self.customers if c['table_id'] == target['id'] and c['id'] == self.hand['customer_id']), None)
            if c and c['state'] == 'assigned':
                ratio = c['patience_ticks_left'] / (self.t['patience_s'] * 60)
                c.update(state='eating', eat_ticks_left=round(self.t['eat_s'] * 60),
                         tip=math.floor(c.get('base_price', self.menu[c['dish_id']]['price']) * self.t['tip_rate']) if ratio >= self.t['tip_min_patience_ratio'] else 0)
                self.hand = None
                events.append(('served', {'customer_id': c['id']}))
                if c.get('reservation_id'):
                    reservation = next(r for r in self.reservations if r['id'] == c['reservation_id'])
                    reservation['state'] = 'served'
                    events.append(('reservation_served', {'id': reservation['id']}))

    def snapshot(self):
        snap = super().snapshot()
        snap['fresh_items'] = snapshot_items(self.fresh_items)
        snap['menu_catalog'] = {key: dict(dish) for key,dish in self.menu.items()}
        snap['reservations'] = [dict(r) for r in sort_by_id(self.reservations)]
        labels = {k: v.get('label', self.world['dish_labels'].get(k, k)) for k, v in self.menu.items()}
        for table, source in zip(snap['tables'], self.tables):
            table['label'] = source['label']
            table['painted'] = bool(source.get('painted', False))
            if 'interact_pos' in source:
                table['interact_pos'] = list(source['interact_pos'])
        for stove, source in zip(snap['stoves'], self.stoves):
            stove['painted'] = bool(source.get('painted', False))
            if 'interact_pos' in source:
                stove['interact_pos'] = list(source['interact_pos'])
        snap.update(
            menu_labels=labels, catalog=self.world['catalog'], demo_stock=self.demo_stock,
            elapsed=self.elapsed,
            kha_banh=dict(self.kha_banh),
            cong_an=dict(self.cong_an),
            jack=dict(self.jack),
            invuln_ticks=self.invuln_ticks
        )
        return snap
