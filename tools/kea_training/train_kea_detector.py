"""
Kea Detection Model Training Pipeline

Trains a YOLOv11 model to detect Kea (New Zealand alpine parrot) using:
  1. NZ Trail Cams dataset (image-level labels, 54,790 kea images)
  2. MegaDetector v5 for auto-generating bounding boxes
  3. Ultralytics YOLOv11 for final training

Usage:
    # Step 1: Download kea images from the dataset
    python train_kea_detector.py download --max-images 5000

    # Step 2: Run MegaDetector to generate bounding boxes
    python train_kea_detector.py detect

    # Step 3: Convert detections to YOLO format and split train/val
    python train_kea_detector.py prepare

    # Step 4: Train YOLOv11
    python train_kea_detector.py train --epochs 100

    # Or run the full pipeline:
    python train_kea_detector.py all --max-images 5000 --epochs 100
"""

import argparse
import json
import os
import random
import shutil
import sys
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
METADATA_FILE = BASE_DIR / "metadata.json"
IMAGES_DIR = BASE_DIR / "images" / "kea"
DETECTIONS_FILE = BASE_DIR / "megadetector_results.json"
DATASET_DIR = BASE_DIR / "dataset"
DATASET_YAML = BASE_DIR / "kea_dataset.yaml"

IMAGE_BASE_URL = "https://storage.googleapis.com/public-datasets-lila/nz-trailcams"
KEA_CATEGORY_ID = 42
MEGADETECTOR_CONFIDENCE_THRESHOLD = 0.3
TRAIN_SPLIT = 0.85


# ---------------------------------------------------------------------------
# Step 1: Download kea images
# ---------------------------------------------------------------------------

