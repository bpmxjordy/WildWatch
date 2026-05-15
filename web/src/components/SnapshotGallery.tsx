"use client";

import type { Detection } from "@/lib/supabase/types";

interface SnapshotGalleryProps {
  detections: Detection[];
}

export default function SnapshotGallery({ detections }: SnapshotGalleryProps) {
  const withThumbnails = detections.filter((d) => d.thumbnail_path);

  if (withThumbnails.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No snapshots available yet.
      </p>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      {withThumbnails.map((d) => (
        <div
          key={d.id}
          className="group relative aspect-video overflow-hidden rounded-lg bg-gray-800"
        >
          <img
            src={d.thumbnail_path!}
            alt={d.common_name || "Detection snapshot"}
            className="h-full w-full object-cover"
            loading="lazy"
          />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent p-2">
            <p className="text-xs font-medium text-white truncate">
              {d.common_name || d.category}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
