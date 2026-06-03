# Kea Detection Model — Training Documentation

## Overview

This directory contains the training pipeline and model weights for a **YOLOv11-based kea (*Nestor notabilis*) detection model**, developed as part of the WildWatch wildlife monitoring system. The model detects and localises kea — New Zealand's endangered alpine parrot — in camera trap imagery and video footage.

The core challenge was that the source dataset provides **image-level classification labels only** (i.e., "this image contains a kea") with **no bounding box annotations**. To overcome this, we employed a two-stage auto-labelling pipeline using Microsoft's MegaDetector to generate bounding boxes, which were then used to train a YOLOv11 object detection model.

---

## Dataset

### Source: NZ Trail Camera Images of New Zealand Animals

- **Publisher**: New Zealand Department of Conservation (DOC)
- **URL**: https://lila.science/datasets/nz-trailcams
- **Total images**: ~2.5 million across 97 species
- **Kea images**: 54,790
- **Annotation format**: COCO Camera Traps JSON (image-level species labels, no bounding boxes)
- **Licence**: Community Data License Agreement (permissive variant)
- **Contact**: Joris Tinnemans, DOC (jtinnemans@doc.govt.nz)

### Dataset Characteristics

The images are sourced from trail cameras (camera traps) deployed across New Zealand conservation areas. They exhibit typical trail camera properties:

- Fixed camera positions, predominantly forest/bush environments
- Mix of daytime colour and night-time infrared imagery
- Variable image quality (motion blur, partial occlusion, distance variation)
- Single-species labels per image (no multi-label annotations)

### Kea Category

- **Category ID**: 42
- **Category name**: `kea`
- **Total annotated images**: 54,790
- **Metadata fields per image**: `file_name`, `id`, `location`, `datetime`, `project`, `species`

---

## Auto-Labelling Pipeline

Since the dataset lacks bounding box annotations, we used **MegaDetector v5a** to automatically generate bounding boxes on all kea-labelled images.

### MegaDetector v5a

- **Model**: MegaDetector v5a (MDV5A) — a YOLOv5-based general-purpose animal detector
- **Source**: https://github.com/agentmorris/MegaDetector
- **Package version**: `megadetector==10.0.21`
- **Detection categories**: 1 = animal, 2 = person, 3 = vehicle
- **Output format**: Normalised bounding boxes `[x_min, y_min, width, height]` with confidence scores

### Auto-Labelling Process

1. Each kea-labelled image was passed through MegaDetector
2. Only detections with `category == "1"` (animal) were retained
3. Detections below a confidence threshold were discarded
4. All retained animal detections were relabelled as class `0` (kea), since the source images are known to contain kea
5. Bounding boxes were converted from MegaDetector format `[x_min, y_min, w, h]` to YOLO format `[x_center, y_center, w, h]` (all normalised 0–1)

### Assumption & Limitation

This approach assumes that every animal detected by MegaDetector in a kea-labelled image is indeed a kea. This is a reasonable assumption for camera trap images where a single species triggers the camera, but may introduce label noise in images containing multiple species or where MegaDetector detects non-kea objects (e.g., vegetation movement).

---

## Model Versions

Three model versions were trained iteratively, each addressing limitations discovered in the previous version.

### v1 — Baseline (YOLOv11n)

| Parameter | Value |
|---|---|
| **Architecture** | YOLOv11n (nano) — 2.59M parameters, 6.4 GFLOPs |
| **Base weights** | `yolo11n.pt` (COCO pretrained) |
| **Training images** | 5,000 kea (random subset) |
| **Negative images** | 0 |
| **MegaDetector threshold** | 0.3 |
| **Train/Val split** | 85% / 15% (4,053 / 716 images) |
| **Epochs** | 100 |
| **Image size** | 640px |
| **Batch size** | 16 |
| **Optimizer** | Auto (SGD) |
| **Learning rate** | 0.01 (initial), 0.01 (final ratio) |
| **Hardware** | NVIDIA GeForce RTX 3070 (8GB VRAM) |

#### v1 Results (Epoch 100)

