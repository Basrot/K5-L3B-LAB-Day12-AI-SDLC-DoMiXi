"""Live-only underwater souvenirs. Never used by the headless runner."""
import json
import math
from pathlib import Path
from .gather import GatherSim
from ..ids import sort_by_id
from ..live_world import load_world
from ..inventory import KINDS_P1, hold_to_items
from ..inputs import InputState
from .freshness import new_item, decay, snapshot_items


class LiveGatherSim(GatherSim):
    def _move(self, inp):
        super()._move(inp)
        limit = self.t.get('max_depth')
        if limit is not None and self.pos[1] > limit:
            self.pos[1] = float(limit)
            self.vel[1] = min(0.0, self.vel[1])

    def __init__(self, *args):
        super().__init__(*args)
        self.world = load_world()
        self.world_tick = 0
        self.weather = 'sun'
        self.weather_end = self.world['weather']['sun_ticks']
        self._weather_bag = []
        self.next_weather = self._draw_weather(self.weather)
        self.bubbles = []
        self.pursuer = {'active': False, 'pos': list(self.pos), 'label': self.world['pursuer']['label'],
                        'hug_ticks_left': 0, 'hug_pos': list(self.pos)}
        self.extras = json.loads((Path(__file__).parent.parent / 'live_gather.json').read_text(encoding='utf-8'))
        existing_fish_ids = {f['id'] for f in self.fish}
        for f in self.t.get('live_extra_fish', []):
            fid = f['id'] if f['id'] not in existing_fish_ids else self.ids.new('F')
            existing_fish_ids.add(fid)
            self.ids.reserve(fid)
            self.fish.append({'id': fid, 'kind': f['kind'], 'pos': [float(c) for c in f['pos']],
                              'heading_deg': f.get('heading_deg', 0)})
        self.collectibles = [dict(n, id=self.ids.new('L'), ready=True)
                             for n in self.extras['collectibles'] + self.world['collectibles']]
        self.collection = []
        self.pickup_ticks = 0
        self.poison_ticks = 0
        self.fresh_items = [new_item(self, kind) for kind in self.hold]
        self.hazards = []
        cfg = self.world['hazards']
        stream = self.rng.get('live_hazards')
        kinds = ['poison_fish'] * cfg['poison_count'] + ['jellyfish'] * cfg['jelly_count']
        stream.shuffle(kinds)
        columns = math.ceil(math.sqrt(len(kinds) * (cfg['spawn_x'][1] - cfg['spawn_x'][0]) /
                                      (cfg['spawn_depth'][1] - cfg['spawn_depth'][0])))
        rows = math.ceil(len(kinds) / columns)
        cells = [(col, row) for row in range(rows) for col in range(columns)]
        stream.shuffle(cells)
        for kind, (col, row) in zip(kinds, cells):
            # One hazard per cell; keep jitter small enough to preserve separation.
            x = cfg['spawn_x'][0] + (col + stream.uniform(.3, .7)) * (cfg['spawn_x'][1] - cfg['spawn_x'][0]) / columns
            depth = cfg['spawn_depth'][0] + (row + stream.uniform(.3, .7)) * (cfg['spawn_depth'][1] - cfg['spawn_depth'][0]) / rows
            pos = [x, depth]
            self.hazards.append({'id': self.ids.new('H'), 'kind': kind, 'pos': pos,
                                 'base_depth': depth})

    def step(self, inp):
        if self.done:
            return []
        self.poison_ticks = max(0, self.poison_ticks - 1)
        freshness_events = []
        decay(self, self.fresh_items, self.world['freshness']['gather_decay'], freshness_events)
        poison_target = None
        if not self._at_surface() and inp.pressed('catch') and self.catch_cd_ticks == 0:
            nearby = [h for h in sort_by_id(self.hazards) if h['kind'] == 'poison_fish'
                      and math.dist(self.pos, h['pos']) <= self.world['hazards']['catch_radius']]
            if nearby:
                target = min(nearby, key=lambda h: math.dist(self.pos, h['pos']))
                normal_distance = min((math.dist(self.pos, f['pos']) for f in self.fish), default=math.inf)
                if math.dist(self.pos, target['pos']) < normal_distance:
                    poison_target = target
                    inp = InputState(inp.move, inp.held, {name for name in ('interact',) if inp.pressed(name)})
        self.pickup_ticks = max(0, self.pickup_ticks - 1)
        cfg = self.world['weather']
        # Apply cold before base survival so oxygen-empty and choking keep their ordering.
        if not self._at_surface():
            extra = (cfg['snow_extra_oxygen'] if self.weather == 'snow' else 0)
            extra += self.world['hazards']['extra_oxygen'] if self.poison_ticks else 0
            self.oxygen_ticks = max(1, self.oxygen_ticks - extra) if self.oxygen_ticks else 0
        if self.weather == 'wind':
            inp = InputState(tuple(-axis for axis in inp.move), inp.held,
                             {name for name in ('interact', 'catch') if inp.pressed(name)})
        events = super().step(inp)
        # Keep original acquisition order; losses remove the most recently acquired items.
        counts = {}
        for kind in self.hold:
            counts[kind] = counts.get(kind, 0) + 1
        retained = []
        for item in self.fresh_items:
            if counts.get(item['kind'], 0):
                retained.append(item)
                counts[item['kind']] -= 1
        for kind, count in counts.items():
            retained.extend(new_item(self, kind) for _ in range(count))
        self.fresh_items = retained
        events = freshness_events + events
        if not self.done:
            if poison_target is not None:
                self.hazards.remove(poison_target)
                self._hazard_hit('poison_fish', events)
            for hazard in sort_by_id(self.hazards):
                if hazard['kind'] == 'jellyfish':
                    cfg = self.world['hazards']
                    hazard['pos'][1] = hazard['base_depth'] + cfg['jelly_amplitude'] * math.sin(self.world_tick * math.tau / cfg['jelly_period'])
                    if not self._at_surface() and math.dist(self.pos, hazard['pos']) <= cfg['radius']:
                        self._hazard_hit('jellyfish', events)
                        break
        if not self.done:
            self._weather_step(events)
        if self.done or self._at_surface() or not inp.pressed('interact'):
            return events
        targets = [n for n in sort_by_id(self.collectibles) if n['ready']
                   and math.dist(self.pos, n['pos']) <= self.extras['pickup_radius']]
        if targets:
            if len(self.collection) >= self.extras['capacity']:
                events.append(('collection_full', {}))
            else:
                n = min(targets, key=lambda n: math.dist(self.pos, n['pos']))
                n['ready'] = False
                self.collection.append(n['kind'])
                self.pickup_ticks = self.extras['animation_ticks']
                events.append(('treasure_picked', {'id': n['id'], 'kind': n['kind'], 'label': n['label']}))
        return events

    def _hazard_hit(self, cause, events):
        if self.done or self.invuln_ticks > 0:
            return
        cfg = self.world['hazards']
        self.hp = max(0, self.hp - cfg['damage'])
        self.invuln_ticks = cfg['grace_ticks']
        self.poison_ticks = cfg['poison_ticks']
        events.append(('hazard_hit', {'cause': cause, 'hp': self.hp, 'poison_ticks': self.poison_ticks}))
        if self.hp == 0:
            lost = list(reversed(self.hold))
            self.hold.clear()
            self.fresh_items.clear()
            events.append(('faint', {'cause': cause, 'lost': lost, 'hp': 0}))
            self._finish('fainted', events)

    def _draw_weather(self, current):
        stream = self.rng.get('live_weather')
        if not self._weather_bag:
            self._weather_bag = list(self.world['weather']['weights'])
            stream.shuffle(self._weather_bag)
        candidates = [kind for kind in self._weather_bag if kind != current]
        if current != 'rain' and stream.random() < .45:
            if 'rain' in self._weather_bag:
                self._weather_bag.remove('rain')
            return 'rain'
        if not candidates:
            self._weather_bag.clear()
            return self._draw_weather(current)
        selected = candidates[0]
        self._weather_bag.remove(selected)
        return selected

    def _weather_step(self, events):
        self.world_tick += 1
        w = self.world['weather']
        if self.world_tick >= self.weather_end:
            self.weather = self.next_weather
            stream = self.rng.get('live_weather')
            self.weather_end = self.world_tick + stream.randint(*w['duration_ticks'])
            self.next_weather = self._draw_weather(self.weather)
            self.bubbles.clear()
            events.append(('weather_changed', {'weather': self.weather}))
        weather = self.weather
        if weather == 'sun' and self._at_surface():
            self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + w['sun_extra_refill'])
        if weather == 'bubbles':
            if self.world_tick % w['bubble_interval'] == 0:
                stream = self.rng.get('live_bubbles')
                self.bubbles.append({'pos': [max(0, min(self.t['bounds']['x'][1], self.pos[0]+stream.uniform(-6,6))),
                                             min(self.t['bounds']['d'][1], self.pos[1]+8)]})
            remaining = []
            for bubble in self.bubbles:
                bubble['pos'][1] -= 1 / 30
                if not self._at_surface() and math.dist(self.pos, bubble['pos']) <= w['bubble_radius']:
                    self.oxygen_ticks = min(self.oxygen_max, self.oxygen_ticks + w['bubble_oxygen'])
                    events.append(('bubble_collected', {'oxygen_ticks': self.oxygen_ticks}))
                elif bubble['pos'][1] > 0:
                    remaining.append(bubble)
            self.bubbles = remaining
        if weather == 'fish_rain' and self.world_tick % w['fish_interval'] == 0 and len(self.fish) < w['fish_cap']:
            stream = self.rng.get('live_fish_rain')
            self.fish.append({'id': self.ids.new('F'), 'kind': stream.choice(list(self.world['gather']['fish_yield'])),
                'pos': [max(4, min(self.t['bounds']['x'][1]-4,self.pos[0]+stream.uniform(-8,8))), 3.0],
                'heading_deg': stream.choice([0,180])})
        cfg = self.world['pursuer']
        enemy = self.pursuer
        if enemy['hug_ticks_left'] > 0:
            if weather != 'rain' or self._at_surface():
                enemy['hug_ticks_left'] = 0
                enemy['active'] = False
                return
            enemy['hug_ticks_left'] -= 1
            enemy['hug_pos'] = list(self.pos)
            enemy['pos'] = list(self.pos)
            if enemy['hug_ticks_left'] == 0:
                away = -1 if self.pos[0] > self.t['bounds']['x'][1] / 2 else 1
                enemy['pos'] = [self.pos[0] + away * cfg['retreat_distance'], self.pos[1]]
            return
        if weather != 'rain' or self._at_surface():
            self.pursuer['active'] = False
            return
        if not enemy['active']:
            x = self.pos[0] + cfg['spawn_distance']
            if x > self.t['bounds']['x'][1]:
                x = self.pos[0] - cfg['spawn_distance']
            enemy['pos'] = [x, self.pos[1]]
            enemy['active'] = True
            events.append(('pursuer_appeared', {'label': cfg['label']}))
        dx, dy = self.pos[0] - enemy['pos'][0], self.pos[1] - enemy['pos'][1]
        distance = math.hypot(dx, dy)
        if distance:
            amount = min(distance, cfg['speed'] / 60)
            enemy['pos'][0] += dx / distance * amount
            enemy['pos'][1] += dy / distance * amount
        if distance <= cfg['hit_radius'] and self.invuln_ticks == 0:
            self.hp = max(0, self.hp - cfg['damage'])
            self.invuln_ticks = cfg['invuln_ticks']
            events.append(('pursuer_hit', {'hp': self.hp, 'damage': cfg['damage']}))
            enemy['hug_ticks_left'] = cfg['hug_ticks']
            enemy['hug_pos'] = list(self.pos)
            enemy['pos'] = list(self.pos)
            if self.hp == 0:
                lost = list(reversed(self.hold))
                self.hold.clear()
                self.fresh_items.clear()
                events.append(('faint', {'cause': 'pursuer', 'lost': lost, 'hp': 0}))
                self._finish('fainted', events)

    def inventory_items(self):
        # The v1.0 file format permits only its original ingredient kinds.
        return hold_to_items([kind for kind in self.hold if kind in KINDS_P1])

    def snapshot(self):
        snap = super().snapshot()
        snap['fresh_items'] = snapshot_items(self.fresh_items)
        snap.update(hazards=[{'id': h['id'], 'kind': h['kind'], 'pos': list(h['pos'])} for h in self.hazards],
                    poison_ticks=self.poison_ticks)
        snap.update(collectibles=self.collectibles, collection=list(self.collection),
                    collection_capacity=self.extras['capacity'], pickup_ticks=self.pickup_ticks,
                    pickup_radius=self.extras['pickup_radius'])
        w = self.world['weather']

        snap.update(weather=self.weather, world_tick=self.world_tick,
                    weather_ticks_left=max(0, self.weather_end-self.world_tick), next_weather=self.next_weather,
                    bubbles=[{'pos':list(b['pos'])} for b in self.bubbles],
                    pursuer=dict(self.pursuer, pos=list(self.pursuer['pos'])), catalog=self.world['catalog'])
        return snap
