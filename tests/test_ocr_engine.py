import unittest
from core.ocr_engine import ScreenOCR, get_dpi_scale_factor

class TestOCREngine(unittest.TestCase):
    def setUp(self):
        self.ocr = ScreenOCR()

    def test_dpi_scale_factor(self):
        dpi = get_dpi_scale_factor()
        self.assertIsInstance(dpi, float)
        self.assertGreater(dpi, 0.0)

    def test_ui_noise_detection(self):
        self.assertTrue(self.ocr.is_ui_noise(""))
        self.assertTrue(self.ocr.is_ui_noise("   "))
        self.assertTrue(self.ocr.is_ui_noise("60"))
        self.assertTrue(self.ocr.is_ui_noise("words/min"))
        self.assertFalse(self.ocr.is_ui_noise("The quick brown fox jumps over the lazy dog."))

    def test_clean_final_text(self):
        raw = "123  The quick   brown fox  jumps over the lazy dog.  "
        cleaned = self.ocr._clean_final_text(raw)
        self.assertEqual(cleaned, "The quick brown fox jumps over the lazy dog.")

if __name__ == "__main__":
    unittest.main()
