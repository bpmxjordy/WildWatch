"use client";

import type { Detection } from "@/lib/supabase/types";

interface BoundingBoxOverlayProps {
  detection: Detection;
  showLabel?: boolean;
}

const COLORS = [
  "rgba(80, 122, 66, 0.85)",
  "rgba(13, 148, 136, 0.85)",
  "rgba(21, 101, 192, 0.85)",
  "rgba(106, 27, 154, 0.85)",
  "rgba(173, 20, 87, 0.85)",
  "rgba(230, 81, 0, 0.85)",
];

export default function BoundingBoxOverlay({
  detection,
  showLabel = true,
}: BoundingBoxOverlayProps) {
  const { bbox_x1, bbox_y1, bbox_x2, bbox_y2 } = detection;
  if (bbox_x1 == null || bbox_y1 == null || bbox_x2 == null || bbox_y2 == null)
    return null;
  if (bbox_x1 === 0 && bbox_y1 === 0 && bbox_x2 === 1 && bbox_y2 === 1)
    return null;

  const colorIdx =
    (detection.common_name?.charCodeAt(0) ?? 0) % COLORS.length;
  const color = COLORS[colorIdx];

  const left = `${bbox_x1 * 100}%`;
  const top = `${bbox_y1 * 100}%`;
  const width = `${(bbox_x2 - bbox_x1) * 100}%`;
  const height = `${(bbox_y2 - bbox_y1) * 100}%`;

  return (
    <div
      className="pointer-events-none absolute"
      style={{ left, top, width, height }}
    >
      <div
        className="absolute inset-0 rounded-[1px]"
        style={{ border: `2px solid ${color}` }}
      />
      {showLabel && detection.common_name && (
        <span
          className="absolute -top-[18px] left-0 whitespace-nowrap rounded-sm px-1 py-px font-mono text-[8px] font-semibold uppercase tracking-wider text-white"
          style={{ backgroundColor: color }}
        >
          {detection.common_name}{" "}
          {detection.confidence != null &&
            `${Math.round(detection.confidence * 100)}%`}
        </span>
      )}
    </div>
  );
}
