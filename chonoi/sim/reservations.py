"""Live reservation scheduling; all randomness uses a dedicated stream."""
from ..ids import sort_by_id


def make_reservations(sim, dishes):
    cfg = sim.world['reservations']
    rng = sim.rng.get('live_reservations')
    source = getattr(sim, 'tables', sim.world['quan']['tables'])
    tables = rng.sample(sort_by_id(source), min(cfg['count'], len(source)))
    return [{'id': f'R{i+1}', 'table_id': table['id'], 'dish_id': rng.choice(sorted(dishes)),
             'arrival_tick': rng.randint(*cfg['arrival_ticks']), 'state': 'scheduled'}
            for i, table in enumerate(tables)]


class Reservations:
    def _fail_reservation(self, reservation, reason, events):
        if reservation['state'] in ('served', 'failed'):
            return
        reservation.update(state='failed', reason=reason)
        cid = reservation.get('customer_id')
        self.customers[:] = [c for c in self.customers if c['id'] != cid]
        for stove in self.stoves:
            if stove.get('customer_id') == cid:
                stove.update(state='idle', dish=None, customer_id=None, cook_ticks_left=0)
        if self.hand and self.hand.get('customer_id') == cid:
            self.hand = None
        self.reputation = max(self.t['reputation_min'], self.reputation + self.world['reservations']['failed_reputation_delta'])
        events.append(('reservation_failed', {'id': reservation['id'], 'reason': reason}))

    def _step_reservations(self, events):
        if self.time_left_ticks == 0:
            return
        cfg = self.world['reservations']
        for reservation in sort_by_id(self.reservations):
            if reservation['state'] in ('served', 'failed'):
                continue
            if reservation['state'] == 'scheduled' and self.elapsed >= max(0, reservation['arrival_tick']-round(cfg['table_hold_s']*60)):
                reservation['state'] = 'holding'
            if reservation['state'] == 'holding' and self.elapsed >= reservation['arrival_tick']:
                if any(c['table_id'] == reservation['table_id'] for c in self.customers):
                    self._fail_reservation(reservation, 'occupied', events)
                    continue
                customer = dict(id=self.ids.new('C'), label=reservation['id'], sprite=0, drink='',
                    table_id=reservation['table_id'], dish_id=reservation['dish_id'], state='waiting',
                    reserved={}, order_tick=self.elapsed, reservation_id=reservation['id'],
                    patience_ticks_left=round(cfg['patience_s']*60))
                self.customers.append(customer)
                self._reserve_fresh()
                if not customer.get('reserved_ids'):
                    reservation['customer_id'] = customer['id']
                    self._fail_reservation(reservation, 'stock', events)
                    continue
                reservation.update(state='waiting', customer_id=customer['id'])
                events.append(('reservation_arrived', {'id': reservation['id'], 'table_id': reservation['table_id']}))
                events.append(('customer_arrived', {'customer_id': customer['id'], 'dish_id': customer['dish_id']}))
            elif reservation['state'] == 'waiting':
                customer = next((c for c in self.customers if c['id'] == reservation.get('customer_id')), None)
                if customer and customer.get('order_status') == 'unfulfillable':
                    self._fail_reservation(reservation, 'stock', events)
