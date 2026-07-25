import sys
import os
import time
import base64
import io
import threading
import ctypes
import platform
import tkinter as tk
from PIL import Image
import webview

import config
from core.typing_engine import AutoTyperEngine
from core.window_manager import WindowManager
from core.ocr_engine import ScreenOCR, get_dpi_scale_factor, HAS_WINOCR

IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    user32 = ctypes.windll.user32

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ('cbSize', ctypes.wintypes.DWORD),
            ('rcMonitor', ctypes.wintypes.RECT),
            ('rcWork', ctypes.wintypes.RECT),
            ('dwFlags', ctypes.wintypes.DWORD)
        ]

class Api:
    """
    Python-JS Bridge Object.
    NOTE: Do NOT store webview.Window or complex native COM objects as public attributes
    to prevent pywebview JS introspection infinite recursion errors.
    """
    def __init__(self):
        self._window_ref = None
        self.engine = AutoTyperEngine()
        self.ocr_engine = ScreenOCR()
        self.selected_hwnd = None
        self.selected_raw_title = ""

        # Setup Callbacks
        self.engine.on_progress_callback = self._on_typing_progress
        self.engine.on_complete_callback = self._on_typing_complete
        self.engine.on_error_callback = self._on_typing_error
        self.engine.on_text_updated_callback = self._on_text_updated

    def _set_window(self, win):
        self._window_ref = win

    def get_open_windows(self):
        return WindowManager.get_open_windows()

    def set_target_hwnd(self, hwnd, raw_title):
        self.selected_hwnd = hwnd
        self.selected_raw_title = raw_title
        self.ocr_engine.custom_region = None  # Reset region on new target

    def select_screen_area(self):
        """Launches multi-monitor virtual desktop overlay to capture region box across all screens (Cross-Platform: Windows, macOS, Linux)."""
        if not self.selected_hwnd:
            return

        WindowManager.focus_window(self.selected_hwnd)
        time.sleep(0.2)

        selection = None
        start_x = start_y = 0

        # Query Cross-Platform Multi-Monitor Virtual Desktop Bounding Box
        dummy = tk.Tk()
        dummy.withdraw()
        vx = dummy.winfo_vrootx()
        vy = dummy.winfo_vrooty()
        vw = dummy.winfo_vrootwidth()
        vh = dummy.winfo_vrootheight()
        dummy.destroy()

        overlay = tk.Tk()
        overlay.overrideredirect(True)
        overlay.attributes('-alpha', 0.25)
        overlay.attributes('-topmost', True)
        overlay.geometry(f"{vw}x{vh}+{vx}+{vy}")
        overlay.configure(cursor='cross', bg='gray')

        canvas = tk.Canvas(overlay, cursor='cross', bg='gray', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        rect_id = None

        def on_press(e):
            nonlocal start_x, start_y
            start_x, start_y = e.x, e.y

        def on_drag(e):
            nonlocal rect_id
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, e.x, e.y, outline='#ef4444', width=3)

        def on_release(e):
            nonlocal selection
            lx1 = min(start_x, e.x)
            ly1 = min(start_y, e.y)
            lx2 = max(start_x, e.x)
            ly2 = max(start_y, e.y)
            
            if (lx2 - lx1) > 20 and (ly2 - ly1) > 20:
                # Add virtual screen offsets (vx, vy) for multi-monitor accuracy
                dpi_scale = get_dpi_scale_factor()
                x1 = int((vx + lx1) * dpi_scale)
                y1 = int((vy + ly1) * dpi_scale)
                x2 = int((vx + lx2) * dpi_scale)
                y2 = int((vy + ly2) * dpi_scale)
                selection = (x1, y1, x2, y2)
            overlay.destroy()

        canvas.bind('<ButtonPress-1>', on_press)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)

        overlay.mainloop()

        if selection:
            self.ocr_engine.custom_region = selection
            threading.Thread(target=self._worker_analyze_screen, daemon=True).start()

    def _worker_analyze_screen(self):
        try:
            extracted = self.ocr_engine.extract_passage_from_window(self.selected_hwnd)
            base64_img = ""
            if self.ocr_engine.last_cropped_image:
                pil_img = self.ocr_engine.last_cropped_image.copy()
                pil_img.thumbnail((480, 120), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                base64_img = base64.b64encode(buf.getvalue()).decode('utf-8')

            word_cnt = len(extracted.split())
            reg_desc = "selected multi-monitor area" if self.ocr_engine.custom_region else "full window"
            engine_name = f"Windows Native Media OCR ({platform.system()})" if HAS_WINOCR else f"Cross-Platform RapidOCR ({platform.system()})"
            status_msg = f"✓ Read via {engine_name} from {reg_desc}! ({word_cnt} words ready)."

            # Escape strings for JS
            clean_extracted = extracted.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
            clean_status = status_msg.replace("'", "\\'")
            
            js = f"window.onTextExtracted(`{clean_extracted}`, '{base64_img}', '{clean_status}');"
            if self._window_ref:
                self._window_ref.evaluate_js(js)
        except Exception as e:
            print(f"Screen analysis error: {e}")

    def start_typing(self, text, min_wpm, max_wpm, human_jitter, auto_rescan):
        self.engine.min_wpm = min_wpm
        self.engine.max_wpm = max_wpm
        self.engine.human_variation = human_jitter
        self.engine.continuous_mode = auto_rescan

        self.engine.start_typing(
            text,
            target_hwnd=self.selected_hwnd,
            mode="pynput",
            ocr_engine=self.ocr_engine
        )

    def toggle_pause(self):
        return self.engine.toggle_pause()

    def stop_typing(self):
        self.engine.stop()

    def _on_typing_progress(self, words_typed, total_words, live_wpm, current_word):
        pct = float(words_typed / total_words) if total_words > 0 else 0.0
        clean_word = current_word.replace("'", "\\'").replace('"', '\\"')
        js = f"window.onTypingProgress({words_typed}, {total_words}, {pct}, {live_wpm}, '{clean_word}');"
        if self._window_ref:
            self._window_ref.evaluate_js(js)

    def _on_text_updated(self, updated_full_text):
        clean_text = updated_full_text.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
        js = f"window.onTextUpdated(`{clean_text}`);"
        if self._window_ref:
            self._window_ref.evaluate_js(js)

    def _on_typing_complete(self, total_typed):
        if self._window_ref:
            self._window_ref.evaluate_js("window.onTypingComplete();")

    def _on_typing_error(self, err_msg):
        clean_err = str(err_msg).replace("'", "\\'")
        if self._window_ref:
            self._window_ref.evaluate_js(f"window.onTypingError('{clean_err}');")

def launch_ui():
    api = Api()
    ui_dir = os.path.dirname(__file__)
    html_file = os.path.join(ui_dir, "index.html")

    win_title = f"Auto-Typer Bot ({platform.system()})"
    win_width = 900
    win_height = 680

    window = webview.create_window(
        win_title,
        url=html_file,
        js_api=api,
        width=win_width,
        height=win_height,
        min_size=(780, 520),
        resizable=True
    )
    api._set_window(window)

    def _exact_primary_center_worker():
        time.sleep(0.18)
        if IS_WINDOWS:
            try:
                hwnd = user32.FindWindowW(None, win_title)
                if hwnd:
                    # Get Primary Monitor Work Area (excluding taskbars)
                    hmon = user32.MonitorFromWindow(hwnd, 1) # MONITOR_DEFAULTTOPRIMARY
                    mi = MONITORINFO()
                    mi.cbSize = ctypes.sizeof(MONITORINFO)
                    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))

                    work_l = mi.rcWork.left
                    work_t = mi.rcWork.top
                    work_w = mi.rcWork.right - work_l
                    work_h = mi.rcWork.bottom - work_t

                    cx = work_l + max(0, int((work_w - win_width) / 2))
                    cy = work_t + max(0, int((work_h - win_height) / 2))
                    # SWP_NOZORDER (0x0004) | SWP_SHOWWINDOW (0x0040)
                    user32.SetWindowPos(hwnd, 0, cx, cy, win_width, win_height, 0x0044)
            except Exception as e:
                print("Primary Work Area center notice:", e)

    threading.Thread(target=_exact_primary_center_worker, daemon=True).start()
    webview.start(debug=False)
