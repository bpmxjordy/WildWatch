"""
Test the trained Kea detector on a video clip.

Downloads a YouTube clip, splits into frames, runs YOLOv11 inference,
and stitches the annotated frames back into a video.
"""

import subprocess
import sys
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "runs" / "kea_detector" / "weights" / "best.pt"
WORK_DIR = BASE_DIR / "test_video"
FRAMES_DIR = WORK_DIR / "frames"
OUTPUT_FRAMES_DIR = WORK_DIR / "output_frames"
RAW_CLIP = WORK_DIR / "clip.mp4"
OUTPUT_VIDEO = WORK_DIR / "kea_detection_result.mp4"

VIDEO_URL = "https://www.youtube.com/watch?v=dNpkGQLNgYQ"
START_TIME = "00:01:26"
END_TIME = "00:01:32"


def step1_download():
    """Download the YouTube clip trimmed to the target segment."""
    print("\n[1/4] Downloading video clip...")
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_CLIP.exists():
        print("  Clip already downloaded, skipping.")
        return

    # Download with yt-dlp, using ffmpeg to trim
    subprocess.run([
        "yt-dlp",
        "--quiet",
        "--download-sections", f"*{START_TIME}-{END_TIME}",
        "--force-keyframes-at-cuts",
        "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "--merge-output-format", "mp4",
        "-o", str(RAW_CLIP),
        VIDEO_URL,
    ], check=True)

    print(f"  Saved clip to {RAW_CLIP}")


def step2_extract_frames():
    """Split the clip into individual frames."""
    print("\n[2/4] Extracting frames...")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    existing = list(FRAMES_DIR.glob("*.png"))
    if existing:
        print(f"  {len(existing)} frames already extracted, skipping.")
        return

    subprocess.run([
        "ffmpeg", "-i", str(RAW_CLIP),
        "-vsync", "0",
        str(FRAMES_DIR / "frame_%05d.png"),
    ], check=True, capture_output=True)

    count = len(list(FRAMES_DIR.glob("*.png")))
    print(f"  Extracted {count} frames")


def step3_run_inference():
    """Run the trained Kea detector on every frame."""
    print("\n[3/4] Running Kea detector inference...")
    OUTPUT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    frames = sorted(FRAMES_DIR.glob("*.png"))
    print(f"  {len(frames)} frames to process")

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

    # Count detections
    total_dets = sum(len(r.boxes) for r in results)
    frames_with_dets = sum(1 for r in results if len(r.boxes) > 0)
    print(f"  Done! {total_dets} detections across {frames_with_dets}/{len(frames)} frames")


def step4_stitch_video():
    """Reassemble annotated frames into a video."""
    print("\n[4/4] Stitching output video...")

    # Get the original FPS from the clip
    probe = subprocess.run([
        "ffmpeg", "-i", str(RAW_CLIP),
    ], capture_output=True, text=True)

    # Parse FPS from ffmpeg output (stderr)
    fps = "30"  # default fallback
    for line in probe.stderr.split("\n"):
        if "fps" in line and "Video:" in line:
            parts = line.split(",")
            for part in parts:
                part = part.strip()
                if "fps" in part:
                    fps = part.split()[0]
                    break
            break

    print(f"  Using {fps} fps")

    # Find output frames
    output_frames = sorted(OUTPUT_FRAMES_DIR.glob("*.png")) + sorted(OUTPUT_FRAMES_DIR.glob("*.jpg"))
    if not output_frames:
        print("  ERROR: No output frames found!")
        return

    # Determine the pattern
    first = output_frames[0]
    ext = first.suffix

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
    print(f"  Output video: {OUTPUT_VIDEO} ({size_mb:.1f} MB)")


def main():
    if not MODEL_PATH.exists():
        print(f"ERROR: Model not found at {MODEL_PATH}")
        sys.exit(1)

    step1_download()
    step2_extract_frames()
    step3_run_inference()
    step4_stitch_video()

    print(f"\n{'='*60}")
    print(f"Done! Result at: {OUTPUT_VIDEO}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
