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
                    amount = price + c.get('tip', 0)
                    self.money += amount
                    self.earned += amount
                    self.shift_earned += amount
                    self.reputation = min(self.t['reputation_max'], self.reputation + (self.t['tip_reputation'] if c.get('tip', 0) else 0))
                    self.customers.remove(c)
                    events.append(('paid', {'customer_id': c['id'], 'amount': amount}))
            else:
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
            targets = [(math.dist(self.pos, x['pos']), rank, x['id'], x)
                       for rank, group in enumerate((self.stoves, self.tables)) for x in group
                       if math.dist(self.pos, x['pos']) <= self.t['interact_radius']]
            if targets:
                _, rank, _, target = min(targets, key=lambda v: v[:3])
                self._interact(target, rank, events)
        interval = round(self.t['customer_interval_s'] * 60)
        if self.elapsed >= self.t['first_customer_tick'] and (self.elapsed-self.t['first_customer_tick']) % interval == 0:
            self._order(events)
        if self.time_left_ticks == 0:
            self.done = True
            self.reason = 'time'
            events.append(('quan_end', {'money': self.money, 'earned': self.earned, 'reputation': self.reputation}))
        return events

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
        snap.update(menu_labels=labels, catalog=self.world['catalog'], demo_stock=self.demo_stock,
                    elapsed=self.elapsed)
        return snap
