# Auto-Typer Bot ⚡

A cross-platform Auto-Typer application powered by Python, PyWebView, and Screen Vision OCR. Designed for automated typing tests, data entry simulation, and accessibility automation across **Windows, macOS, and Linux**.

---

## 🚀 Quick Start (Zero Configuration)

Ensure that **Python 3.8 or higher** is installed on your computer. Open a terminal in the project folder, and execute the following command to launch the application:

```bash
python main.py
```

> **🛡️ Automatic Dependency Guard**: On launch, `main.py` automatically verifies and installs any missing Python packages (`pywebview`, `Pillow`, `pynput`, `rapidocr-onnxruntime`, `numpy`, `winocr`) via `pip` in the background. No manual setup is required!

---

## 🔧 Manual Installation & Troubleshooting

If automatic package installation fails due to strict firewall rules, offline environments, or corporate proxies, you can manually install all required dependencies be executing the following command in your terminal inside the project folder:

```bash
pip install -r requirements.txt
```

---

## 📁 Clean Project Architecture

```
auto_typer_bot/
├── main.py                     # Primary Application Entry Point & Dependency Guard
├── config.py                   # Global Configuration & Speed Defaults
├── requirements.txt            # Python Dependencies Specification
├── README.md                   # Project Documentation
│
├── core/                       # Core Business Logic & Engines Module
│   ├── __init__.py
│   ├── ocr_engine.py           # Screen Vision OCR (Windows Native Media OCR + RapidOCR + Tesseract)
│   ├── typing_engine.py        # Keystroke Engine & Continuous Queue Merger
│   └── window_manager.py       # Cross-Platform Window Enumeration & Focus
│
├── ui/                         # User Interface Module (Web-based PyWebView Dashboard)
│   ├── __init__.py
│   ├── app.py                  # PyWebView Launcher & Python-JS Bridge
│   ├── index.html              # Modern HTML5 Layout
│   ├── style.css               # Modern CSS Glassmorphic Design
│   └── app.js                  # Frontend Real-Time Controller
│
└── tests/                      # Unit Test Suite
    ├── __init__.py
    ├── test_config.py          # Configuration Constants Unit Tests
    ├── test_ocr_engine.py      # OCR Engine & DPI Scaling Unit Tests
    ├── test_typing_engine.py   # Keystroke Engine Unit Tests
    └── test_window_manager.py  # Window Manager Unit Tests
```

---

## 🧪 Running Unit Tests

To run the automated unit test suite:

```bash
python -m unittest discover tests
```

---

## ✨ Features & Highlights

- **🎯 Cross-Platform Multi-Monitor Crop**: Drag a red selection box on any monitor (including secondary portrait monitors) to crop target passage text.
- **⚡ Human Micro-Jitter**: Simulates natural human typing variations and subtle micro-pauses between keystrokes to bypass anti-bot detectors.
- **🔄 Queue-Drain Continuous Re-Scan**: Intelligently scans the screen for newly scrolled text *only* when the current passage is completely typed, ensuring 100% flawless typing accuracy without mid-passage OCR noise.
- **👁️ Raw Crop Precision OCR**: Employs raw screen crops directly to native OCR engines, preventing contrast distortion and guaranteeing razor-sharp character extraction for custom web fonts.
- **🌙 Light & Dark Themes**: Sleek UI with native OS tooltips and dark mode support.
- **🛑 Emergency Stop**: Press the `[ESC]` key at any time to immediately abort active typing.
