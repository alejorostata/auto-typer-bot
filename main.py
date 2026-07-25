"""
Auto-Typer Bot Pro - Primary Application Entry Point.
Run this script to launch the Auto-Typer Bot Desktop Application.
Usage: python main.py
"""
import sys
import os
import platform
import subprocess
import importlib

# Ensure UTF-8 output encoding for Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add root directory to sys.path for clean imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_and_install_dependencies():
    """
    Automatic Dependency Guard & Auto-Installer.
    Verifies that all required packages exist. Automatically installs any missing dependency.
    """
    print("[+] Auto-Typer Bot Dependency Guard:")

    # Mapping of (pip package name, Python import module name)
    dependencies = [
        ("pywebview", "webview"),
        ("Pillow", "PIL"),
        ("pynput", "pynput"),
        ("rapidocr-onnxruntime", "rapidocr_onnxruntime"),
        ("numpy", "numpy"),
    ]

    if platform.system() == "Windows":
        dependencies.append(("winocr", "winocr"))

    all_satisfied = True
    for pip_name, import_name in dependencies:
        try:
            importlib.import_module(import_name)
            print(f"  [OK] checking {pip_name}... already installed.")
        except ImportError:
            all_satisfied = False
            print(f"  [!] checking {pip_name}... not found. Installing via pip...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", pip_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print(f"  [OK] successfully installed {pip_name}!")
            except Exception as e:
                print(f"  [ERR] Error installing {pip_name}: {e}")

    if all_satisfied:
        print("[+] All dependencies verified!")
    print("")

def main():
    check_and_install_dependencies()
    print("[+] Launching Auto-Typer Bot...")
    from ui.app import launch_ui
    launch_ui()

if __name__ == "__main__":
    main()
