import unittest
from core.window_manager import WindowManager, get_window_icon_emoji

class TestWindowManager(unittest.TestCase):
    def test_window_icon_mapping(self):
        self.assertEqual(get_window_icon_emoji("Google Chrome"), "🌐")
        self.assertEqual(get_window_icon_emoji("Visual Studio Code"), "📝")
        self.assertEqual(get_window_icon_emoji("Slack"), "💬")
        self.assertEqual(get_window_icon_emoji("Windows PowerShell"), "🖥️")
        self.assertEqual(get_window_icon_emoji("Monkeytype Game"), "🎮")

    def test_get_open_windows(self):
        wins = WindowManager.get_open_windows()
        self.assertIsInstance(wins, list)
        self.assertGreater(len(wins), 0)
        for w in wins:
            self.assertIn("hwnd", w)
            self.assertIn("title", w)

if __name__ == "__main__":
    unittest.main()
