import json
import unittest
from pathlib import Path
from chonoi.contract import load_contract
from chonoi.inputs import InputState
from chonoi.live import LiveGame
from chonoi.runner import Session

def inp(*edges):
    return InputState((0, 0), {}, set(edges))

class LiveWorldTest(unittest.TestCase):
    def test_reservations_hold_arrive_serve_and_fail_once(self):
        q = LiveGame('quan', load_contract()['tuning'], {}, 3).session.sim
        dish = 'ca_loc_nuong_trui'
        q.reservations = [{'id':'R1','table_id':'T1','dish_id':dish,'arrival_tick':1,'state':'scheduled'}]
        q.elapsed = 1
        events = []
        q._step_reservations(events)
        self.assertEqual([name for name, _ in events], ['reservation_arrived','customer_arrived'])
        c = q.customers[0]
        q._interact(q.stoves[0],0,events)
        self.assertEqual(c['base_price'], int(q.menu[dish]['price']*1.5))
        q.stoves[0]['state'] = 'ready'
        q._interact(q.stoves[0],0,events)
        table = next(t for t in q.tables if t['id']=='T1')
        q._interact(table,1,events)
        self.assertEqual(q.reservations[0]['state'],'served')
        self.assertEqual(events[-1][0],'reservation_served')
        r = {'id':'R2','table_id':'T2','dish_id':dish,'arrival_tick':1,'state':'scheduled'}
        q.reservations.append(r)
        q.fresh_items=[]
        before=q.reputation
        q._step_reservations(events)
        q._step_reservations(events)
        self.assertEqual(r['reason'],'stock')
        self.assertEqual(q.reputation,max(q.t['reputation_min'],before-1))
        self.assertEqual(sum(name=='reservation_failed' for name,_ in events),1)

    def test_live_menu_uses_all_harvested_ingredients(self):
        game=LiveGame('gather',load_contract()['tuning'],{},3)
        tuning=game.tuning
        ingredients=set(tuning['gather']['fish_yield'])|{n['kind'] for n in tuning['gather']['nodes']}
        used={kind for dish in tuning['menu'].values() for kind in dish['recipe']}
        self.assertFalse(ingredients-used)

    def setUp(self):
        self.t = load_contract()['tuning']

    def test_expansion_is_live_only_and_does_not_mutate_contract(self):
        before = json.dumps(self.t, sort_keys=True)
        g = LiveGame('gather', self.t, {}, 3)
        self.assertGreater(g.session.sim.t['bounds']['x'][1], self.t['gather']['bounds']['x'][1])
        self.assertGreater(len(g.session.sim.fish), 6)
        self.assertEqual(json.dumps(self.t, sort_keys=True), before)
        self.assertEqual(Session('gather', self.t, {}, 3).sim.t, self.t['gather'])

    def test_weather_rotation_includes_every_kind_and_is_seeded(self):
        a = LiveGame('gather', self.t, {}, 3).session.sim
        b = LiveGame('gather', self.t, {}, 3).session.sim
        seen = []
        for _ in range(32):
            for sim in (a, b):
                sim.world_tick = sim.weather_end
                sim._weather_step([])
            self.assertEqual((a.weather, a.next_weather), (b.weather, b.next_weather))
            self.assertNotEqual(a.weather, a.next_weather)
            seen.append(a.weather)
        # Rain can now interrupt the shuffled rotation more frequently.
        self.assertEqual(set(seen), set(a.world['weather']['weights']))
        self.assertGreater(seen.count('rain'), seen.count('snow'))

    def test_freshness_decay_spoil_once_and_delivery(self):
        from chonoi.sim.freshness import new_item
        game = LiveGame('gather', self.t, {}, 3)
        s = game.session.sim
        s.hold = ['ca_loc']
        item = new_item(s, 'ca_loc')
        item['fresh_units'] = 7200
        s.fresh_items = [item]
        events = s.step(inp())
        self.assertEqual(item['fresh_units'], 7198)
        self.assertEqual(sum(name == 'spoiled' for name, _ in events), 1)
        self.assertFalse(any(name == 'spoiled' for name, _ in s.step(inp())))
        game.switch_mode('quan')
        q = game.session.sim
        self.assertEqual(q.fresh_items[0]['fresh_units'], 7196)
        self.assertEqual(q.stock['ca_loc'], 1)
        q.step(inp())
        self.assertEqual(q.fresh_items[0]['fresh_units'], 7195)
        self.assertEqual(q.customers, [])

    def test_fresh_reservation_replaces_spoiled_and_prices_used_items(self):
        from chonoi.sim.freshness import new_item
        q = LiveGame('quan', self.t, {}, 3).session.sim
        q.customers = []
        recipe = q.menu['ca_loc_nuong_trui']['recipe']
        q.fresh_items = []
        q.stock = {}
        for kind, count in recipe.items():
            for _ in range(count):
                item = new_item(q, kind)
                item['fresh_units'] = 12000
                q.fresh_items.append(item)
                q.stock[kind] = q.stock.get(kind, 0) + 1
        c = {'id':'C999','table_id':'T1','state':'waiting','dish_id':'ca_loc_nuong_trui',
             'reserved':dict(recipe),'order_tick':0,'patience_ticks_left':1000}
        q.customers.append(c)
        q._reserve_fresh()
        self.assertTrue(c['reserved_ids'])
        q._interact(q.stoves[0], 0, [])
        self.assertEqual(c['base_price'], q.menu[c['dish_id']]['price']//2)
        self.assertEqual(q.fresh_items, [])

    def test_wind_reverses_movement_and_preserves_catch(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.weather = 'wind'
        s.weather_end = 99999
        s.pos = [30, 5]
        for _ in range(12):
            s.step(InputState((-1, 0), {}, set()))
        self.assertGreater(s.pos[0], 30)
        s.fish = [{'id': 'F999', 'kind': 'ca_loc', 'pos': list(s.pos), 'heading_deg': 0}]
        events = s.step(inp('catch'))
        self.assertTrue(any(name == 'fish_caught' for name, _ in events))

    def test_hazards_stack_with_snow_and_can_cause_faint(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.pos = [30, 8]
        s.hazards = [{'id': 'H999', 'kind': 'jellyfish', 'pos': list(s.pos), 'base_depth': 8}]
        s.weather = 'snow'
        s.weather_end = 99999
        hp = s.hp
        s.step(inp())
        self.assertEqual(s.hp, hp - 1)
        self.assertGreater(s.poison_ticks, 0)
        oxygen = s.oxygen_ticks
        s.step(inp())
        self.assertEqual(s.oxygen_ticks, oxygen - 4)
        self.assertEqual(s.hp, hp - 1)
        s.hp = 1
        s.invuln_ticks = 0
        s.hold = ['ca_loc']
        s.step(inp())
        self.assertEqual(s.reason, 'fainted')
        self.assertEqual(s.hold, [])

    def test_catching_poison_fish_does_not_add_it_to_inventory(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.pos = [30, 8]
        s.fish = []
        s.hazards = [{'id': 'H999', 'kind': 'poison_fish', 'pos': list(s.pos), 'base_depth': 8}]
        events = s.step(inp('catch'))
        self.assertTrue(any(name == 'hazard_hit' for name, _ in events))
        self.assertEqual(s.hold, [])
        self.assertEqual(s.hazards, [])

    def test_live_gather_hud_has_flower_icons_stack_counts_and_oxygen_warning(self):
        html = (Path(__file__).resolve().parents[1] / 'chonoi' / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('function itemSprite', html)
        self.assertIn('SẮP HẾT OXY', html)
        self.assertIn('stack.count', html)
        self.assertIn('hug_ticks_left', html)

    def test_rain_chase_contact_costs_one_hp_with_grace(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.next_weather = 'rain'
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

    def test_pursuer_hit_starts_a_visible_hug_scene(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.next_weather = 'rain'
        s.world_tick = s.world['weather']['sun_ticks']
        s.pos = [30, 5]
        s.step(inp())
        s.pursuer['pos'] = list(s.pos)
        s.step(inp())
        self.assertGreater(s.pursuer['hug_ticks_left'], 0)
        self.assertEqual(s.pursuer['hug_pos'], [30, 5])
        self.assertGreater(s.snapshot()['pursuer']['hug_ticks_left'], 0)

    def test_final_hit_ends_and_file_inventory_filters_extras(self):
        s = LiveGame('gather', self.t, {}, 3).session.sim
        s.hold = ['ca_ro', 'ca_loc', 'tom_song']
        self.assertEqual(s.inventory_items(), {'ca_loc': 1})
        s.next_weather = 'rain'
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
        self.assertEqual(len(g.session.sim.tables), 3)  # 3 bàn gỗ khớp ảnh nền 15-quan-cho-noi.jpg (headless vẫn 4 bàn v1.1)
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

    def test_kha_banh_and_cong_an_interactions(self):
        g = LiveGame('quan', self.t, {}, 1)
        sim = g.session.sim
        self.assertIn('kha_banh', sim.snapshot())
        self.assertIn('cong_an', sim.snapshot())
        sim.money = 200
        sim.kha_banh['active'] = True
        sim.kha_banh['state'] = 'patrolling'
        sim.kha_banh['pos'] = [8.0, 5.0]
        sim.pos = [8.0, 5.0]
        events = sim.step(inp())
        self.assertTrue(any(e[0] == 'bao_ke_hit' for e in events))
        self.assertEqual(sim.money, 150)
        self.assertEqual(sim.kha_banh['state'], 'leaving')
        sim.kha_banh['active'] = True
        sim.kha_banh['state'] = 'patrolling'
        sim.cong_an['active'] = True
        sim.cong_an['state'] = 'patrolling'
        sim.cong_an['pos'] = [5.0, 5.0]
        sim.pos = [5.0, 5.0]
        ev_alert = sim.step(inp('interact'))
        self.assertTrue(any(e[0] == 'police_alerted' for e in ev_alert))
        self.assertEqual(sim.cong_an['state'], 'chasing')

    def test_jack_performance_and_tip_bonus(self):
        g = LiveGame('quan', self.t, {}, 1)
        sim = g.session.sim
        self.assertIn('jack', sim.snapshot())
        # Kích hoạt Jack bước vào sân khấu
        sim.jack['timer'] = 1
        ev_arr = sim.step(inp())
        self.assertTrue(any(e[0] == 'jack_arrived' for e in ev_arr))
        self.assertEqual(sim.jack['state'], 'entering')
        # Đến sân khấu -> bắt đầu hát Thiên Lý Ơi
        sim.jack['pos'] = list(sim.jack['target'])
        ev_sing = sim.step(inp())
        self.assertTrue(any(e[0] == 'jack_sing_start' for e in ev_sing))
        self.assertEqual(sim.jack['state'], 'singing')
        # Thử khách ăn xong trả tiền trong lúc Jack hát -> được cộng thêm tiền tip bonus
        dish_id = list(sim.menu.keys())[0]
        price = sim.menu[dish_id]['price']
        sim.customers.append({
            'id': 'C99', 'table_id': 'T1', 'state': 'eating',
            'dish_id': dish_id, 'eat_ticks_left': 1, 'tip': 10
        })
        init_money = sim.money
        ev_paid = sim.step(inp())
        paid_ev = next(e for e in ev_paid if e[0] == 'paid')
        expected_amount = price + 10 + sim.jack_cfg.get('tip_bonus', 20)
        self.assertEqual(paid_ev[1]['amount'], expected_amount)
        self.assertEqual(sim.money, init_money + expected_amount)
        # Giữa bài hát: khán giả tặng thêm tiền cho quán
        sim.jack['timer'] = int(round(sim.jack_cfg.get('sing_duration_s', 26) * 30))
        ev_fan = sim.step(inp())
        self.assertTrue(any(e[0] == 'jack_fan_donation' for e in ev_fan))
        # Hết bài hát -> Jack chào tạm biệt và rời đi
        sim.jack['timer'] = 0
        ev_leave = sim.step(inp())
        self.assertTrue(any(e[0] == 'jack_left' for e in ev_leave))
        self.assertEqual(sim.jack['state'], 'leaving')


