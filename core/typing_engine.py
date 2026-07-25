import time
import random
import threading
import sys
import platform

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

try:
    from pynput.keyboard import Controller as PynputController, Key
    PYNPUT_AVAILABLE = True
except Exception:
    PYNPUT_AVAILABLE = False

class AutoTyperEngine:
    def __init__(self, min_wpm=80, max_wpm=120, human_variation=True, continuous_mode=True):
        self.min_wpm = min_wpm
        self.max_wpm = max_wpm
        self.human_variation = human_variation
        self.continuous_mode = continuous_mode

        self.keyboard = PynputController() if PYNPUT_AVAILABLE else None

        self._stop_event = threading.Event()
        self._pause_event = threading.Event()

        self.on_progress_callback = None
        self.on_complete_callback = None
        self.on_error_callback = None
        self.on_text_updated_callback = None

        self.word_queue = []
        self.typed_words_list = []
        self.initial_words_list = []
        self.lock = threading.Lock()
        self.start_time = None
        self.total_typed_words = 0
        self.target_hwnd = None

    def start_typing(self, text, target_hwnd=None, mode="pynput", ocr_engine=None):
        self.stop()
        self._stop_event.clear()
        self._pause_event.clear()

        words = text.strip().split()
        if not words:
            if self.on_error_callback:
                self.on_error_callback("No valid text found to type.")
            return

        with self.lock:
            self.word_queue = list(words)
            self.initial_words_list = list(words)
            self.typed_words_list = []
            self.total_typed_words = 0
            self.start_time = time.time()
            self.target_hwnd = target_hwnd

        threading.Thread(target=self._pynput_worker, args=(target_hwnd, ocr_engine), daemon=True).start()

    def toggle_pause(self):
        if self._pause_event.is_set():
            self._pause_event.clear()
            return False  # Resumed
        else:
            self._pause_event.set()
            return True   # Paused

    def stop(self):
        self._stop_event.set()
        self._pause_event.clear()

    def _pynput_worker(self, target_hwnd, ocr_engine):
        try:
            if target_hwnd:
                from core.window_manager import WindowManager
                WindowManager.focus_window(target_hwnd)
                time.sleep(0.3)

            while not self._stop_event.is_set():
                while self._pause_event.is_set():
                    time.sleep(0.1)
                    if self._stop_event.is_set():
                        return

                current_word = None
                with self.lock:
                    if self.word_queue:
                        current_word = self.word_queue.pop(0)

                if not current_word:
                    # Initial queue is empty! Now (and ONLY now) check if new text scrolled into view
                    if self.continuous_mode and ocr_engine and target_hwnd:
                        new_words = self._perform_queue_rescan(ocr_engine, target_hwnd)
                        if new_words:
                            continue
                    break # Queue is completely empty and no new text scrolled into view

                # Type word keystrokes with human micro-jitter via Pynput
                for char in current_word:
                    if self._stop_event.is_set():
                        return
                    while self._pause_event.is_set():
                        time.sleep(0.1)

                    target_wpm = random.uniform(self.min_wpm, self.max_wpm) if self.human_variation else (self.min_wpm + self.max_wpm) / 2
                    delay = 60.0 / (target_wpm * 5.0)

                    if self.human_variation:
                        delay *= random.uniform(0.7, 1.3)
                        if random.random() < 0.05:
                            delay += random.uniform(0.05, 0.15)

                    if self.keyboard:
                        self.keyboard.type(char)
                    time.sleep(max(0.005, delay))

                # Type space bar after word
                if self.keyboard:
                    self.keyboard.type(' ')
                
                space_delay = 60.0 / (random.uniform(self.min_wpm, self.max_wpm) * 5.0)
                time.sleep(max(0.01, space_delay))

                with self.lock:
                    self.total_typed_words += 1
                    self.typed_words_list.append(current_word)
                    words_typed = self.total_typed_words
                    total_words = words_typed + len(self.word_queue)

                elapsed = max(0.1, time.time() - self.start_time)
                live_wpm = int((words_typed / elapsed) * 60)

                if self.on_progress_callback:
                    self.on_progress_callback(words_typed, total_words, live_wpm, current_word)

            if self.on_complete_callback and not self._stop_event.is_set():
                self.on_complete_callback(self.total_typed_words)

        except Exception as e:
            if self.on_error_callback:
                self.on_error_callback(str(e))

    def _perform_queue_rescan(self, ocr_engine, target_hwnd):
        """
        Triggers ONLY after current passage queue reaches 0.
        Scans active screen area for newly scrolled lines/passages.
        """
        try:
            fresh_text = ocr_engine.extract_passage_from_window(target_hwnd)
            if not fresh_text:
                return False

            fresh_words = fresh_text.split()
            if not fresh_words:
                return False

            added_count = 0

            with self.lock:
                known_words_set = set(self.initial_words_list)
                new_scrolled_words = [w for w in fresh_words if w not in known_words_set]

                if new_scrolled_words:
                    clean_new_words = []
                    for w in new_scrolled_words:
                        clean_w = w.lstrip('l|I')
                        if clean_w:
                            clean_new_words.append(clean_w)

                    if clean_new_words:
                        self.word_queue.extend(clean_new_words)
                        self.initial_words_list.extend(clean_new_words)
                        added_count = len(clean_new_words)
                        
                        full_updated_passage = " ".join(self.initial_words_list)
                        if self.on_text_updated_callback:
                            self.on_text_updated_callback(full_updated_passage)

            return added_count > 0
        except Exception as e:
            print(f"Continuous OCR rescan notice: {e}")
            return False
