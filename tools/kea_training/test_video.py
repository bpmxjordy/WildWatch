"""
Test the trained Kea detector on a YouTube video.

Downloads the video, splits into frames, runs YOLOv11 inference,
and stitches the annotated frames back into a video.

Usage:
    python test_video.py URL [--model v1|v2|v3] [--start 0:00] [--end 1:30] [--conf 0.25]

Examples:
    python test_video.py https://www.youtube.com/watch?v=tkXo1gbPjAQ
    python test_video.py https://www.youtube.com/watch?v=dNpkGQLNgYQ --start 1:26 --end 1:32 --model v3
"""

import argparse
import subprocess
import shutil
import sys
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent

MODELS = {
    "v1": BASE_DIR / "runs" / "kea_detector" / "weights" / "best.pt",
    "v2": BASE_DIR / "runs" / "kea_detector_v2" / "weights" / "best.pt",
    "v3": BASE_DIR / "runs" / "kea_detector_v3" / "weights" / "best.pt",
}


def main():
    parser = argparse.ArgumentParser(description="Test Kea detector on a YouTube video")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--model", default="v3", choices=["v1", "v2", "v3"],
                        help="Model version to use (default: v3)")
    parser.add_argument("--start", default=None, help="Start time e.g. 1:26 or 0:00:30")
    parser.add_argument("--end", default=None, help="End time e.g. 1:32 or 0:01:00")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: auto)")
    args = parser.parse_args()

    # Resolve model
    model_path = MODELS[args.model]
    if not model_path.exists():
        # Try any available model
        available = {k: v for k, v in MODELS.items() if v.exists()}
        if not available:
            print("ERROR: No trained model found. Run training first.")
            sys.exit(1)
        fallback = list(available.keys())[-1]
        print(f"WARNING: {args.model} model not found, using {fallback}")
        model_path = MODELS[fallback]

    print(f"Using model: {model_path.name} ({args.model})")

    # Set up directories
    work_dir = Path(args.output_dir) if args.output_dir else BASE_DIR / f"test_{args.model}"
    frames_dir = work_dir / "frames"
    output_frames_dir = work_dir / "output_frames"
    raw_clip = work_dir / "clip.mp4"
    output_video = work_dir / f"kea_detection_{args.model}_result.mp4"

    # Step 1: Download
    print(f"\n[1/4] Downloading video...")
    work_dir.mkdir(parents=True, exist_ok=True)

    if not raw_clip.exists():
        cmd = [
            "yt-dlp", "--quiet",
            "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", str(raw_clip),
        ]
        if args.start and args.end:
            # Normalise times to HH:MM:SS
            start = args.start if args.start.count(":") == 2 else f"00:{args.start}"
            end = args.end if args.end.count(":") == 2 else f"00:{args.end}"
            cmd += ["--download-sections", f"*{start}-{end}", "--force-keyframes-at-cuts"]

        cmd.append(args.url)
        subprocess.run(cmd, check=True)
        print(f"  Saved to {raw_clip}")
    else:
        print("  Already downloaded.")

    # Step 2: Extract frames
    print("\n[2/4] Extracting frames...")
    frames_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(frames_dir.glob("*.png"))
    if not existing:
        subprocess.run([
            "ffmpeg", "-i", str(raw_clip),
            "-vsync", "0",
            str(frames_dir / "frame_%05d.png"),
        ], check=True, capture_output=True)
        existing = sorted(frames_dir.glob("*.png"))
    print(f"  {len(existing)} frames")

    # Step 3: Inference
    print(f"\n[3/4] Running Kea detector ({args.model}, conf={args.conf})...")

    # Clean previous output
    if output_frames_dir.exists():
        shutil.rmtree(output_frames_dir)

    model = YOLO(str(model_path))
    results = model.predict(
        source=str(frames_dir),
        save=True,
        save_txt=False,
        project=str(work_dir),
        name="output_frames",
        exist_ok=True,
        conf=args.conf,
        line_width=2,
        show_labels=True,
        show_conf=True,
    )
    total_dets = sum(len(r.boxes) for r in results)
    frames_with = sum(1 for r in results if len(r.boxes) > 0)
    print(f"  {total_dets} detections across {frames_with}/{len(results)} frames")

    # Step 4: Stitch
    print("\n[4/4] Stitching video...")
    probe = subprocess.run(["ffmpeg", "-i", str(raw_clip)], capture_output=True, text=True)
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

    output_files = sorted(output_frames_dir.glob("*.png")) + sorted(output_frames_dir.glob("*.jpg"))
    if not output_files:
        print("  ERROR: No output frames found!")
        sys.exit(1)

    ext = output_files[0].suffix
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", fps,
        "-i", str(output_frames_dir / f"frame_%05d{ext}"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        str(output_video),
    ], check=True, capture_output=True)

    size_mb = output_video.stat().st_size / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"Done! Output: {output_video} ({size_mb:.1f} MB)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
