from __future__ import annotations

import logging

from PIL import Image, ImageDraw, ImageFont

from inference.base import DetectionResult

logger = logging.getLogger(__name__)

COLORS = [
    (46, 125, 50), (0, 121, 107), (21, 101, 192), (106, 27, 154),
    (173, 20, 87), (230, 81, 0), (62, 39, 35), (38, 50, 56),
]


def draw_detections(image_path: str, detections: list[DetectionResult], output_path: str) -> str:
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for i, det in enumerate(detections):
        color = COLORS[i % len(COLORS)]
        x1 = int(det.bbox_x1 * w)
        y1 = int(det.bbox_y1 * h)
        x2 = int(det.bbox_x2 * w)
        y2 = int(det.bbox_y2 * h)

        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)

        label = f"{det.class_name} {det.confidence:.0%}"
        bbox = font.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        label_y = max(y1 - th - 6, 0)
        draw.rectangle([x1, label_y, x1 + tw + 8, label_y + th + 6], fill=color)
        draw.text((x1 + 4, label_y + 2), label, fill="white", font=font)

    img.save(output_path, quality=90)
    return output_path