| Metric | Value |
|---|---|
| Precision | 0.977 |
| Recall | 0.965 |
| mAP@50 | 0.983 |
| mAP@50-95 | 0.883 |
| Train box_loss | 0.393 |
| Val box_loss | 0.493 |

#### v1 Observations

- Strong performance on trail camera imagery (in-domain)
- **High false positive rate on out-of-domain imagery** — the model detected non-kea objects (e.g., plastic cups, rocks) as kea with high confidence, because it was never trained on negative examples
- Inference speed: ~14ms per frame on RTX 3070 (GPU)

### v2 — With Negative Examples (YOLOv11m)

| Parameter | Value |
|---|---|
| **Architecture** | YOLOv11m (medium) — 20.1M parameters |
| **Base weights** | `yolo11m.pt` (COCO pretrained) |
| **Training images** | 5,000 kea (same subset as v1) |
| **Negative images** | 2,000 non-kea animals from same NZ Trail Cams dataset |
| **Negative species** | Prioritised confusable species: kaka, parakeet, rosella (other NZ parrots); harrier, robin, tui, bellbird, fantail (other birds); possum, cat, stoat, hedgehog (mammals); weka, pukeko, takahe (ground birds) |
| **MegaDetector threshold** | 0.3 |
| **Train/Val split** | 85% / 15% (~5,754 / ~1,015 images) |
| **Epochs** | 100 |
| **Image size** | 640px |
| **Batch size** | 8 |
| **Hardware** | NVIDIA GeForce RTX 3070 (8GB VRAM) |

#### v2 Results (Epoch 100)

| Metric | Value |
|---|---|
| Precision | 0.965 |
| Recall | 0.960 |
| mAP@50 | 0.978 |
| mAP@50-95 | 0.902 |
| Train box_loss | 0.342 |
| Val box_loss | 0.365 |

#### v2 Confusion Matrix

|  | Predicted: kea | Predicted: background |
|---|---|---|
| **Actual: kea** | 775 | 30 |
| **Actual: background** | 42 | — |

- 96% recall (775/805 true kea detected)
- 42 false positives on background images (reduced from v1)

#### v2 Observations

- Significantly reduced false positives compared to v1
- Negative examples from the same dataset ensured terrain/camera consistency
- The val/cls_loss exhibited a large spike (~25) around epochs 5–10 as the model initially struggled with the new "not everything is kea" signal, but recovered fully
- **On out-of-domain footage (YouTube video)**, the model showed lower confidence scores compared to v1, causing some true detections to fall below the inference threshold (conf=0.25). This is a confidence calibration effect — the model is more discriminating, not less capable
- The larger architecture (medium vs nano) did not fully compensate for the limited training data (5,000 images)

### v3 — Full Dataset (YOLOv11m) *[In Training]*

| Parameter | Value |
|---|---|
| **Architecture** | YOLOv11m (medium) — 20.1M parameters |
| **Base weights** | `yolo11m.pt` (COCO pretrained) |
| **Training images** | 54,790 kea (full dataset) |
| **Negative images** | 2,000 non-kea animals from same NZ Trail Cams dataset |
| **MegaDetector threshold** | 0.3 |
| **Train/Val split** | 85% / 15% |
| **Epochs** | 150 |
| **Image size** | 640px |
| **Batch size** | 8 |
| **Patience** | 30 (early stopping) |
| **Hardware** | Remote training machine |

#### v3 Rationale

- Using the full 54,790 kea images (11x more than v1/v2) provides the model with far greater variety in poses, lighting conditions, camera angles, and environmental contexts
- Training for 150 epochs (vs 100) allows the model more time to converge on the larger dataset
- Expected improvements: higher confidence on true detections across both in-domain (trail cam) and out-of-domain (video) imagery

---

