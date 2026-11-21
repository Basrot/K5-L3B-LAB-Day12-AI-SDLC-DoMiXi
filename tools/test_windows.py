"""Run the unchanged contract tests with the active Windows Python interpreter.

Only replaces the python3 launcher in memory, never modifies game.contract.json.
"""
import sys
import unittest
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(root / 'tests'), str(root)]
import helpers

original_cmd = helpers.headless_cmd

def local_cmd():
    cmd = original_cmd()
    if sys.platform == 'win32' and cmd[0] == 'python3':
        return [sys.executable, *cmd[1:]]
    return cmd

helpers.headless_cmd = local_cmd
if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(root / 'tests'))
    sys.exit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
