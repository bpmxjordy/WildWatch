"""
Retrain Kea detector with negative examples and YOLOv11m.

Adds non-kea animal images from the same NZ Trail Cams dataset as negatives.
These get empty YOLO label files so the model learns "not kea."

Usage:
    python retrain_with_negatives.py download   # Download negative images
    python retrain_with_negatives.py prepare     # Build dataset with positives + negatives
    python retrain_with_negatives.py train       # Train YOLOv11m
    python retrain_with_negatives.py all         # Run full pipeline
"""

import json
import random
import shutil
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
METADATA_FILE = BASE_DIR / "metadata.json"
IMAGES_DIR = BASE_DIR / "images" / "kea"
NEGATIVES_DIR = BASE_DIR / "images" / "negatives"
DETECTIONS_FILE = BASE_DIR / "megadetector_results.json"
DATASET_DIR = BASE_DIR / "dataset_v2"
DATASET_YAML = BASE_DIR / "kea_dataset_v2.yaml"

NZ_IMAGE_BASE = "https://storage.googleapis.com/public-datasets-lila/nz-trailcams"

KEA_CATEGORY_ID = 42
CONFIDENCE_THRESHOLD = 0.3
TRAIN_SPLIT = 0.85

NUM_NEGATIVE_ANIMALS = 2000  # non-kea animal images from same NZ dataset


def download_negative_animals(max_images=NUM_NEGATIVE_ANIMALS, workers=8):
    """Download non-kea animal images from NZ Trail Cams."""
    print(f"\n{'='*60}")
    print(f"Downloading {max_images} non-kea animal images")
    print(f"{'='*60}\n")

    NEGATIVES_DIR.mkdir(parents=True, exist_ok=True)

    with open(METADATA_FILE) as f:
        meta = json.load(f)

    # Get non-kea images — prefer species that might cause confusion
    # (other birds, similar-sized animals)
    preferred_species = [
        "kaka", "parakeet", "rosella",  # other NZ parrots
        "harrier", "robin", "tui", "bellbird", "fantail",  # other birds
        "possum", "cat", "stoat", "hedgehog",  # mammals at similar scale
        "weka", "pukeko", "takahe",  # ground birds
    ]

    non_kea = [img for img in meta["images"] if img.get("species") != "kea"]

    # Prioritise preferred species
    preferred = [img for img in non_kea if img.get("species") in preferred_species]
    other = [img for img in non_kea if img.get("species") not in preferred_species]

    random.seed(42)
    random.shuffle(preferred)
    random.shuffle(other)

    # Take as many preferred as possible, fill rest with other
    selected = preferred[:max_images]
    if len(selected) < max_images:
        selected += other[:max_images - len(selected)]

    print(f"Selected {len(selected)} non-kea images")
    from collections import Counter
    species_counts = Counter(img.get("species") for img in selected)
    for s, c in species_counts.most_common(10):
        print(f"  {s}: {c}")

    existing = {f.name for f in NEGATIVES_DIR.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")}
    to_download = []
    for img in selected:
        fname = "neg_" + img["file_name"].replace("/", "_")
        if fname not in existing:
            to_download.append((img["file_name"], fname))

    print(f"Already have {len(existing)}, downloading {len(to_download)}")

    if not to_download:
        return

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
            if (completed + failed) % 200 == 0:
                print(f"  Progress: {completed + failed}/{len(to_download)}")

    print(f"Downloaded {completed}, failed {failed}")


def prepare_dataset():
    """Build YOLO dataset with kea positives + negatives."""
    print(f"\n{'='*60}")
    print("Preparing dataset v2 with negatives")
    print(f"{'='*60}\n")

    # --- Positive kea images (with bounding boxes from MegaDetector) ---
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

    # --- Negative images (empty label files) ---
    negatives = []

    # Non-kea animals
    if NEGATIVES_DIR.exists():
        for img_path in NEGATIVES_DIR.iterdir():
            if img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                negatives.append(("negative", img_path, []))
    print(f"Non-kea animal negatives: {len([n for n in negatives if 'neg_' in n[1].name])}")

    print(f"Total negatives: {len(negatives)}")

    # --- Combine and split ---
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

    print(f"\nTrain: {len(train_set)} ({pos_train} positive, {neg_train} negative)")
    print(f"Val:   {len(val_set)} ({pos_val} positive, {neg_val} negative)")

    # --- Write files ---
    for split in ("train", "val"):
        (DATASET_DIR / split / "images").mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / split / "labels").mkdir(parents=True, exist_ok=True)

    def write_split(items, split_name):
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
                # Empty file for negatives — YOLO treats as background

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

    print(f"\nDataset v2 ready at: {DATASET_DIR}")


def train():
    """Train YOLOv11m."""
    print(f"\n{'='*60}")
    print("Training YOLOv11m (medium)")
    print(f"{'='*60}\n")

    from ultralytics import YOLO

    model = YOLO("yolo11m.pt")
    model.train(
        data=str(DATASET_YAML.resolve()),
        epochs=100,
        imgsz=640,
        batch=8,  # smaller batch for medium model on 8GB VRAM
        name="kea_detector_v2",
        project=str(BASE_DIR / "runs"),
        exist_ok=True,
        patience=20,
        save=True,
        plots=True,
        device=0,
        workers=2,
    )

    print(f"\nDone! Best model: {BASE_DIR / 'runs' / 'kea_detector_v2' / 'weights' / 'best.pt'}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Retrain Kea detector with negatives (YOLOv11m)")
    parser.add_argument(
        "step",
        choices=["download", "prepare", "train", "all"],
        help="Pipeline step to run",
    )
    args = parser.parse_args()

    if args.step in ("download", "all"):
        download_negative_animals()
    if args.step in ("prepare", "all"):
        prepare_dataset()
    if args.step in ("train", "all"):
        train()


if __name__ == "__main__":
    main()
