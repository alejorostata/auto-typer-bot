import unittest
import time
from core.typing_engine import AutoTyperEngine

class TestTypingEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AutoTyperEngine(min_wpm=100, max_wpm=120)

    def test_engine_initialization(self):
        self.assertEqual(self.engine.min_wpm, 100)
        self.assertEqual(self.engine.max_wpm, 120)
        self.assertTrue(self.engine.human_variation)
        self.assertTrue(self.engine.continuous_mode)

    def test_toggle_pause(self):
        # Initial state: not paused
        is_paused = self.engine.toggle_pause()
        self.assertTrue(is_paused)
        is_resumed = not self.engine.toggle_pause()
        self.assertTrue(is_resumed)

    def test_stop_engine(self):
        self.engine.stop()
        self.assertTrue(self.engine._stop_event.is_set())

if __name__ == "__main__":
    unittest.main()
