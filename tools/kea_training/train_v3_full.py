"""
Kea Detector v3 — Full Dataset Training Pipeline

Uses ALL 54,790 kea images + 2,000 non-kea negatives.
Runs MegaDetector only on images not already processed.
Trains YOLOv11m for 150 epochs.

Usage:
    python train_v3_full.py download     # Download all kea images
    python train_v3_full.py detect       # Run MegaDetector on new images
    python train_v3_full.py prepare      # Build YOLO dataset
    python train_v3_full.py train        # Train YOLOv11m
    python train_v3_full.py all          # Run full pipeline
"""

import argparse
import json
import random
import shutil
import sys
import urllib.request
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
METADATA_FILE = BASE_DIR / "metadata.json"
IMAGES_DIR = BASE_DIR / "images" / "kea"
NEGATIVES_DIR = BASE_DIR / "images" / "negatives"
DETECTIONS_FILE = BASE_DIR / "megadetector_results_full.json"
DATASET_DIR = BASE_DIR / "dataset_v3"
DATASET_YAML = BASE_DIR / "kea_dataset_v3.yaml"

NZ_IMAGE_BASE = "https://storage.googleapis.com/public-datasets-lila/nz-trailcams"

KEA_CATEGORY_ID = 42
CONFIDENCE_THRESHOLD = 0.3
TRAIN_SPLIT = 0.85
NUM_NEGATIVE_ANIMALS = 2000


# ---------------------------------------------------------------------------
# Step 1: Download ALL kea images
# ---------------------------------------------------------------------------

def download_all_kea(workers=12):
    print(f"\n{'='*60}")
    print("Step 1: Downloading ALL kea images")
    print(f"{'='*60}\n")

    with open(METADATA_FILE) as f:
        meta = json.load(f)

    kea_image_ids = {
        a["image_id"]
        for a in meta["annotations"]
        if a.get("category_id") == KEA_CATEGORY_ID
    }
    kea_images = [img for img in meta["images"] if img["id"] in kea_image_ids]
    print(f"Total kea images in dataset: {len(kea_images)}")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    existing = {f.name for f in IMAGES_DIR.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
    to_download = []
    for img in kea_images:
        fname = img["file_name"].replace("/", "_")
        if fname not in existing:
            to_download.append((img["file_name"], fname))

    print(f"Already have {len(existing)}, need to download {len(to_download)}")

    if not to_download:
        print("All images already downloaded!")
        return

    completed = 0
    failed = 0

    def fetch(item):
        remote, local = item
        url = f"{NZ_IMAGE_BASE}/{remote}"
        try:
            urllib.request.urlretrieve(url, IMAGES_DIR / local)
            return True
        except Exception:
            return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in to_download}
        for future in as_completed(futures):
            if future.result():
                completed += 1
            else:
                failed += 1
            total = completed + failed
            if total % 500 == 0:
                print(f"  Progress: {total}/{len(to_download)} ({completed} ok, {failed} failed)")

    print(f"\nDownload complete: {completed} succeeded, {failed} failed")


# ---------------------------------------------------------------------------
# Step 1b: Download negative images (if not already present)
# ---------------------------------------------------------------------------

