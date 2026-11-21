"""Live-only underwater souvenirs. Never used by the headless runner."""
import json
import math
from pathlib import Path
from .gather import GatherSim
from ..ids import sort_by_id
from ..live_world import load_world
from ..inventory import KINDS_P1, hold_to_items


class LiveGatherSim(GatherSim):
    def __init__(self, *args):
        super().__init__(*args)
        self.world = load_world()
        self.world_tick = 0
        self.weather = 'sun'
        self.pursuer = {'active': False, 'pos': list(self.pos), 'label': self.world['pursuer']['label']}
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

    def step(self, inp):
        self.pickup_ticks = max(0, self.pickup_ticks - 1)
        events = super().step(inp)
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

    def _weather_step(self, events):
        self.world_tick += 1
        w = self.world['weather']
        phase = self.world_tick % (w['sun_ticks'] + w['rain_ticks'])
        weather = 'sun' if phase < w['sun_ticks'] else 'rain'
        if weather != self.weather:
            events.append(('weather_changed', {'weather': weather}))
        self.weather = weather
        cfg = self.world['pursuer']
        if weather != 'rain' or self._at_surface():
            self.pursuer['active'] = False
            return
        enemy = self.pursuer
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
            # Back the pursuer away, leaving the player control and an escape window.
            away = -1 if self.pos[0] > self.t['bounds']['x'][1] / 2 else 1
            enemy['pos'][0] = self.pos[0] + away * cfg['retreat_distance']
            if self.hp == 0:
                self.hold.clear()
                events.append(('faint', {}))
                self._finish('fainted', events)

    def inventory_items(self):
        # The v1.0 file format permits only its original ingredient kinds.
        return hold_to_items([kind for kind in self.hold if kind in KINDS_P1])

    def snapshot(self):
        snap = super().snapshot()
        snap.update(collectibles=self.collectibles, collection=list(self.collection),
                    collection_capacity=self.extras['capacity'], pickup_ticks=self.pickup_ticks,
                    pickup_radius=self.extras['pickup_radius'])
        w = self.world['weather']
        phase = self.world_tick % (w['sun_ticks'] + w['rain_ticks'])
        snap.update(weather=self.weather, world_tick=self.world_tick,
                    weather_ticks_left=w['sun_ticks']-phase if self.weather == 'sun' else w['sun_ticks']+w['rain_ticks']-phase,
                    pursuer=dict(self.pursuer, pos=list(self.pursuer['pos'])), catalog=self.world['catalog'])
        return snap
