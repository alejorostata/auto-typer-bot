import re
import sys
import platform
import asyncio
import ctypes
from ctypes import wintypes
import numpy as np
from PIL import Image, ImageGrab, ImageEnhance, ImageOps

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

HAS_WINOCR = False
if IS_WINDOWS:
    try:
        import winocr
        HAS_WINOCR = True
    except Exception:
        HAS_WINOCR = False

HAS_TESSERACT = False
try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    HAS_TESSERACT = False

if IS_WINDOWS:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def get_dpi_scale_factor():
    """Calculates physical vs logical screen DPI scaling factor (Cross-platform compatible)."""
    if IS_WINDOWS:
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hdc = user32.GetDC(0)
            logical_h = gdi32.GetDeviceCaps(hdc, 10)   # VERTRES
            physical_h = gdi32.GetDeviceCaps(hdc, 117) # DESKTOPVERTRES
            user32.ReleaseDC(0, hdc)
            if logical_h > 0:
                return physical_h / logical_h
        except Exception:
            pass
    return 1.0

class ScreenOCR:
    def __init__(self):
        self._rapid_ocr = None
        self.custom_region = None  # (x1, y1, x2, y2) in screen coordinates
        self.last_cropped_image = None # Stores last PIL image for GUI preview

    def _get_rapid_ocr(self):
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._rapid_ocr = RapidOCR()
            except Exception:
                self._rapid_ocr = False
        return self._rapid_ocr

    def is_ui_noise(self, text):
        clean = text.strip().lower()
        if not clean:
            return True
        
        # Discard standalone numbers (like timer badges '60', '15', '14', '12', '4', '5')
        if clean.isdigit() and len(clean) <= 3:
            return True

        # Keep valid single-character English words ('a', 'i')
        if len(clean) == 1 and clean not in ['a', 'i']:
            return True

        # Exact UI elements to ignore
        exact_ui_elements = [
            "google chrome", "microsoft edge", "mozilla firefox", "stop practice test",
            "stoppracticetest", "step 1 of 5", "step 2 of 5", "step 3 of 5",
            "step 4 of 5", "step 5 of 5", "show global scores", "words/min",
            "chars/min", "% accuracy", "typing test", "practice", "actual test", "results",
            "back", "skip"
        ]

        for ui_el in exact_ui_elements:
            if clean == ui_el:
                return True

        return False

    def extract_passage_from_window(self, hwnd, custom_region=None):
        """
        Cross-platform passage extractor (Windows, macOS, Linux).
        Focuses target window, captures precise user region selection box across all monitors,
        and uses multi-engine OCR fallback.
        """
        if not hwnd and not custom_region and not self.custom_region:
            return ""

        try:
            if IS_WINDOWS and hwnd:
                user32 = ctypes.windll.user32
                user32.ShowWindow(hwnd, 5) # SW_SHOW (retain exact window dimensions)
                import time
                time.sleep(0.3)
                user32.SetForegroundWindow(hwnd)
                time.sleep(0.2)

            region = custom_region or self.custom_region

            if region:
                x1, y1, x2, y2 = region
                rx1 = min(x1, x2)
                ry1 = min(y1, y2)
                rx2 = max(x1, x2)
                ry2 = max(y1, y2)

                pad = 8
                px1 = rx1 - pad
                py1 = ry1 - pad
                px2 = rx2 + pad
                py2 = ry2 + pad

                raw_crop = ImageGrab.grab(bbox=(px1, py1, px2, py2), all_screens=True)
            else:
                if IS_WINDOWS and hwnd:
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))

                    left = max(0, rect.left)
                    top = max(0, rect.top)
                    right = rect.right
                    bottom = rect.bottom

                    width = right - left
                    height = bottom - top

                    if width <= 100 or height <= 100:
                        return ""

                    full_img = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
                else:
                    full_img = ImageGrab.grab(all_screens=True)
                    width, height = full_img.size

                crop_top = int(height * 0.05)
                crop_bottom = int(height * 0.85)
                crop_left = int(width * 0.05)
                crop_right = int(width * 0.95)
                raw_crop = full_img.crop((crop_left, crop_top, crop_right, crop_bottom))

            # Store exact cropped image for GUI preview display
            self.last_cropped_image = raw_crop.copy()

            # 1. RapidOCR ONNX (PaddleOCR) - Primary Engine for Web Fonts & Custom Fonts
            rapid_engine = self._get_rapid_ocr()
            if rapid_engine:
                res = self._run_rapid_ocr(rapid_engine, raw_crop)
                if res and len(res.split()) >= 3:
                    print(f"✓ Text extracted via RapidOCR ONNX ({platform.system()})!")
                    return self._clean_final_text(res)

            # 2. Windows Native Media OCR
            if IS_WINDOWS and HAS_WINOCR:
                try:
                    win_text = asyncio.run(self._run_winocr(raw_crop))
                    if win_text and len(win_text.split()) >= 3:
                        print("✓ Text extracted via Windows Native Media OCR!")
                        return self._clean_final_text(win_text)
                except Exception as e:
                    print(f"Windows Native OCR notice: {e}")

            # 3. Cross-Platform Engine Fallback: PyTesseract
            if HAS_TESSERACT:
                try:
                    tess_text = pytesseract.image_to_string(raw_crop, config='--psm 6').strip()
                    if tess_text:
                        print(f"✓ Text extracted via Cross-Platform Tesseract ({platform.system()})!")
                        return self._clean_final_text(tess_text)
                except Exception:
                    pass

            return ""

        except Exception as e:
            print(f"Screen OCR extraction error: {e}")
            return ""

    async def _run_winocr(self, pil_img):
        res = await winocr.recognize_pil(pil_img, lang='en')
        if not res or not res.lines:
            return ""
        
        valid_lines = []
        for line in res.lines:
            txt = line.text.strip()
            clean_txt = re.sub(r'^\d+\s+', '', txt).strip()
            if clean_txt and not self.is_ui_noise(clean_txt):
                valid_lines.append(clean_txt)

        return " ".join(valid_lines)

    def _clean_final_text(self, raw_text):
        if not raw_text:
            return ""
        
        # Normalize Unicode dashes & smart quotes
        raw_text = raw_text.replace('–', '-').replace('—', '-').replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        raw_text = re.sub(r'^\d+\s+', '', raw_text).strip()
        
        words = raw_text.split()
        cleaned_words = []
        i = 0
        while i < len(words):
            w = words[i]
            
            # Strip trailing OCR artifacts (like etche( -> etched or etche)
            if len(w) > 3 and w.endswith('('):
                if w.lower() == "etche(":
                    w = "etched"
                else:
                    w = w[:-1]
            elif len(w) > 3 and w.endswith(')'):
                w = w[:-1]

            # Remove leading/trailing pipe symbols without corrupting letters
            w = re.sub(r'^[|\\]+', '', w)
            w = re.sub(r'[|\\]+$', '', w)

            # Discard UI noise numbers or stray non-word tokens
            if self.is_ui_noise(w):
                i += 1
                continue

            if len(w) == 1 and w.lower() not in ['a', 'i'] and (i + 1 < len(words)):
                i += 1
                continue
            if w:
                cleaned_words.append(w)
            i += 1

        final_str = " ".join(cleaned_words)
        final_str = re.sub(r'\s+', ' ', final_str).strip()
        return final_str

    def _run_rapid_ocr(self, engine, pil_img):
        try:
            img_array = np.array(pil_img.convert('RGB'))
            result, _ = engine(img_array)
            if not result:
                return ""

            boxes_with_text = []
            for box, txt, score in result:
                txt = txt.strip()
                clean_txt = re.sub(r'^[^\w"\']+', '', txt)
                clean_txt = re.sub(r'[^\w"\'.!?,;:]+$', '', clean_txt).strip()
                
                if not clean_txt or float(score) < 0.3:
                    continue

                if self.is_ui_noise(clean_txt):
                    continue

                avg_y = sum(pt[1] for pt in box) / 4.0
                min_x = min(pt[0] for pt in box)
                boxes_with_text.append({'x': min_x, 'y': avg_y, 'txt': clean_txt})

            if not boxes_with_text:
                return ""

            boxes_with_text.sort(key=lambda b: b['y'])

            lines = []
            current_line = []
            last_y = None

            for b in boxes_with_text:
                if last_y is None or abs(b['y'] - last_y) <= 25:
                    current_line.append(b)
                else:
                    current_line.sort(key=lambda item: item['x'])
                    lines.append(" ".join(item['txt'] for item in current_line))
                    current_line = [b]
                last_y = b['y']

            if current_line:
                current_line.sort(key=lambda item: item['x'])
                lines.append(" ".join(item['txt'] for item in current_line))

            full_text = " ".join(lines)
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            return full_text
        except Exception:
            return ""
