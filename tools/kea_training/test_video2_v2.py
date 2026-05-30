"""Test kea detector v2 on the second YouTube video (reuses existing frames)."""

import subprocess
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "runs" / "kea_detector_v2" / "weights" / "best.pt"
WORK_DIR = BASE_DIR / "test_video2"
FRAMES_DIR = WORK_DIR / "frames"
OUTPUT_FRAMES_DIR = WORK_DIR / "output_frames"
RAW_CLIP = WORK_DIR / "clip.mp4"
OUTPUT_VIDEO = WORK_DIR / "kea_detection_v2_result.mp4"

print(f"Using model: {MODEL_PATH}")
print(f"Frames dir: {FRAMES_DIR}")

frames = sorted(FRAMES_DIR.glob("*.png"))
print(f"\n[1/2] Running Kea detector v2 on {len(frames)} frames...")

model = YOLO(str(MODEL_PATH))
results = model.predict(
    source=str(FRAMES_DIR),
    save=True,
    save_txt=False,
    project=str(WORK_DIR),
    name="output_frames",
    exist_ok=True,
    conf=0.25,
    line_width=2,
    show_labels=True,
    show_conf=True,
)

total_dets = sum(len(r.boxes) for r in results)
frames_with = sum(1 for r in results if len(r.boxes) > 0)
print(f"  {total_dets} detections across {frames_with}/{len(results)} frames")

print("\n[2/2] Stitching video...")
probe = subprocess.run(["ffmpeg", "-i", str(RAW_CLIP)], capture_output=True, text=True)
fps = "29.97"
for line in probe.stderr.split("\n"):
    if "fps" in line and "Video:" in line:
        for part in line.split(","):
            if "fps" in part.strip():
                fps = part.strip().split()[0]
                break
        break

output_files = sorted(OUTPUT_FRAMES_DIR.glob("*.png")) + sorted(OUTPUT_FRAMES_DIR.glob("*.jpg"))
ext = output_files[0].suffix if output_files else ".jpg"

subprocess.run([
    "ffmpeg", "-y",
    "-framerate", fps,
    "-i", str(OUTPUT_FRAMES_DIR / f"frame_%05d{ext}"),
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "18",
    str(OUTPUT_VIDEO),
], check=True, capture_output=True)

size_mb = OUTPUT_VIDEO.stat().st_size / (1024 * 1024)
print(f"\nDone! Output: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")
