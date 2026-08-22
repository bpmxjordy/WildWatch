"use client";

import { useState } from "react";
import type { Detection } from "@/lib/supabase/types";
import DetectionLightbox from "./DetectionLightbox";

interface SnapshotGalleryProps {
  detections: Detection[];
}

export default function SnapshotGallery({ detections }: SnapshotGalleryProps) {
  const [selected, setSelected] = useState<Detection | null>(null);
  const withThumbnails = detections.filter((d) => d.thumbnail_path);

  if (withThumbnails.length === 0) {
    return (
      <p className="py-8 text-center font-serif text-sm italic text-muted">
        No snapshots available yet.
      </p>
    );
  }

  // Group detections by thumbnail for frame list
  const byThumbnail = new Map<string, Detection[]>();
  withThumbnails.forEach((d) => {
    const key = d.thumbnail_path!;
    if (!byThumbnail.has(key)) byThumbnail.set(key, []);
    byThumbnail.get(key)!.push(d);
  });
  const uniqueFrames = Array.from(byThumbnail.entries());

  return (
    <>
      <div className="grid grid-cols-3 gap-2.5">
        {uniqueFrames.map(([thumb, frameDets]) => {
          const primary = frameDets[0];
          return (
            <div
              key={thumb}
              onClick={() => setSelected(primary)}
              className="group relative aspect-[4/3] cursor-pointer overflow-hidden rounded-sm bg-paper-2 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_1px_2px_rgba(0,0,0,0.04),0_6px_18px_rgba(0,0,0,0.05)] transition-shadow hover:shadow-[0_8px_24px_rgba(0,0,0,0.12)]"
            >
              {/* Detection rows are kept for a year but snapshots are pruned
                  after IMAGE_TTL_DAYS, so older rows point at objects that no
                  longer exist. Degrade to a caption rather than a broken image
                  icon and its alt text. */}
              <img
                src={thumb}
                alt={primary.common_name || "Detection snapshot"}
                className="h-full w-full object-cover transition-transform duration-200 group-hover:scale-[1.03]"
                loading="lazy"
                onError={(e) => {
                  const img = e.currentTarget;
                  img.style.display = "none";
                  img.parentElement?.classList.add("snapshot-expired");
                }}
              />
              <span className="pointer-events-none absolute inset-0 hidden items-center justify-center px-2 text-center font-serif text-[12px] italic text-muted [.snapshot-expired_&]:flex">
                Snapshot expired
              </span>
              {/* Expand icon on hover */}
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/20">
                <svg
                  className="h-6 w-6 text-white opacity-0 drop-shadow transition-opacity group-hover:opacity-80"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                </svg>
              </div>
              {primary.common_name && (
                <span className="absolute right-1 top-1 rounded-sm bg-detect px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-wider text-[#1a2e1a]">
                  {primary.common_name}
                </span>
              )}
              {frameDets.length > 1 && (
                <span className="absolute left-1 top-1 rounded-sm bg-black/50 px-1.5 py-0.5 font-mono text-[8.5px] tracking-wider text-white">
                  {frameDets.length} detections
                </span>
              )}
              {primary.detected_at && (
                <span className="absolute bottom-1 left-1 rounded-sm bg-black/50 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-white">
                  {new Date(primary.detected_at).toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  })}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <DetectionLightbox
        detection={selected}
        allDetections={withThumbnails}
        onClose={() => setSelected(null)}
      />
    </>
  );
}
