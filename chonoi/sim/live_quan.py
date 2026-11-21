"""Playable restaurant extension, deliberately isolated from contract QuanSim."""
import math
from .quan import QuanSim
from ..ids import sort_by_id
from ..live_world import load_world


class LiveQuanSim(QuanSim):
    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        self.world = load_world()
        self.demo_stock = inventory is None and 'stock' not in scenario
        if self.demo_stock:
            inventory = self.world['demo_stock']
        super().__init__(tuning, scenario, streams, ids, inventory)
        self.elapsed = 0
        self.seat_counter = 0

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
            'entrance_pos': [8.0, 0.5], 'stage_pos': [5.5, 5.2],
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
            'target': list(self.jack_cfg.get('stage_pos', [5.5, 5.2])),
            'facing_left': True,
            'timer': int(round(self.jack_cfg.get('first_spawn_s', 35) * 60)),
            'action_ticks': 0,
            'fan_donated': False
        }
        self.invuln_ticks = 0

    def _order(self, events):
        occupied = {c['table_id'] for c in self.customers}
        tables = [t for t in sort_by_id(self.tables) if t['id'] not in occupied]
        if not tables:
            return
        available = dict(self.stock)
        for c in self.customers:
            for k, amount in c.get('reserved', {}).items():
                available[k] = available.get(k, 0) - amount
        dishes = [k for k, dish in sorted(self.menu.items())
                  if all(available.get(i, 0) >= n for i, n in dish['recipe'].items())]
        if not dishes:
            events.append(('no_dish', {}))
            return
        dish = self.rng.get('live_orders').choice(dishes)
        person = self.world['diners'][self.seat_counter % len(self.world['diners'])]
        self.seat_counter += 1
        c = dict(person, id=self.ids.new('C'), table_id=tables[0]['id'], state='waiting',
                 dish_id=dish, reserved=dict(self.menu[dish]['recipe']),
                 patience_ticks_left=round(self.t['patience_s'] * 60))
        self.customers.append(c)
        events.append(('customer_arrived', {'customer_id': c['id'], 'dish_id': dish}))

    def step(self, inp):
        events = []
        self.elapsed += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
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
                    events.append(('dish_ready', {'stove_id': st['id']}))
        for c in sort_by_id(list(self.customers)):
            if c['state'] == 'eating':
                c['eat_ticks_left'] -= 1
                if c['eat_ticks_left'] <= 0:
                    price = self.menu[c['dish_id']]['price']
                    base_tip = c.get('tip', 0)
                    jack_bonus = self.jack_cfg.get('tip_bonus', 20) if (self.jack['active'] and self.jack['state'] == 'singing') else 0
                    amount = price + base_tip + jack_bonus
                    self.money += amount
                    self.earned += amount
                    self.shift_earned += amount
                    self.reputation = min(self.t['reputation_max'], self.reputation + (self.t['tip_reputation'] if base_tip else 0))
                    self.customers.remove(c)
                    ev_data = {'customer_id': c['id'], 'amount': amount}
                    if jack_bonus:
                        ev_data['jack_bonus'] = jack_bonus
                    events.append(('paid', ev_data))
            else:
                # Khi Jack đang hát, khách say sưa nghe nhạc nên kiên nhẫn giảm chậm hơn 50%
                if not (self.jack['active'] and self.jack['state'] == 'singing' and self.elapsed % 2 == 0):
                    c['patience_ticks_left'] = max(0, c['patience_ticks_left'] - 1)
                if c['patience_ticks_left'] == 0:
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
                targets = [(math.dist(self.pos, x['pos']), rank, x['id'], x)
                           for rank, group in enumerate((self.stoves, self.tables)) for x in group
                           if math.dist(self.pos, x['pos']) <= self.t['interact_radius']]
                if targets:
                    _, rank, _, target = min(targets, key=lambda v: v[:3])
                    self._interact(target, rank, events)

        interval = round(self.t['customer_interval_s'] * 60)
        if self.elapsed >= self.t['first_customer_tick'] and (self.elapsed - self.t['first_customer_tick']) % interval == 0:
            self._order(events)
        if self.time_left_ticks == 0:
            self.done = True
            self.reason = 'time'
            events.append(('quan_end', {'money': self.money, 'earned': self.earned, 'reputation': self.reputation}))
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
                self._move_actor(kb, dx, dz, dist, self.kb_cfg['speed'])

        elif kb['state'] == 'patrolling':
            kb['timer'] -= 1
            if dist < 0.4:
                bounds = self.kb_cfg.get('patrol_bounds', {'x': [3.0, 14.0], 'z': [2.0, 8.5]})
                rand_x = bounds['x'][0] + ((self.elapsed * 17 + 23) % 100) / 100.0 * (bounds['x'][1] - bounds['x'][0])
                rand_z = bounds['z'][0] + ((self.elapsed * 31 + 47) % 100) / 100.0 * (bounds['z'][1] - bounds['z'][0])
                kb['target'] = [round(rand_x, 2), round(rand_z, 2)]
            else:
                self._move_actor(kb, dx, dz, dist, self.kb_cfg['speed'])

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
                self._move_actor(kb, dx, dz, dist, speed)

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
                points = [[4.0, 5.0], [12.0, 5.0], [8.0, 3.5], [8.0, 6.0]]
                idx = (self.elapsed // 180) % len(points)
                ca['target'] = points[idx]
            else:
                self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'])

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
            self._move_actor(ca, dx, dz, dist, self.ca_cfg['chase_speed'])

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
            self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'] * 1.3)
            self.kha_banh['pos'] = [pos[0] + (0.5 if not ca['facing_left'] else -0.5), pos[1]]
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
                self._move_actor(ca, dx, dz, dist, self.ca_cfg['speed'])

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
                self._move_actor(jk, dx, dz, dist, self.jack_cfg['speed'])

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
                self._move_actor(jk, dx, dz, dist, self.jack_cfg['speed'])

    @staticmethod
    def _move_actor(actor, dx, dz, dist, speed):
        if dist > 0.001:
            step_len = min(dist, speed / 60.0)
            actor['pos'][0] += (dx / dist) * step_len
            actor['pos'][1] += (dz / dist) * step_len
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
                waiting = [c for c in sort_by_id(self.customers) if c['state'] == 'waiting']
                if waiting:
                    c = waiting[0]
                    for kind, count in c['reserved'].items():
                        self.stock[kind] -= count
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
                         tip=round(self.menu[c['dish_id']]['price'] * self.t['tip_rate']) if ratio >= self.t['tip_min_patience_ratio'] else 0)
                self.hand = None
                events.append(('served', {'customer_id': c['id']}))

    def snapshot(self):
        snap = super().snapshot()
        labels = {k: v.get('label', self.world['dish_labels'].get(k, k)) for k, v in self.menu.items()}
        for table, source in zip(snap['tables'], self.tables):
            table['label'] = source['label']
            table['painted'] = bool(source.get('painted', False))
        for stove, source in zip(snap['stoves'], self.stoves):
            stove['painted'] = bool(source.get('painted', False))
        snap.update(
            menu_labels=labels, catalog=self.world['catalog'], demo_stock=self.demo_stock,
            elapsed=self.elapsed,
            kha_banh=dict(self.kha_banh),
            cong_an=dict(self.cong_an),
            jack=dict(self.jack),
            invuln_ticks=self.invuln_ticks
        )
        return snap
