import unittest
from chonoi.contract import load_contract
from chonoi.live import CampaignLiveGame


class CampaignFlowTest(unittest.TestCase):
    def test_intro_equipment_morning_evening_results_shop(self):
        game = CampaignLiveGame(load_contract()['tuning'], 3)
        game._save_progress = lambda: None
        game.action({'action':'start'})
        self.assertEqual(game.screen,'intro')
        game.action({'action':'intro_done'})
        self.assertEqual(game.screen,'equipment')
        game.action({'action':'equip','item':'oxygen','level':0})
        game.action({'action':'begin_morning'})
        self.assertEqual((game.screen,game.mode),('playing','gather'))
        game.action({'action':'evening'})
        self.assertEqual(game.mode,'quan')
        self.assertTrue(game.session.sim.snapshot()['menu_catalog'])
        game.action({'action':'close_evening'})
        game._tick_once()
        self.assertEqual(game.screen,'results')
        game.action({'action':'shop'})
        self.assertEqual(game.screen,'shop')
        game.action({'action':'prepare'})
        self.assertEqual(game.screen,'equipment')
        self.assertEqual(game.equipped['oxygen'],0)

    def test_cannot_equip_unowned_level(self):
        game = CampaignLiveGame(load_contract()['tuning'],3)
        game.screen='equipment'
        game.upgrades['oxygen']=0
        with self.assertRaises(ValueError):
            game.action({'action':'equip','item':'oxygen','level':1})

    def test_remove_lamp_and_slow_fish_reflection(self):
        game=CampaignLiveGame(load_contract()['tuning'],3)
        game.screen='equipment'
        game.action({'action':'equip','item':'lamp','level':-1})
        game.action({'action':'begin_morning'})
        sim=game.session.sim
        self.assertEqual(sim.t['reveal_radius'],0)
        sim.fish=[{'id':'F999','kind':'ca_loc','pos':[10.,5.],'heading_deg':0}]
        sim._swim_fish()
        self.assertAlmostEqual(sim.fish[0]['pos'][0],10+.65/60)
        edge=sim.t['bounds']['x'][1]
        sim.fish[0]['pos'][0]=edge
        sim._swim_fish()
        self.assertLess(sim.fish[0]['pos'][0],edge)
        self.assertAlmostEqual(sim.fish[0]['heading_deg'],180)

    def test_equipped_upgrades_apply_to_morning(self):
        game = CampaignLiveGame(load_contract()['tuning'],3)
        game.screen='equipment'
        for item in game.upgrades:
            game.upgrades[item]=2
            game.action({'action':'equip','item':item,'level':2})
        game.action({'action':'begin_morning'})
        sim=game.session.sim
        self.assertEqual(sim.oxygen_max,3600)
        self.assertEqual(sim.hp,5)
        self.assertEqual(sim.t['max_depth'],30)
        self.assertEqual(sim.t['reveal_radius'],7)
        base=game.progression['upgrades']['fins']['levels'][2]['swim_speed_multiplier']
        self.assertGreater(base,1)
        self.assertEqual(sim.t['swim_speed'],7*base)
