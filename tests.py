"""
tests.py — unit tests for doom-ascii.

Run with:  python tests.py
"""
import sys
import types
import unittest
import numpy as np

# Stub out vizdoom so agent.py / game.py can be imported without it installed
_vzd = types.ModuleType("vizdoom")

class _Button:
    MOVE_LEFT = MOVE_RIGHT = MOVE_FORWARD = MOVE_BACKWARD = None
    TURN_LEFT = TURN_RIGHT = ATTACK = USE = None

class _GameVariable:
    HEALTH = AMMO2 = KILLCOUNT = POSITION_X = POSITION_Y = ANGLE = None

class _ScreenResolution:
    RES_320X240 = None

class _ScreenFormat:
    RGB24 = GRAY8 = None

class _Mode:
    PLAYER = None

class _DoomGame:
    def set_doom_scenario_path(self, *a): pass
    def set_doom_game_path(self, *a): pass
    def set_doom_map(self, *a): pass
    def set_screen_resolution(self, *a): pass
    def set_screen_format(self, *a): pass
    def set_render_hud(self, *a): pass
    def set_render_crosshair(self, *a): pass
    def set_render_weapon(self, *a): pass
    def set_render_decals(self, *a): pass
    def set_render_particles(self, *a): pass
    def set_depth_buffer_enabled(self, *a): pass
    def set_labels_buffer_enabled(self, *a): pass
    def set_window_visible(self, *a): pass
    def set_mode(self, *a): pass
    def set_episode_timeout(self, *a): pass
    def set_episode_start_time(self, *a): pass
    def add_available_button(self, *a): pass
    def add_available_game_variable(self, *a): pass
    def set_living_reward(self, *a): pass
    def init(self): pass

_vzd.Button = _Button
_vzd.GameVariable = _GameVariable
_vzd.ScreenResolution = _ScreenResolution
_vzd.ScreenFormat = _ScreenFormat
_vzd.Mode = _Mode
_vzd.DoomGame = _DoomGame
_vzd.scenarios_path = "."
sys.modules["vizdoom"] = _vzd

# Now safe to import project modules
from game import read_stats, make_no_op, N_BUTTONS
from ascii_renderer import _compute_dims, AsciiRenderer
import agent as _agent


# ===========================================================================
# Helpers
# ===========================================================================

class FakeLabel:
    def __init__(self, name, x=0, y=0, width=10, height=10, object_id=1):
        self.object_name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.object_id = object_id


class FakeState:
    def __init__(self, labels=None, depth=None, screen=None, game_vars=None):
        self.labels = labels or []
        self.depth_buffer = depth
        self.screen_buffer = screen
        self.game_variables = game_vars or [100, 50, 0, 0.0, 0.0, 0.0]


# ===========================================================================
# game.py
# ===========================================================================

class TestReadStats(unittest.TestCase):

    def test_none_state(self):
        self.assertEqual(read_stats(None), (0, 0, 0))

    def test_normal_state(self):
        state = FakeState(game_vars=[75, 30, 5, 0, 0, 0])
        self.assertEqual(read_stats(state), (75, 30, 5))

    def test_short_game_vars(self):
        state = FakeState(game_vars=[50])
        h, a, k = read_stats(state)
        self.assertEqual(h, 50)
        self.assertEqual(a, 0)
        self.assertEqual(k, 0)


class TestMakeNoOp(unittest.TestCase):

    def test_length(self):
        action = make_no_op()
        self.assertEqual(len(action), N_BUTTONS)

    def test_all_false(self):
        self.assertTrue(all(v is False for v in make_no_op()))


# ===========================================================================
# ascii_renderer.py
# ===========================================================================

class TestComputeDims(unittest.TestCase):

    def test_wide_terminal(self):
        cols, rows = _compute_dims(200, 50)
        self.assertGreaterEqual(cols, 20)
        self.assertGreaterEqual(rows, 5)

    def test_narrow_terminal(self):
        cols, rows = _compute_dims(30, 10)
        self.assertGreaterEqual(cols, 20)
        self.assertGreaterEqual(rows, 5)

    def test_minimum_enforced(self):
        cols, rows = _compute_dims(1, 1)
        self.assertGreaterEqual(cols, 20)
        self.assertGreaterEqual(rows, 5)


class TestBuildHud(unittest.TestCase):

    def _hud(self, **kw):
        defaults = dict(health=100, ammo=50, kills=0, episode=1, width=200, damage_flash=False)
        defaults.update(kw)
        r = AsciiRenderer(width=200, height=50)
        return r._build_hud(**defaults)

    def test_contains_health(self):
        self.assertIn("HP:", self._hud(health=75))

    def test_contains_ammo(self):
        self.assertIn("AMMO:", self._hud(ammo=25))

    def test_contains_kills(self):
        self.assertIn("KILLS:", self._hud(kills=3))


class TestFrameToAscii(unittest.TestCase):

    def _renderer(self, cols=40, rows=10):
        r = AsciiRenderer(width=cols * 2, height=rows + 4)
        r._cols, r._rows = cols, rows
        return r

    def test_output_line_count(self):
        buf = np.zeros((240, 320), dtype=np.uint8)
        r = self._renderer(cols=40, rows=10)
        out = r._frame_to_ascii(buf)
        self.assertEqual(out.count("\n"), 9)

    def test_black_frame_uses_dark_chars(self):
        buf = np.zeros((240, 320), dtype=np.uint8)
        r = self._renderer(cols=20, rows=5)
        out = r._frame_to_ascii(buf)
        self.assertTrue(all(c == " " for c in out if c != "\n"))


# ===========================================================================
# agent.py — HumanAgent keyboard input
# ===========================================================================

class TestHumanAgent(unittest.TestCase):

    def test_init_graphics_mode(self):
        agent = _agent.HumanAgent("graphics")
        self.assertEqual(agent._mode, "graphics")
        self.assertIsNone(agent._kb)

    def test_init_ascii_mode(self):
        agent = _agent.HumanAgent("ascii")
        self.assertEqual(agent._mode, "ascii")
        self.assertIsNotNone(agent._kb)
        agent.stop()

    def test_reset(self):
        agent = _agent.HumanAgent("graphics")
        agent.quit_requested = True
        agent.restart_requested = True
        agent.reset()
        self.assertFalse(agent.quit_requested)
        self.assertFalse(agent.restart_requested)

    def test_make_no_op_returns_correct_length(self):
        action = make_no_op()
        self.assertEqual(len(action), 8)  # 8 buttons in HumanAgent


# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