def download_negatives(workers=8):
    print(f"\n{'='*60}")
    print(f"Step 1b: Downloading {NUM_NEGATIVE_ANIMALS} non-kea negatives")
    print(f"{'='*60}\n")

    NEGATIVES_DIR.mkdir(parents=True, exist_ok=True)

    existing = {f.name for f in NEGATIVES_DIR.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
    if len(existing) >= NUM_NEGATIVE_ANIMALS:
        print(f"Already have {len(existing)} negatives, skipping.")
        return

    with open(METADATA_FILE) as f:
        meta = json.load(f)

    preferred_species = [
        "kaka", "parakeet", "rosella",
        "harrier", "robin", "tui", "bellbird", "fantail",
        "possum", "cat", "stoat", "hedgehog",
        "weka", "pukeko", "takahe",
    ]

    non_kea = [img for img in meta["images"] if img.get("species") != "kea"]
    preferred = [img for img in non_kea if img.get("species") in preferred_species]
    other = [img for img in non_kea if img.get("species") not in preferred_species]

    random.seed(42)
    random.shuffle(preferred)
    random.shuffle(other)

    selected = preferred[:NUM_NEGATIVE_ANIMALS]
    if len(selected) < NUM_NEGATIVE_ANIMALS:
        selected += other[:NUM_NEGATIVE_ANIMALS - len(selected)]

    to_download = []
    for img in selected:
        fname = "neg_" + img["file_name"].replace("/", "_")
        if fname not in existing:
            to_download.append((img["file_name"], fname))

    print(f"Downloading {len(to_download)} negative images...")

    completed = 0
    failed = 0

    def fetch(item):
        remote, local = item
        url = f"{NZ_IMAGE_BASE}/{remote}"
        try:
            urllib.request.urlretrieve(url, NEGATIVES_DIR / local)
            return True
        except Exception:
            return False

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, item): item for item in to_download}
        for future in as_completed(futures):
            if future.result():
                completed += 1
            else:
                failed += 1
            total = completed + failed
            if total % 200 == 0:
                print(f"  Progress: {total}/{len(to_download)}")

    print(f"Downloaded {completed}, failed {failed}")


# ---------------------------------------------------------------------------
# Step 2: Run MegaDetector (only on new images)
# ---------------------------------------------------------------------------

