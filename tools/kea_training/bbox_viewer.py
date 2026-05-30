"""
Kea Bounding Box Viewer

A lightweight web app to browse kea images with MegaDetector bounding box overlays.

Usage:
    python bbox_viewer.py
    Then open http://localhost:8501 in your browser.
"""

import json
import mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images" / "kea"
DETECTIONS_FILE = BASE_DIR / "megadetector_results.json"
PORT = 8501

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kea Bounding Box Viewer</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f1117;
    color: #e0e0e0;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: #1a1d27;
    border-bottom: 1px solid #2a2d37;
    flex-shrink: 0;
  }
  header h1 { font-size: 18px; font-weight: 600; }
  header h1 span { color: #4ade80; }
  .stats { font-size: 13px; color: #888; }

  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 20px;
    background: #14161e;
    border-bottom: 1px solid #2a2d37;
    flex-shrink: 0;
  }
  .toolbar button {
    background: #2a2d3a;
    border: 1px solid #3a3d4a;
    color: #e0e0e0;
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.15s;
  }
  .toolbar button:hover { background: #3a3d4a; }
  .toolbar button:disabled { opacity: 0.4; cursor: default; }
  .toolbar .nav-group { display: flex; gap: 4px; }
  .toolbar input[type="range"] { width: 120px; accent-color: #4ade80; }
  .toolbar label { font-size: 13px; color: #aaa; }
  .toolbar .spacer { flex: 1; }
  .toolbar .page-info { font-size: 13px; color: #aaa; font-variant-numeric: tabular-nums; }

  .filter-bar {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 20px;
    background: #14161e;
    border-bottom: 1px solid #2a2d37;
    flex-shrink: 0;
  }
  .filter-bar label { font-size: 12px; color: #888; }
  .filter-bar input[type="range"] { width: 160px; accent-color: #4ade80; }
  .filter-bar .conf-val { font-size: 12px; color: #4ade80; font-variant-numeric: tabular-nums; min-width: 36px; }
  .filter-bar select {
    background: #2a2d3a; border: 1px solid #3a3d4a; color: #e0e0e0;
    padding: 4px 8px; border-radius: 4px; font-size: 12px;
  }

  .main-area {
    flex: 1;
    display: flex;
    overflow: hidden;
  }

  .canvas-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
    background: #0a0c12;
  }
  canvas {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }
  .loading {
    position: absolute;
    color: #666;
    font-size: 14px;
  }

  .sidebar {
    width: 280px;
    background: #1a1d27;
    border-left: 1px solid #2a2d37;
    overflow-y: auto;
    flex-shrink: 0;
  }
  .sidebar h3 {
    padding: 12px 16px 8px;
    font-size: 13px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .detection-card {
    margin: 4px 8px;
    padding: 10px 12px;
    background: #22252f;
    border-radius: 6px;
    border-left: 3px solid #4ade80;
    font-size: 12px;
  }
  .detection-card.person { border-left-color: #f59e0b; }
  .detection-card.vehicle { border-left-color: #60a5fa; }
  .detection-card .det-type { font-weight: 600; margin-bottom: 4px; }
  .detection-card .det-conf { color: #4ade80; }
  .detection-card.person .det-conf { color: #f59e0b; }
  .detection-card.vehicle .det-conf { color: #60a5fa; }
  .detection-card .det-bbox { color: #666; font-family: monospace; font-size: 11px; margin-top: 2px; }

  .file-info {
    padding: 12px 16px;
    font-size: 12px;
    color: #666;
    word-break: break-all;
    border-bottom: 1px solid #2a2d37;
  }

  .keyboard-hint {
    padding: 12px 16px;
    font-size: 11px;
    color: #555;
    border-top: 1px solid #2a2d37;
  }
  .keyboard-hint kbd {
    background: #2a2d3a;
    padding: 1px 5px;
    border-radius: 3px;
    font-family: monospace;
    border: 1px solid #3a3d4a;
  }
</style>
</head>
<body>

<header>
  <h1>🦜 <span>Kea</span> Bounding Box Viewer</h1>
  <div class="stats" id="stats">Loading...</div>
</header>

<div class="toolbar">
  <div class="nav-group">
    <button id="btn-first" title="First image">⏮</button>
    <button id="btn-prev" title="Previous image (←)">◀</button>
    <button id="btn-next" title="Next image (→)">▶</button>
    <button id="btn-last" title="Last image">⏭</button>
  </div>
  <div class="page-info" id="page-info">0 / 0</div>
  <div class="spacer"></div>
  <label><input type="checkbox" id="chk-boxes" checked> Boxes</label>
  <label><input type="checkbox" id="chk-labels" checked> Labels</label>
</div>

<div class="filter-bar">
  <label>Min confidence:</label>
  <input type="range" id="conf-slider" min="0" max="100" value="30">
  <span class="conf-val" id="conf-val">0.30</span>
  <label>Category:</label>
  <select id="cat-filter">
    <option value="all">All</option>
    <option value="1" selected>Animal only</option>
    <option value="2">Person only</option>
    <option value="3">Vehicle only</option>
  </select>
  <label>Sort:</label>
  <select id="sort-mode">
    <option value="name">Filename</option>
    <option value="detections">Most detections</option>
    <option value="confidence">Highest confidence</option>
  </select>
</div>

<div class="main-area">
  <div class="canvas-container">
    <canvas id="canvas"></canvas>
    <div class="loading" id="loading">Loading...</div>
  </div>
  <div class="sidebar">
    <div class="file-info" id="file-info"></div>
    <h3>Detections</h3>
    <div id="detections-list"></div>
    <div class="keyboard-hint">
      <kbd>←</kbd> <kbd>→</kbd> navigate &nbsp;
      <kbd>B</kbd> toggle boxes &nbsp;
      <kbd>L</kbd> toggle labels
    </div>
  </div>
</div>

<script>
const CAT_NAMES = { "1": "Animal (Kea)", "2": "Person", "3": "Vehicle" };
const CAT_COLORS = { "1": "#4ade80", "2": "#f59e0b", "3": "#60a5fa" };
const CAT_CSS = { "1": "", "2": "person", "3": "vehicle" };

let allData = [];
let filtered = [];
let currentIdx = 0;
let currentImg = null;

// Fetch detection data
async function init() {
  const res = await fetch("/api/detections");
  const data = await res.json();
  allData = data.images || [];
  document.getElementById("stats").textContent =
    `${allData.length} images · ${allData.reduce((s, d) => s + d.detections.length, 0)} detections`;
  applyFilters();
}

function getConf() {
  return parseInt(document.getElementById("conf-slider").value) / 100;
}

function applyFilters() {
  const minConf = getConf();
  const catFilter = document.getElementById("cat-filter").value;
  const sortMode = document.getElementById("sort-mode").value;

  filtered = allData
    .map(img => {
      const dets = img.detections.filter(d =>
        d.conf >= minConf && (catFilter === "all" || d.category === catFilter)
      );
      return { ...img, filteredDets: dets };
    })
    .filter(img => img.filteredDets.length > 0);

  if (sortMode === "detections") {
    filtered.sort((a, b) => b.filteredDets.length - a.filteredDets.length);
  } else if (sortMode === "confidence") {
    filtered.sort((a, b) => {
      const maxA = Math.max(...a.filteredDets.map(d => d.conf));
      const maxB = Math.max(...b.filteredDets.map(d => d.conf));
      return maxB - maxA;
    });
  } else {
    filtered.sort((a, b) => a.file.localeCompare(b.file));
  }

  currentIdx = Math.min(currentIdx, Math.max(0, filtered.length - 1));
  updatePageInfo();
  loadCurrent();
}

function updatePageInfo() {
  document.getElementById("page-info").textContent =
    filtered.length > 0 ? `${currentIdx + 1} / ${filtered.length}` : "0 / 0";
}

function loadCurrent() {
  if (filtered.length === 0) {
    document.getElementById("loading").textContent = "No images match filters";
    document.getElementById("loading").style.display = "";
    document.getElementById("file-info").textContent = "";
    document.getElementById("detections-list").innerHTML = "";
    return;
  }

  const entry = filtered[currentIdx];
  document.getElementById("loading").style.display = "";
  document.getElementById("loading").textContent = "Loading...";
  document.getElementById("file-info").textContent = entry.file;

  // Render detection cards
  const listEl = document.getElementById("detections-list");
  listEl.innerHTML = entry.filteredDets
    .sort((a, b) => b.conf - a.conf)
    .map((d, i) => {
      const cls = CAT_CSS[d.category] || "";
      const name = CAT_NAMES[d.category] || d.category;
      const bbox = d.bbox.map(v => v.toFixed(3)).join(", ");
      return `<div class="detection-card ${cls}">
        <div class="det-type">#${i+1} ${name}</div>
        <div class="det-conf">Confidence: ${(d.conf * 100).toFixed(1)}%</div>
        <div class="det-bbox">[${bbox}]</div>
      </div>`;
    }).join("");

  // Load image
  const img = new Image();
  img.onload = () => {
    currentImg = img;
    document.getElementById("loading").style.display = "none";
    draw();
  };
  img.onerror = () => {
    document.getElementById("loading").textContent = "Failed to load image";
  };
  img.src = `/api/image?file=${encodeURIComponent(entry.file)}`;
}

function draw() {
  if (!currentImg || filtered.length === 0) return;
  const canvas = document.getElementById("canvas");
  const entry = filtered[currentIdx];
  const img = currentImg;

  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0);

  const showBoxes = document.getElementById("chk-boxes").checked;
  const showLabels = document.getElementById("chk-labels").checked;

  if (!showBoxes && !showLabels) return;

  for (const d of entry.filteredDets) {
    const [xMin, yMin, w, h] = d.bbox;
    const px = xMin * img.naturalWidth;
    const py = yMin * img.naturalHeight;
    const pw = w * img.naturalWidth;
    const ph = h * img.naturalHeight;
    const color = CAT_COLORS[d.category] || "#4ade80";

    if (showBoxes) {
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(2, Math.round(img.naturalWidth / 400));
      ctx.strokeRect(px, py, pw, ph);
    }

    if (showLabels) {
      const name = CAT_NAMES[d.category] || d.category;
      const label = `${name} ${(d.conf * 100).toFixed(0)}%`;
      const fontSize = Math.max(14, Math.round(img.naturalWidth / 60));
      ctx.font = `bold ${fontSize}px sans-serif`;
      const metrics = ctx.measureText(label);
      const labelH = fontSize + 6;

      ctx.fillStyle = color;
      ctx.fillRect(px, py - labelH, metrics.width + 8, labelH);
      ctx.fillStyle = "#000";
      ctx.fillText(label, px + 4, py - 4);
    }
  }
}

// Navigation
function go(idx) {
  currentIdx = Math.max(0, Math.min(filtered.length - 1, idx));
  updatePageInfo();
  loadCurrent();
}

document.getElementById("btn-first").onclick = () => go(0);
document.getElementById("btn-prev").onclick = () => go(currentIdx - 1);
document.getElementById("btn-next").onclick = () => go(currentIdx + 1);
document.getElementById("btn-last").onclick = () => go(filtered.length - 1);

document.addEventListener("keydown", e => {
  if (e.key === "ArrowLeft") go(currentIdx - 1);
  else if (e.key === "ArrowRight") go(currentIdx + 1);
  else if (e.key === "b" || e.key === "B") {
    const chk = document.getElementById("chk-boxes");
    chk.checked = !chk.checked;
    draw();
  } else if (e.key === "l" || e.key === "L") {
    const chk = document.getElementById("chk-labels");
    chk.checked = !chk.checked;
    draw();
  }
});

// Filter controls
document.getElementById("conf-slider").oninput = e => {
  document.getElementById("conf-val").textContent = (e.target.value / 100).toFixed(2);
  applyFilters();
};
document.getElementById("cat-filter").onchange = () => applyFilters();
document.getElementById("sort-mode").onchange = () => applyFilters();
document.getElementById("chk-boxes").onchange = () => draw();
document.getElementById("chk-labels").onchange = () => draw();

init();
</script>
</body>
</html>"""


class ViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._send_html(HTML_PAGE)

        elif parsed.path == "/api/detections":
            self._send_json()

        elif parsed.path == "/api/image":
            qs = parse_qs(parsed.query)
            filename = qs.get("file", [None])[0]
            if filename:
                self._send_image(filename)
            else:
                self.send_error(400, "Missing file parameter")

        else:
            self.send_error(404)

    def _send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self):
        if not DETECTIONS_FILE.exists():
            payload = json.dumps({"images": [], "error": "No detections file found"})
        else:
            with open(DETECTIONS_FILE) as f:
                payload = f.read()
        data = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_image(self, filename):
        # Sanitise: only allow files in the images directory
        safe_name = Path(filename).name
        img_path = IMAGES_DIR / safe_name
        if not img_path.exists() or not img_path.is_file():
            self.send_error(404, f"Image not found: {safe_name}")
            return
        mime = mimetypes.guess_type(str(img_path))[0] or "image/jpeg"
        data = img_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Quieter logging
        pass


def main():
    if not IMAGES_DIR.exists():
        print(f"WARNING: Images directory not found at {IMAGES_DIR}")
    if not DETECTIONS_FILE.exists():
        print(f"WARNING: Detections file not found at {DETECTIONS_FILE}")

    n_images = len(list(IMAGES_DIR.glob("*"))) if IMAGES_DIR.exists() else 0
    print(f"Kea Bounding Box Viewer")
    print(f"  Images: {n_images} in {IMAGES_DIR}")
    print(f"  Detections: {DETECTIONS_FILE}")
    print(f"\n  Open http://localhost:{PORT} in your browser\n")

    server = HTTPServer(("0.0.0.0", PORT), ViewerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
