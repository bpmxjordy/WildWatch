"""Test kea detector on a second YouTube video (full length)."""

import subprocess
import sys
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "runs" / "kea_detector" / "weights" / "best.pt"
WORK_DIR = BASE_DIR / "test_video2"
FRAMES_DIR = WORK_DIR / "frames"
OUTPUT_FRAMES_DIR = WORK_DIR / "output_frames"
RAW_CLIP = WORK_DIR / "clip.mp4"
OUTPUT_VIDEO = WORK_DIR / "kea_detection_result.mp4"

VIDEO_URL = "https://www.youtube.com/watch?v=tkXo1gbPjAQ"


def main():
    if not MODEL_PATH.exists():
        print(f"ERROR: Model not found at {MODEL_PATH}")
        sys.exit(1)

    # Step 1: Download
    print("\n[1/4] Downloading full video...")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    if not RAW_CLIP.exists():
        subprocess.run([
            "yt-dlp", "--quiet",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", str(RAW_CLIP),
            VIDEO_URL,
        ], check=True)
        print(f"  Saved to {RAW_CLIP}")
    else:
        print("  Already downloaded.")

    # Step 2: Extract frames
    print("\n[2/4] Extracting frames...")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(FRAMES_DIR.glob("*.png"))
    if not existing:
        subprocess.run([
            "ffmpeg", "-i", str(RAW_CLIP),
            "-vsync", "0",
            str(FRAMES_DIR / "frame_%05d.png"),
        ], check=True, capture_output=True)
        existing = list(FRAMES_DIR.glob("*.png"))
    print(f"  {len(existing)} frames")

    # Step 3: Inference
    print("\n[3/4] Running Kea detector...")
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

    # Step 4: Stitch
    print("\n[4/4] Stitching video...")
    probe = subprocess.run(["ffmpeg", "-i", str(RAW_CLIP)], capture_output=True, text=True)
    fps = "25"
    for line in probe.stderr.split("\n"):
        if "fps" in line and "Video:" in line:
            for part in line.split(","):
                part = part.strip()
                if "fps" in part:
                    fps = part.split()[0]
                    break
            break
    print(f"  Using {fps} fps")

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
    print(f"\n  Output: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")
    print("Done!")


if __name__ == "__main__":
    main()
