"""Data for live-only creative features; never loaded by headless."""
import json
from pathlib import Path
from copy import deepcopy

def load_world():
    return json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))

def live_tuning(tuning):
    world = load_world()
    result = deepcopy(tuning)
    result['gather'].update(world['gather'])
    result['gather']['fish_initial'] += world['fish']
    result['gather']['nodes'] += world['nodes']
    result['quan'].update(world['quan'])
    result['menu'].update(world['menu'])
    return result