def run_megadetector():
    print(f"\n{'='*60}")
    print("Step 2: Running MegaDetector on new images")
    print(f"{'='*60}\n")

    all_images = sorted(
        [f for f in IMAGES_DIR.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )
    print(f"Total kea images on disk: {len(all_images)}")

    # Load existing detections (from previous runs)
    already_done = {}

    # Merge results from v1 detections file if it exists
    v1_file = BASE_DIR / "megadetector_results.json"
    if v1_file.exists():
        with open(v1_file) as f:
            v1_data = json.load(f)
        for entry in v1_data.get("images", []):
            already_done[entry["file"]] = entry
        print(f"Loaded {len(already_done)} existing detections from v1")

    # Also load from our own file if it exists
    if DETECTIONS_FILE.exists():
        with open(DETECTIONS_FILE) as f:
            our_data = json.load(f)
        for entry in our_data.get("images", []):
            already_done[entry["file"]] = entry
        print(f"Total existing detections after merge: {len(already_done)}")

    to_process = [f for f in all_images if f.name not in already_done]
    print(f"New images to process: {len(to_process)}")

    if not to_process:
        # Just save the merged results
        with open(DETECTIONS_FILE, "w") as f:
            json.dump({"images": list(already_done.values())}, f)
        print("All images already processed! Saved merged results.")
        return

    import torch
    import numpy as np
    from PIL import Image
    from megadetector.detection.run_detector import load_detector
    from megadetector.utils.ct_utils import truncate_float

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    print("Loading MegaDetector model...")
    detector = load_detector("MDV5A")
    print("Model loaded!")

    results = list(already_done.values())
    processed = 0
    errors = 0

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
            processed += 1
        except Exception as e:
            print(f"  Error: {img_path.name}: {e}")
            results.append({"file": img_path.name, "detections": []})
            errors += 1

        # Progress + periodic save
        total = processed + errors
        if total % 200 == 0:
            print(f"  Processed {total}/{len(to_process)} ({processed} ok, {errors} errors)")
            with open(DETECTIONS_FILE, "w") as f:
                json.dump({"images": results}, f)

    # Final save
    with open(DETECTIONS_FILE, "w") as f:
        json.dump({"images": results}, f, indent=2)

    total_dets = sum(len(r["detections"]) for r in results)
    print(f"\nMegaDetector complete: {len(results)} images, {total_dets} total detections")
    print(f"New: {processed} processed, {errors} errors")


# ---------------------------------------------------------------------------
# Step 3: Prepare YOLO dataset
# ---------------------------------------------------------------------------

def prepare_dataset():
    print(f"\n{'='*60}")
    print("Step 3: Preparing YOLO dataset v3")
    print(f"{'='*60}\n")

    with open(DETECTIONS_FILE) as f:
        data = json.load(f)

    ANIMAL_CATEGORY = "1"
    positives = []

    for entry in data["images"]:
        fname = entry["file"]
        img_path = IMAGES_DIR / fname
        if not img_path.exists():
            continue

        animal_dets = [
            d for d in entry["detections"]
            if d["category"] == ANIMAL_CATEGORY
            and d["conf"] >= CONFIDENCE_THRESHOLD
        ]

        if not animal_dets:
            continue

        yolo_lines = []
        for d in animal_dets:
            x_min, y_min, w, h = d["bbox"]
            x_center = max(0, min(1, x_min + w / 2))
            y_center = max(0, min(1, y_min + h / 2))
            w = max(0, min(1, w))
            h = max(0, min(1, h))
            yolo_lines.append(f"0 {x_center:.6f} {y_center:.6f} {w:.6f} {h:.6f}")

        positives.append(("kea", img_path, yolo_lines))

    print(f"Positive kea images: {len(positives)}")

    # Negatives
    negatives = []
    if NEGATIVES_DIR.exists():
        for img_path in NEGATIVES_DIR.iterdir():
            if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                negatives.append(("negative", img_path, []))

    print(f"Negative images: {len(negatives)}")

    # Combine and split
    all_samples = positives + negatives
    random.seed(42)
    random.shuffle(all_samples)

    split_idx = int(len(all_samples) * TRAIN_SPLIT)
    train_set = all_samples[:split_idx]
    val_set = all_samples[split_idx:]

    pos_train = sum(1 for s in train_set if s[0] == "kea")
    neg_train = sum(1 for s in train_set if s[0] != "kea")
    pos_val = sum(1 for s in val_set if s[0] == "kea")
    neg_val = sum(1 for s in val_set if s[0] != "kea")

    print(f"\nTrain: {len(train_set)} total ({pos_train} positive, {neg_train} negative)")
    print(f"Val:   {len(val_set)} total ({pos_val} positive, {neg_val} negative)")

    # Write files
    for split in ("train", "val"):
        (DATASET_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    def write_split(items, split_name):
        written = 0
        for _, img_path, labels in items:
            dst_name = img_path.name
            stem = img_path.stem

            dst_img = DATASET_DIR / split_name / "images" / dst_name
            if not dst_img.exists():
                shutil.copy2(img_path, dst_img)

            dst_label = DATASET_DIR / split_name / "labels" / (stem + ".txt")
            with open(dst_label, "w") as f:
                if labels:
                    f.write("\n".join(labels) + "\n")

            written += 1
            if written % 2000 == 0:
                print(f"  {split_name}: {written}/{len(items)}")

    write_split(train_set, "train")
    write_split(val_set, "val")

    yaml_content = f"""path: {DATASET_DIR.resolve().as_posix()}
train: train/images
val: val/images

names:
  0: kea
"""
    with open(DATASET_YAML, "w") as f:
        f.write(yaml_content)

    print(f"\nDataset v3 ready at: {DATASET_DIR}")


# ---------------------------------------------------------------------------
# Step 4: Train YOLOv11m
# ---------------------------------------------------------------------------

def train():
    print(f"\n{'='*60}")
    print("Step 4: Training YOLOv11m — 150 epochs")
    print(f"{'='*60}\n")

    from ultralytics import YOLO

    model = YOLO("yolo11m.pt")
    model.train(
        data=str(DATASET_YAML.resolve()),
        epochs=150,
        imgsz=640,
        batch=8,
        name="kea_detector_v3",
        project=str(BASE_DIR / "runs"),
        exist_ok=True,
        patience=30,
        save=True,
        plots=True,
        device=0,
        workers=2,
    )

    print(f"\nDone! Best model: {BASE_DIR / 'runs' / 'kea_detector_v3' / 'weights' / 'best.pt'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kea Detector v3 — Full dataset training")
    parser.add_argument(
        "step",
        choices=["download", "detect", "prepare", "train", "all"],
        help="Pipeline step to run",
    )
    args = parser.parse_args()

    if args.step in ("download", "all"):
        download_all_kea()
        download_negatives()

    if args.step in ("detect", "all"):
        run_megadetector()

    if args.step in ("prepare", "all"):
        prepare_dataset()

    if args.step in ("train", "all"):
        train()


if __name__ == "__main__":
    main()
