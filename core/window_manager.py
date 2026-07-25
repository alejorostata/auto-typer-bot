import sys
import platform
import time
from PIL import ImageGrab

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32

def get_window_icon_emoji(title):
    """Categorizes open window by title and assigns a distinct, recognizable app icon."""
    t = title.lower()
    if any(b in t for b in ["chrome", "edge", "firefox", "brave", "opera", "safari", "browser"]):
        return "🌐"
    elif any(e in t for e in ["notepad", "code", "sublime", "word", "textedit", "writer", "document"]):
        return "📝"
    elif any(c in t for c in ["slack", "discord", "teams", "telegram", "whatsapp", "livechat", "chat"]):
        return "💬"
    elif any(p in t for p in ["cmd", "powershell", "terminal", "bash", "zsh"]):
        return "🖥️"
    elif any(g in t for g in ["game", "steam", "monkeytype"]):
        return "🎮"
    else:
        return "💻"

class WindowManager:
    @staticmethod
    def get_open_windows():
        """
        Enumerates all visible user application windows with smart app type icons (Cross-platform).
        """
        windows = []

        if IS_WINDOWS:
            ignored_titles = {
                "Program Manager", "Settings", "Task Switching", 
                "Windows Input Experience", "System Resource Monitor", 
                "PopupHost", "Default IME", "MSCTFIME UI", "Auto-Typer Bot", ""
            }

            def enum_windows_callback(hwnd, extra):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()
                        
                        if title and title not in ignored_titles and not title.startswith("PopupHost") and not "Auto-Typer Bot" in title:
                            rect = wintypes.RECT()
                            user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            width = rect.right - rect.left
                            height = rect.bottom - rect.top
                            
                            if width > 100 and height > 100:
                                icon = get_window_icon_emoji(title)
                                windows.append({
                                    "hwnd": hwnd,
                                    "title": f"{icon}  {title}",
                                    "raw_title": title,
                                    "width": width,
                                    "height": height
                                })
                return True

            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
            return windows

        elif IS_MAC:
            try:
                import subprocess
                cmd = "osascript -e 'tell application \"System Events\" to get title of every process whose visible is true'"
                output = subprocess.check_output(cmd, shell=True).decode('utf-8')
                titles = [t.strip() for t in output.split(',') if t.strip()]
                for idx, t in enumerate(titles):
                    if "Auto-Typer" not in t:
                        icon = get_window_icon_emoji(t)
                        windows.append({
                            "hwnd": idx + 1,
                            "title": f"{icon}  {t}",
                            "raw_title": t,
                            "width": 1280,
                            "height": 800
                        })
                return windows
            except Exception:
                pass

        elif IS_LINUX:
            try:
                import subprocess
                cmd = "wmctrl -l"
                output = subprocess.check_output(cmd, shell=True).decode('utf-8')
                for line in output.strip().split('\n'):
                    parts = line.split(None, 3)
                    if len(parts) >= 4 and "Auto-Typer" not in parts[3]:
                        title = parts[3]
                        icon = get_window_icon_emoji(title)
                        windows.append({
                            "hwnd": parts[0],
                            "title": f"{icon}  {title}",
                            "raw_title": title,
                            "width": 1280,
                            "height": 800
                        })
                return windows
            except Exception:
                pass

        # Universal Fallback
        return [{"hwnd": 1, "title": "🌐  Desktop Web Browser Target", "raw_title": "Desktop Screen Target", "width": 1920, "height": 1080}]

    @staticmethod
    def focus_window(hwnd):
        """Brings specified window handle to foreground (Cross-Platform)."""
        if IS_WINDOWS and isinstance(hwnd, int):
            try:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9) # SW_RESTORE
                else:
                    user32.ShowWindow(hwnd, 5) # SW_SHOW
                time.sleep(0.05)
                user32.SetForegroundWindow(hwnd)
                time.sleep(0.1)
                return True
            except Exception as e:
                print(f"Error focusing window handle {hwnd}: {e}")
                return False
        return True

    @staticmethod
    def capture_window_image(hwnd):
        """Captures a PIL screenshot image of the specified window's screen region."""
        try:
            WindowManager.focus_window(hwnd)
            time.sleep(0.15)

            if IS_WINDOWS and isinstance(hwnd, int):
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                left = max(0, rect.left)
                top = max(0, rect.top)
                right = rect.right
                bottom = rect.bottom

                if right > left and bottom > top:
                    return ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)

            return ImageGrab.grab(all_screens=True)
        except Exception as e:
            print(f"Error capturing window screenshot: {e}")
        return None
