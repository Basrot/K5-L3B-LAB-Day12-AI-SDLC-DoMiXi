import unittest
from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.runner import Session
from chonoi.live import LiveGame


def inp(*edges):
    return InputState((0, 0), {}, set(edges))


class DivingTest(unittest.TestCase):
    def setUp(self):
        self.t = load_contract()['tuning']

    def test_oxygen_underwater_and_refill(self):
        s = Session('gather', self.t, {'player': {'pos': [20, 5], 'oxygen_ticks': 10}}, 1)
        s.step(inp())
        self.assertEqual(s.sim.oxygen_ticks, 9)
        s.sim.pos[1] = 0
        s.step(inp())
        self.assertEqual(s.sim.oxygen_ticks, 9 + self.t['gather']['oxygen_refill_per_tick'])

    def test_catch_underwater_and_cooldown(self):
        s = Session('gather', self.t, {'player': {'pos': [15, 5]}}, 1)
        rows = s.step(inp('catch'))
        self.assertIn('fish_caught', [e['name'] for e in rows])
        self.assertEqual(s.sim.hold, ['ca_linh'] * self.t['gather']['fish_yield']['ca_linh'])
        self.assertGreater(s.sim.catch_cd_ticks, 0)

    def test_faint_loses_hold(self):
        s = Session('gather', self.t, {'player': {'pos': [20, 5], 'oxygen_ticks': 0, 'hp': 1,
            'zero_oxy_ticks': self.t['gather']['choke_interval_ticks'] - 1}, 'hold': ['ca_loc']}, 1)
        s.step(inp())
        self.assertEqual(s.sim.reason, 'fainted')
        self.assertEqual(s.sim.hold, [])

    def test_live_pickup_once_and_restart(self):
        g = LiveGame('gather', self.t, {}, 1)
        sim = g.session.sim
        node = sim.collectibles[0]
        sim.pos = list(node['pos'])
        sim.step(inp('interact'))
        self.assertEqual(len(sim.collection), 1)
        sim.step(inp('interact'))
        self.assertEqual(len(sim.collection), 1)
        g.restart()
        self.assertEqual(g.session.sim.collection, [])

    def test_live_pickup_capacity_and_range(self):
        g = LiveGame('gather', self.t, {}, 1)
        sim = g.session.sim
        self.assertFalse(any(e[0] == 'treasure_picked' for e in sim.step(inp('interact'))))
        sim.pos = list(sim.collectibles[0]['pos'])
        sim.collection = ['shell'] * sim.extras['capacity']
        sim.step(inp('interact'))
        self.assertTrue(sim.collectibles[0]['ready'])

    def test_headless_has_no_live_collectibles(self):
        self.assertNotIn('collectibles', Session('gather', self.t, {}, 1).snapshot())
