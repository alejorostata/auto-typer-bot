let windowsList = [];
let isDarkMode = false;
let isDrawerOpen = false;

document.addEventListener("DOMContentLoaded", () => {
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const refreshBtn = document.getElementById("refreshBtn");
  const windowSelect = document.getElementById("windowSelect");
  const selectAreaBtn = document.getElementById("selectAreaBtn");
  const startBtn = document.getElementById("startBtn");
  const pauseBtn = document.getElementById("pauseBtn");
  const stopBtn = document.getElementById("stopBtn");
  const toggleCropBtn = document.getElementById("toggleCropBtn");
  const cropDrawer = document.getElementById("cropDrawer");

  // Theme Toggle
  themeToggleBtn.addEventListener("click", () => {
    isDarkMode = !isDarkMode;
    document.documentElement.setAttribute("data-theme", isDarkMode ? "dark" : "light");
    themeToggleBtn.textContent = isDarkMode ? "☀️ Light Mode" : "🌙 Dark Mode";
  });

  // Toggle Collapsible Crop Drawer
  toggleCropBtn.addEventListener("click", () => {
    isDrawerOpen = !isDrawerOpen;
    cropDrawer.style.display = isDrawerOpen ? "flex" : "none";
    toggleCropBtn.textContent = isDrawerOpen ? "✖ Hide Crop Preview" : "📷 View Crop Preview";
  });

  // Window Select Event
  windowSelect.addEventListener("change", (e) => {
    const selectedTitle = e.target.value;
    const found = windowsList.find(w => w.title === selectedTitle);
    if (found && window.pywebview) {
      window.pywebview.api.set_target_hwnd(found.hwnd, found.raw_title);
    }
  });

  // Refresh Windows
  refreshBtn.addEventListener("click", refreshWindows);

  // Select Screen Area (Multi-Monitor Virtual Desktop Box Drawing)
  selectAreaBtn.addEventListener("click", () => {
    if (window.pywebview) {
      window.pywebview.api.select_screen_area();
    }
  });

  // Start Typing
  startBtn.addEventListener("click", () => {
    const text = document.getElementById("visionStream").value.trim();
    if (!text) {
      alert("No text to type! Click '🎯 Select Screen Area' or enter text in the box.");
      return;
    }
    const minWpm = parseInt(document.getElementById("minWpm").value) || 80;
    const maxWpm = parseInt(document.getElementById("maxWpm").value) || 120;
    const humanJitter = document.getElementById("humanJitter").checked;
    const autoRescan = document.getElementById("autoRescan").checked;

    if (window.pywebview) {
      window.pywebview.api.start_typing(text, minWpm, maxWpm, humanJitter, autoRescan);
      startBtn.disabled = true;
      pauseBtn.disabled = false;
      stopBtn.disabled = false;
      document.getElementById("statusBadge").textContent = "TYPING...";
      document.getElementById("statusBadge").style.backgroundColor = "var(--accent-color)";
      document.getElementById("typingStream").value = "";
    }
  });

  // Pause Typing
  pauseBtn.addEventListener("click", () => {
    if (window.pywebview) {
      window.pywebview.api.toggle_pause().then(isPaused => {
        pauseBtn.textContent = isPaused ? "▶ Resume" : "⏸ Pause";
        document.getElementById("statusBadge").textContent = isPaused ? "PAUSED" : "TYPING...";
        document.getElementById("statusBadge").style.backgroundColor = isPaused ? "var(--warning-color)" : "var(--accent-color)";
      });
    }
  });

  // Stop Typing
  stopBtn.addEventListener("click", () => {
    if (window.pywebview) {
      window.pywebview.api.stop_typing();
      resetUiAfterStop("STOPPED", "var(--danger-color)");
    }
  });

  // Initial Window Refresh when PyWebView API is ready
  window.addEventListener('pywebviewready', () => {
    refreshWindows();
  });
});

function refreshWindows() {
  const windowSelect = document.getElementById("windowSelect");
  windowSelect.innerHTML = "<option>Scanning open desktop windows...</option>";
  
  if (window.pywebview) {
    window.pywebview.api.get_open_windows().then(wins => {
      windowsList = wins;
      windowSelect.innerHTML = "";
      if (!wins || wins.length === 0) {
        windowSelect.innerHTML = "<option>No open application windows found</option>";
        return;
      }
      wins.forEach((w, idx) => {
        const opt = document.createElement("option");
        opt.value = w.title;
        opt.textContent = w.title;
        windowSelect.appendChild(opt);
      });
      // Select first
      windowSelect.value = wins[0].title;
      window.pywebview.api.set_target_hwnd(wins[0].hwnd, wins[0].raw_title);
    });
  }
}

// Global JS callbacks invoked from Python
window.onTextExtracted = function(extractedText, base64Img, statusMsg) {
  document.getElementById("visionStream").value = extractedText;
  document.getElementById("statusText").textContent = statusMsg;
  
  const imgEl = document.getElementById("cropPreviewImg");
  const toggleBtn = document.getElementById("toggleCropBtn");
  if (base64Img) {
    imgEl.src = "data:image/png;base64," + base64Img;
    toggleBtn.style.display = "inline-flex";
  }
};

window.onTypingProgress = function(wordsTyped, totalWords, pctVal, liveWpm, currentWord) {
  const pctInt = Math.floor(pctVal * 100);
  document.getElementById("progressBarFill").style.width = pctInt + "%";
  document.getElementById("progressText").textContent = `Typed: ${wordsTyped} / ${totalWords} words (${pctInt}%)`;
  document.getElementById("liveWpm").textContent = `Live Speed: ~${liveWpm} WPM`;
  
  const typingStream = document.getElementById("typingStream");
  typingStream.value += currentWord + " ";
  typingStream.scrollTop = typingStream.scrollHeight;
};

window.onTextUpdated = function(updatedFullText) {
  document.getElementById("visionStream").value = updatedFullText;
};

window.onTypingComplete = function() {
  resetUiAfterStop("COMPLETED", "var(--success-color)");
};

window.onTypingError = function(err) {
  resetUiAfterStop("ERROR", "var(--danger-color)");
  alert("Typing Error: " + err);
};

function resetUiAfterStop(statusText, color) {
  document.getElementById("startBtn").disabled = false;
  document.getElementById("pauseBtn").disabled = true;
  document.getElementById("pauseBtn").textContent = "⏸ Pause";
  document.getElementById("stopBtn").disabled = true;
  document.getElementById("statusBadge").textContent = statusText;
  document.getElementById("statusBadge").style.backgroundColor = color;
}
