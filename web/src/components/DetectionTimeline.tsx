"use client";

import type { Detection } from "@/lib/supabase/types";
import { getSpeciesEmoji, timeAgo, confidencePercent } from "@/lib/utils";

interface DetectionTimelineProps {
  detections: Detection[];
  loading: boolean;
}

export default function DetectionTimeline({ detections, loading }: DetectionTimelineProps) {
  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 rounded-lg bg-gray-800" />
        ))}
      </div>
    );
  }

  if (detections.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-gray-500">
        No detections yet for this stream.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {detections.map((d) => (
        <div
          key={d.id}
          className="flex items-center gap-3 rounded-lg border border-gray-800 bg-gray-900 px-3 py-2"
        >
          <span className="text-lg">
            {d.category === "animal"
              ? getSpeciesEmoji(d.common_name)
              : d.category === "person"
              ? "👤"
              : d.category === "vehicle"
              ? "🚗"
              : "⬜"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-white">
              {d.common_name || d.category}
            </p>
            <p className="text-xs text-gray-500">
              {confidencePercent(d.confidence)} confidence
            </p>
          </div>
          <span className="whitespace-nowrap text-xs text-gray-500">
            {timeAgo(d.detected_at)}
          </span>
        </div>
      ))}
    </div>
  );
}
