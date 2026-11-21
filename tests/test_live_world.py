import json
import unittest
from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.live import LiveGame
from chonoi.runner import Session

def inp(*edges):
    return InputState((0, 0), {}, set(edges))

class LiveWorldTest(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()['tuning']

    def test_expansion_is_live_only_and_does_not_mutate_contract(self):
        before = json.dumps(self.t, sort_keys=True)
        g = LiveGame('gather', self.t, {}, 3)
        self.assertGreater(g.session.sim.t['bounds']['x'][1], self.t['gather']['bounds']['x'][1])
        self.assertGreater(len(g.session.sim.fish), 6)
        self.assertEqual(json.dumps(self.t, sort_keys=True), before)
        self.assertEqual(Session('gather', self.t, {}, 3).sim.t, self.t['gather'])

    def test_rain_chase_contact_costs_one_hp_with_grace(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.world_tick = s.world['weather']['sun_ticks']
        s.pos = [30, 5]
        s.step(inp())
        self.assertEqual(s.weather, 'rain')
        self.assertTrue(s.pursuer['active'])
        s.pursuer['pos'] = list(s.pos)
        old_hp = s.hp
        s.step(inp())
        self.assertEqual(s.hp, old_hp - 1)
        s.pursuer['pos'] = list(s.pos)
        s.step(inp())
        self.assertEqual(s.hp, old_hp - 1)
        s.pos[1] = 0
        s.step(inp())
        self.assertFalse(s.pursuer['active'])

    def test_final_hit_ends_and_file_inventory_filters_extras(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.hold = ['ca_ro', 'ca_loc', 'tom_song']
        self.assertEqual(s.inventory_items(), {'ca_loc': 1})
        s.world_tick = s.world['weather']['sun_ticks']
        s.pos = [30, 5]
        s.step(inp())
        s.hp = 1
        s.pursuer['pos'] = list(s.pos)
        s.step(inp())
        self.assertEqual(s.reason, 'fainted')
        self.assertEqual(s.hold, [])

    def test_mode_switch_transfers_gather_stock(self):
        g = LiveGame('gather', self.t, {}, 3)
        g.session.sim.hold = ['ca_ro', 'ca_loc']
        g.switch_mode('quan')
        self.assertEqual(g.session.sim.stock, {'ca_ro': 1, 'ca_loc': 1})
        self.assertEqual(len(g.session.sim.tables), 4)
        self.assertTrue(all(t.get('label') for t in g.session.sim.tables))

    def test_restaurant_cook_serve_eat_and_pay(self):
        s = LiveGame('quan', self.t, {}, 3).session.sim
        for _ in range(s.t['first_customer_tick']):
            s.step(inp())
        c = s.customers[0]
        self.assertTrue(c['reserved'])
        s.pos = list(s.stoves[0]['pos'])
        s.step(inp('interact'))
        stove = s.stoves[0]
        self.assertEqual(stove['state'], 'cooking')
        for _ in range(stove['cook_ticks_left']):
            s.step(inp())
        s.step(inp('interact'))
        self.assertIsNotNone(s.hand)
        s.pos = list(next(t for t in s.tables if t['id'] == c['table_id'])['pos'])
        s.step(inp('interact'))
        self.assertEqual(c['state'], 'eating')
        for _ in range(c['eat_ticks_left']):
            s.step(inp())
        self.assertGreater(s.money, 0)
        self.assertNotIn(c, s.customers)

    def test_no_food_has_no_unfulfillable_orders(self):
        s = LiveGame('quan', self.t, {'stock': {}}, 3).session.sim
        for _ in range(s.t['first_customer_tick']):
            s.step(inp())
        self.assertEqual(s.customers, [])

    def test_demo_does_not_replace_real_restaurant(self):
        g = LiveGame('gather', self.t, {}, 1)
        g.session.sim.hold = ['ca_loc']
        g.switch_mode('quan')
        original = g.session
        g.session.sim.money = 123
        g.switch_mode('quan', demo=True)
        self.assertIsNot(g.session, original)
        g.switch_mode('quan')
        self.assertIs(g.session, original)
        self.assertEqual(g.session.sim.money, 123)
        self.assertEqual(g.session.sim.stock, {'ca_loc': 1})

    def test_finished_restaurant_opens_new_shift_with_stock(self):
        g = LiveGame('gather', self.t, {}, 1)
        g.session.sim.hold = ['ca_loc']
        g.switch_mode('quan')
        g.session.sim.done = True
        g.switch_mode('gather')
        g.session.sim.hold = ['ca_ro']
        g.switch_mode('quan')
        self.assertFalse(g.session.done)
        self.assertEqual(g.session.sim.stock, {'ca_loc': 1, 'ca_ro': 1})
