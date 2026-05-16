"use client";

import type { Detection } from "@/lib/supabase/types";

interface SnapshotGalleryProps {
  detections: Detection[];
}

export default function SnapshotGallery({ detections }: SnapshotGalleryProps) {
  const withThumbnails = detections.filter((d) => d.thumbnail_path);

  if (withThumbnails.length === 0) {
    return (
      <p className="py-8 text-center font-serif text-sm italic text-muted">
        No snapshots available yet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2.5">
      {withThumbnails.map((d) => (
        <div
          key={d.id}
          className="relative aspect-[4/3] cursor-pointer overflow-hidden rounded-sm bg-paper-2 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_1px_2px_rgba(0,0,0,0.04),0_6px_18px_rgba(0,0,0,0.05)]"
        >
          <img
            src={d.thumbnail_path!}
            alt={d.common_name || "Detection snapshot"}
            className="h-full w-full object-cover"
            loading="lazy"
          />
          {d.common_name && (
            <span className="absolute right-1 top-1 rounded-sm bg-detect px-1.5 py-0.5 font-mono text-[8.5px] uppercase tracking-wider text-[#1a2e1a]">
              {d.common_name}
            </span>
          )}
          {d.detected_at && (
            <span className="absolute bottom-1 left-1 rounded-sm bg-black/50 px-1.5 py-0.5 font-mono text-[9px] tracking-wide text-white">
              {new Date(d.detected_at).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
              })}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