## Training Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    NZ Trail Cams Dataset                  │
│              (COCO Camera Traps JSON format)              │
│         54,790 kea images (image-level labels)           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               Step 1: Image Download                     │
│    Download from Google Cloud Storage (GCP bucket)       │
│    gs://public-datasets-lila/nz-trailcams               │
│    Multi-threaded (12 workers)                           │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│          Step 2: MegaDetector v5a Inference               │
│    Auto-generate bounding boxes on all kea images        │
│    Filter: category == "animal", conf >= 0.3             │
│    Output: [x_min, y_min, width, height] normalised      │
│    Incremental: skips previously processed images        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│          Step 3: YOLO Format Conversion                   │
│    Convert bbox: [x_min,y_min,w,h] → [x_ctr,y_ctr,w,h] │
│    Label all animal detections as class 0 (kea)          │
│    Add negative images with empty label files            │
│    Split 85% train / 15% val (seeded shuffle)            │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│             Step 4: YOLOv11 Training                      │
│    Ultralytics YOLOv11 with COCO pretrained weights      │
│    Transfer learning (448/499 layers transferred)        │
│    AMP (Automatic Mixed Precision) enabled               │
│    Augmentation: mosaic, fliplr, HSV jitter, erasing     │
└─────────────────────────────────────────────────────────┘
```

---

## Hyperparameters (Common Across All Versions)

| Category | Parameter | Value |
|---|---|---|
| **Optimizer** | Type | Auto (SGD with momentum) |
| | Initial LR | 0.01 |
| | Final LR ratio | 0.01 |
| | Momentum | 0.937 |
| | Weight decay | 0.0005 |
| | Warmup epochs | 3.0 |
| | Warmup momentum | 0.8 |
| **Loss weights** | Box loss | 7.5 |
| | Classification loss | 0.5 |
| | DFL (Distribution Focal Loss) | 1.5 |
| **Augmentation** | Mosaic | 1.0 |
| | Horizontal flip | 0.5 |
| | HSV hue | 0.015 |
| | HSV saturation | 0.7 |
| | HSV value | 0.4 |
| | Scale | 0.5 |
| | Translation | 0.1 |
| | Erasing | 0.4 |
| | Close mosaic (last N epochs) | 10 |
| **Training** | Image size | 640x640 |
| | IoU threshold (NMS) | 0.7 |
| | Max detections | 300 |
| | AMP | Enabled |
| | Deterministic | True |
| | Seed | 0 |

---

## Software Dependencies

| Package | Version | Purpose |
|---|---|---|
| Python | 3.11.9 | Runtime |
| PyTorch | 2.11.0+cu128 | Deep learning framework |
| Ultralytics | 8.4.26 | YOLOv11 training and inference |
| MegaDetector | 10.0.21 | Auto-labelling (bounding box generation) |
| OpenCV | 4.11.0 | Image processing |
| Pillow | 12.2.0 | Image I/O |
| NumPy | 2.4.4 | Array operations |
| CUDA | 12.8 | GPU acceleration |

---

## File Structure

```
tools/kea_training/
├── train_kea_detector.py      # v1 training pipeline (5K images, no negatives)
├── retrain_with_negatives.py  # v2 training pipeline (5K images + 2K negatives)
├── train_v3_full.py           # v3 training pipeline (54.8K images + 2K negatives)
├── test_video.py              # Video inference test (YouTube URL → annotated video)
├── bbox_viewer.py             # Web-based bounding box viewer (localhost:8501)
├── requirements.txt           # Python dependencies
├── categories.json            # All 97 species categories from NZ Trail Cams
├── kea_dataset.yaml           # YOLO dataset config (v1)
├── kea_dataset_v2.yaml        # YOLO dataset config (v2)
├── kea_dataset_v3.yaml        # YOLO dataset config (v3)
├── runs/
│   ├── kea_detector/          # v1 model outputs
│   │   ├── weights/best.pt    # Best v1 model weights
│   │   ├── results.csv        # Per-epoch metrics
│   │   ├── results.png        # Training curves
│   │   ├── confusion_matrix.png
│   │   └── ...
│   ├── kea_detector_v2/       # v2 model outputs
│   │   ├── weights/best.pt    # Best v2 model weights
│   │   └── ...
│   └── kea_detector_v3/       # v3 model outputs (when complete)
│       └── weights/best.pt
├── images/                    # (gitignored) Downloaded images
│   ├── kea/                   # Kea positive images
│   └── negatives/             # Non-kea negative images
├── dataset_v*/                # (gitignored) YOLO-formatted datasets
├── metadata.json              # (gitignored, auto-downloaded) NZ Trail Cams metadata
└── megadetector_results*.json # (gitignored) MegaDetector detection outputs
```

---

## Key Design Decisions

### 1. Auto-Labelling with MegaDetector

**Problem**: The NZ Trail Cams dataset provides only image-level species labels with no bounding box annotations, which are required for object detection training.

**Solution**: MegaDetector v5a, a general-purpose animal detector trained on millions of camera trap images, was used to generate bounding boxes. Since the source images are pre-labelled as containing kea, all MegaDetector "animal" detections were relabelled as kea.

**Trade-off**: This introduces some label noise (MegaDetector may occasionally box vegetation or non-kea animals), but eliminates the need for manual annotation of thousands of images.

### 2. Confidence Threshold for Auto-Labels (0.3)

A MegaDetector confidence threshold of 0.3 was used to filter detections. Analysis showed:
- >= 0.3: 4,769 images with detections
- >= 0.5: 4,707 images (loss of 62 images)
- >= 0.7: 4,531 images (loss of 238 images)

The 0.3 threshold maximised data retention while excluding clearly spurious detections.

### 3. Negative Example Selection Strategy

Rather than using generic empty images from a different dataset (e.g., Caltech Camera Traps, which features Californian terrain), negatives were sourced from the **same NZ Trail Cams dataset**. This ensures:
- Same camera types and image characteristics
- Same terrain and environmental contexts
- Species prioritised by visual similarity to kea (other NZ parrots first, then other birds, then mammals)

### 4. Iterative Model Development

The three-version approach allowed systematic evaluation:
- **v1**: Established baseline detection capability
- **v2**: Addressed false positive problem with hard negative mining
- **v3**: Addressed confidence calibration by scaling to the full dataset

---

## Inference

### Single Image

```python
from ultralytics import YOLO

