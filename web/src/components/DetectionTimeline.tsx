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
      <div className="animate-pulse space-y-0">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-14 border-b border-rule bg-paper" />
        ))}
      </div>
    );
  }

  if (detections.length === 0) {
    return (
      <p className="py-8 text-center font-serif text-sm italic text-muted">
        No detections yet for this stream.
      </p>
    );
  }

  return (
    <div className="flex flex-col">
      {detections.map((d, i) => {
        const conf = d.confidence ? Math.round(d.confidence * 100) : 0;
        return (
          <div
            key={d.id}
            className={`grid grid-cols-[88px_1fr_auto] items-center gap-4 px-1 py-3.5 cursor-pointer hover:bg-paper border-b border-rule ${
              i === 0 ? "border-t border-rule" : ""
            }`}
          >
            <div className="font-mono text-[11px] text-muted tracking-wide">
              <span className="block text-[9.5px] uppercase tracking-[0.14em] opacity-70 mb-0.5">
                {d.detected_at
                  ? new Date(d.detected_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                    }).toUpperCase()
                  : ""}
              </span>
              {d.detected_at
                ? new Date(d.detected_at).toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: false,
                  })
                : ""}
            </div>
            <div className="flex items-baseline gap-2.5 flex-wrap">
              <span className="font-serif text-[19px] font-medium tracking-tight text-ink">
                {d.category === "animal"
                  ? `${getSpeciesEmoji(d.common_name)} ${d.common_name || "Unknown"}`
                  : d.category === "person"
                  ? "Person"
                  : d.category === "vehicle"
                  ? "Vehicle"
                  : "No detection"}
              </span>
            </div>
            <div className="flex flex-col items-end gap-1 font-mono text-[10.5px] text-ink-2 tracking-wide">
              <span>{conf}%</span>
              <span className="h-[3px] w-[60px] overflow-hidden rounded-full bg-rule">
                <span
                  className="block h-full rounded-full bg-detect"
                  style={{ width: `${conf}%` }}
                />
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