def download_images(max_images: int = 5000, workers: int = 8):
    print(f"\n{'='*60}")
    print(f"Step 1: Downloading up to {max_images} kea images")
    print(f"{'='*60}\n")

    with open(METADATA_FILE) as f:
        meta = json.load(f)

    kea_image_ids = {
        a["image_id"]
        for a in meta["annotations"]
        if a.get("category_id") == KEA_CATEGORY_ID
    }
    kea_images = [img for img in meta["images"] if img["id"] in kea_image_ids]
    print(f"Found {len(kea_images)} kea images in metadata")

    if max_images < len(kea_images):
        random.seed(42)
        kea_images = random.sample(kea_images, max_images)
        print(f"Randomly sampled {max_images} images")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    existing = {f.name for f in IMAGES_DIR.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
    to_download = []
    for img in kea_images:
        fname = img["file_name"].replace("/", "_")
        if fname not in existing:
            to_download.append((img["file_name"], fname))

    print(f"Already have {len(existing)} images, need to download {len(to_download)}")

    if not to_download:
        print("All images already downloaded!")
        return

    failed = []
    completed = 0

    def fetch(item):
        remote_path, local_name = item
        url = f"{IMAGE_BASE_URL}/{remote_path}"
        dest = IMAGES_DIR / local_name
        try:
            urllib.request.urlretrieve(url, dest)
            return True
        except Exception as e:
            return f"{local_name}: {e}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in to_download}
        for future in as_completed(futures):
            result = future.result()
            completed += 1
            if result is True:
                if completed % 100 == 0:
                    print(f"  Downloaded {completed}/{len(to_download)}")
            else:
                failed.append(result)

    print(f"\nDownload complete: {completed - len(failed)} succeeded, {len(failed)} failed")
    if failed:
        print(f"First 10 failures:")
        for f in failed[:10]:
            print(f"  {f}")


# ---------------------------------------------------------------------------
# Step 2: Run MegaDetector to generate bounding boxes
# ---------------------------------------------------------------------------

def run_megadetector(batch_size: int = 16):
    print(f"\n{'='*60}")
    print("Step 2: Running MegaDetector for bounding box generation")
    print(f"{'='*60}\n")

    image_files = sorted(IMAGES_DIR.glob("*.[jJ][pP][gG]")) + sorted(IMAGES_DIR.glob("*.[jJ][pP][eE][gG]"))
    if not image_files:
        print("ERROR: No images found. Run 'download' step first.")
        sys.exit(1)

    print(f"Found {len(image_files)} images to process")

    already_done = {}
    if DETECTIONS_FILE.exists():
        with open(DETECTIONS_FILE) as f:
            existing_results = json.load(f)
        already_done = {r["file"]: r for r in existing_results.get("images", [])}
        print(f"Found {len(already_done)} existing detections, will skip those")

    to_process = [f for f in image_files if f.name not in already_done]
    if not to_process:
        print("All images already processed!")
        return

    print(f"Processing {len(to_process)} new images...")

    from megadetector.detection.run_detector import load_detector
    from megadetector.utils.ct_utils import truncate_float
    import torch
    from PIL import Image
    import numpy as np

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("Loading MegaDetector model...")
    detector = load_detector("MDV5A")

    results = list(already_done.values())

    for i, img_path in enumerate(to_process):
        try:
            img = Image.open(img_path).convert("RGB")
            result = detector.generate_detections_one_image(
                np.array(img), str(img_path), detection_threshold=0.01
            )

            results.append({
                "file": img_path.name,
                "detections": [
                    {
                        "category": d["category"],
                        "conf": truncate_float(d["conf"], precision=4),
                        "bbox": [truncate_float(x, precision=4) for x in d["bbox"]],
                    }
                    for d in result["detections"]
                ],
            })
        except Exception as e:
            print(f"  Error processing {img_path.name}: {e}")
            results.append({"file": img_path.name, "detections": []})

        if (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(to_process)} images")
            with open(DETECTIONS_FILE, "w") as f:
                json.dump({"images": results}, f)

    with open(DETECTIONS_FILE, "w") as f:
        json.dump({"images": results}, f, indent=2)

    total_dets = sum(len(r["detections"]) for r in results)
    print(f"\nMegaDetector complete: {len(results)} images, {total_dets} total detections")


# ---------------------------------------------------------------------------
# Step 3: Convert to YOLO format and split train/val
# ---------------------------------------------------------------------------

def prepare_dataset():
    print(f"\n{'='*60}")
    print("Step 3: Converting to YOLO format and splitting train/val")
    print(f"{'='*60}\n")

    if not DETECTIONS_FILE.exists():
        print("ERROR: No detections file found. Run 'detect' step first.")
        sys.exit(1)

    with open(DETECTIONS_FILE) as f:
        data = json.load(f)

    # MegaDetector categories: "1" = animal, "2" = person, "3" = vehicle
    # We only want animal detections and relabel them all as "kea" (class 0)
    ANIMAL_CATEGORY = "1"

    kept = 0
    skipped_no_animal = 0
    image_labels = []

    for entry in data["images"]:
        fname = entry["file"]
        img_path = IMAGES_DIR / fname
        if not img_path.exists():
            continue

        animal_dets = [
            d for d in entry["detections"]
            if d["category"] == ANIMAL_CATEGORY
            and d["conf"] >= MEGADETECTOR_CONFIDENCE_THRESHOLD
        ]

        if not animal_dets:
            skipped_no_animal += 1
            continue

        # MegaDetector bbox format: [x_min, y_min, width, height] (normalized 0-1)
        # YOLO format: [class_id, x_center, y_center, width, height] (normalized 0-1)
        yolo_lines = []
        for d in animal_dets:
            x_min, y_min, w, h = d["bbox"]
            x_center = x_min + w / 2
            y_center = y_min + h / 2
            # Clamp to [0, 1]
            x_center = max(0, min(1, x_center))
            y_center = max(0, min(1, y_center))
            w = max(0, min(1, w))
            h = max(0, min(1, h))
            yolo_lines.append(f"0 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

        image_labels.append((fname, yolo_lines))
        kept += 1

    print(f"Images with animal detections: {kept}")
    print(f"Images skipped (no confident animal detection): {skipped_no_animal}")

    if kept == 0:
        print("ERROR: No usable images. Check MegaDetector results.")
        sys.exit(1)

    # Shuffle and split
    random.seed(42)
    random.shuffle(image_labels)
    split_idx = int(len(image_labels) * TRAIN_SPLIT)
    train_set = image_labels[:split_idx]
    val_set = image_labels[split_idx:]
    print(f"Train: {len(train_set)}, Val: {len(val_set)}")

    # Create directory structure
    for split in ("train", "val"):
        (DATASET_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    def write_split(items, split_name):
        for fname, labels in items:
            src = IMAGES_DIR / fname
            stem = Path(fname).stem

            # Copy image
            dst_img = DATASET_DIR / split_name / "images" / fname
            if not dst_img.exists():
                shutil.copy2(src, dst_img)

            # Write label
            dst_label = DATASET_DIR / split_name / "labels" / (stem + ".txt")
            with open(dst_label, "w") as f:
                f.write("\n".join(labels) + "\n")

    write_split(train_set, "train")
    write_split(val_set, "val")

    # Write dataset YAML
    yaml_content = f"""path: {DATASET_DIR.resolve().as_posix()}
train: train/images
val: val/images

names:
  0: kea
"""
    with open(DATASET_YAML, "w") as f:
        f.write(yaml_content)

    print(f"\nDataset prepared at: {DATASET_DIR}")
    print(f"Dataset YAML: {DATASET_YAML}")


# ---------------------------------------------------------------------------
# Step 4: Train YOLOv11
# ---------------------------------------------------------------------------

def train_model(epochs: int = 100, imgsz: int = 640, batch: int = 16, model_size: str = "n"):
    print(f"\n{'='*60}")
    print(f"Step 4: Training YOLOv11{model_size} for {epochs} epochs")
    print(f"{'='*60}\n")

    if not DATASET_YAML.exists():
        print("ERROR: Dataset YAML not found. Run 'prepare' step first.")
        sys.exit(1)

    from ultralytics import YOLO

    model_name = f"yolo11{model_size}.pt"
    print(f"Loading pretrained {model_name}...")
    model = YOLO(model_name)

    results = model.train(
        data=str(DATASET_YAML.resolve()),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        name="kea_detector",
        project=str(BASE_DIR / "runs"),
        exist_ok=True,
        patience=20,
        save=True,
        plots=True,
        device=0,
        workers=2,
    )

    print(f"\nTraining complete!")
    print(f"Best model: {BASE_DIR / 'runs' / 'kea_detector' / 'weights' / 'best.pt'}")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kea Detection Training Pipeline")
    parser.add_argument(
        "step",
        choices=["download", "detect", "prepare", "train", "all"],
        help="Pipeline step to run",
    )
    parser.add_argument("--max-images", type=int, default=5000, help="Max kea images to download (default: 5000)")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs (default: 100)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--model-size", type=str, default="n", choices=["n", "s", "m", "l", "x"],
                        help="YOLOv11 model size (default: n)")
    parser.add_argument("--workers", type=int, default=8, help="Download workers (default: 8)")
    parser.add_argument("--confidence", type=float, default=0.3,
                        help="MegaDetector confidence threshold (default: 0.3)")

    args = parser.parse_args()

    global MEGADETECTOR_CONFIDENCE_THRESHOLD
    MEGADETECTOR_CONFIDENCE_THRESHOLD = args.confidence

    if args.step in ("download", "all"):
        download_images(max_images=args.max_images, workers=args.workers)

    if args.step in ("detect", "all"):
        run_megadetector()

    if args.step in ("prepare", "all"):
        prepare_dataset()

    if args.step in ("train", "all"):
        train_model(
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            model_size=args.model_size,
        )


if __name__ == "__main__":
    main()
