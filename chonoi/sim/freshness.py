"""Per-item freshness for the live game, in exact 1/240 percent units."""
from ..ids import sort_by_id


def new_item(sim, kind):
    return {'id': sim.ids.new('I'), 'kind': kind,
            'fresh_units': sim.world['freshness']['maximum']}


def decay(sim, items, rate, events):
    threshold = sim.world['freshness']['spoiled_below']
    for item in sort_by_id(items):
        before = item['fresh_units']
        item['fresh_units'] = max(0, before - rate)
        if before >= threshold > item['fresh_units']:
            events.append(('spoiled', {'id': item['id'], 'kind': item['kind']}))


def snapshot_items(items):
    return [dict(item, fresh=item['fresh_units'] / 240) for item in items]
