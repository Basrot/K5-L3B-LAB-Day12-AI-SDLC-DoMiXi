"""Data for live-only creative features; never loaded by headless."""
import json
from copy import deepcopy
from pathlib import Path


def load_world():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))


def live_tuning(tuning):
    world = load_world()
    result = deepcopy(tuning)
    result['gather'].update(world['gather'])
    # Giữ các loài cá của day_plan trong contract khi thêm cá sáng tạo ở Live.
    result['gather']['fish_yield'] = {**tuning['gather']['fish_yield'], **world['gather'].get('fish_yield', {})}
    if isinstance(result['gather'].get('fish_initial'), list):
        result['gather']['fish_initial'] += world['fish']
    else:
        result['gather']['live_extra_fish'] = list(world['fish'])
    existing_node_ids = {n['id'] for n in result['gather']['nodes']}
    next_n = max((int(nid[1:]) for nid in existing_node_ids if nid.startswith('N') and nid[1:].isdigit()), default=0) + 1
    for node in world['nodes']:
        n = dict(node)
        if n['id'] in existing_node_ids:
            n['id'] = f'N{next_n}'
            next_n += 1
        existing_node_ids.add(n['id'])
        result['gather']['nodes'].append(n)
    result['quan'].update(world['quan'])
    result['menu'].update(world['menu'])
    return result
