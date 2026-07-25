import unittest
import config

class TestConfig(unittest.TestCase):
    def test_default_config_values(self):
        self.assertIsNotNone(config.MIN_WPM)
        self.assertIsNotNone(config.MAX_WPM)
        self.assertTrue(config.MIN_WPM < config.MAX_WPM)
        self.assertIsInstance(config.HUMAN_VARIATION, bool)
        self.assertEqual(config.EMERGENCY_STOP_KEY, "esc")

if __name__ == "__main__":
    unittest.main()