model = YOLO("runs/kea_detector_v2/weights/best.pt")
results = model.predict("image.jpg", conf=0.25)

for r in results:
    for box in r.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        confidence = box.conf[0].item()
        print(f"Kea detected: ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f}) conf={confidence:.2f}")
```

### Video

```bash
python test_video.py URL --model v2 --conf 0.25
python test_video.py URL --model v3 --start 1:26 --end 1:32
```

---

## Limitations & Future Work

1. **Domain gap**: Models trained on trail camera imagery show reduced confidence on cinematic/YouTube footage due to differences in angle, resolution, lighting, and background
2. **Single-class detection**: The model only detects "kea" — it cannot distinguish between individual kea or differentiate kea from visually similar species (e.g., kaka) without additional training
3. **Auto-label noise**: MegaDetector-generated bounding boxes may not perfectly align with kea outlines, introducing some localisation noise into training labels
4. **No tracking**: Frame-by-frame detection without temporal tracking means the same kea is detected independently in each frame — no identity persistence across frames

### Potential Improvements

- Fine-tune on manually annotated YouTube/video frames to bridge the domain gap
- Train at higher resolution (1280px) for better detection of distant/small kea
- Add temporal tracking (e.g., ByteTrack, BoTSORT) for video applications
- Expand to multi-class detection (kea vs kaka vs other parrots)
- Apply test-time augmentation (TTA) for higher-stakes inference scenarios

---

## References

- Tinnemans, J. et al. "Trail Camera Images of New Zealand Animals." LILA Science, 2024. https://lila.science/datasets/nz-trailcams
- Beery, S., Morris, D., & Yang, S. "Efficient Pipeline for Camera Trap Image Review." arXiv:1907.06772, 2019. (MegaDetector)
- Jocher, G. et al. "Ultralytics YOLO11." https://docs.ultralytics.com, 2024.
- Redmon, J. & Farhadi, A. "You Only Look Once: Unified, Real-Time Object Detection." CVPR, 2016.
