"use client";

import { useEffect, useCallback } from "react";
import type { Detection } from "@/lib/supabase/types";
import BoundingBoxOverlay from "./BoundingBoxOverlay";

interface DetectionLightboxProps {
  detection: Detection | null;
  allDetections?: Detection[];
  onClose: () => void;
}

export default function DetectionLightbox({
  detection,
  allDetections = [],
  onClose,
}: DetectionLightboxProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (!detection) return;
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [detection, handleKeyDown]);

  if (!detection) return null;

  const sameFrame = allDetections.filter(
    (d) =>
      d.thumbnail_path === detection.thumbnail_path &&
      d.thumbnail_path != null &&
      d.confidence >= 0.8
  );
  const detectionsToShow = sameFrame.length > 0 ? sameFrame : (detection.confidence >= 0.8 ? [detection] : []);

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-h-[90vh] max-w-[90vw] overflow-hidden rounded-lg bg-paper shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-black/50 text-white/80 transition-colors hover:bg-black/70 hover:text-white"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Image with bounding boxes */}
        <div className="relative">
          <img
            src={detection.thumbnail_path!}
            alt={detection.common_name || "Detection"}
            className="max-h-[80vh] max-w-[90vw] object-contain"
          />
          {detectionsToShow.map((d) => (
            <BoundingBoxOverlay key={d.id} detection={d} showLabel />
          ))}
        </div>

        {/* Info bar */}
        <div className="flex items-center justify-between border-t border-rule bg-paper px-5 py-3">
          <div className="flex items-center gap-3">
            {detection.common_name && (
              <span className="rounded-sm bg-detect px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider text-[#1a2e1a]">
                {detection.common_name}
              </span>
            )}
            {detection.confidence != null && (
              <span className="font-mono text-[11px] text-muted">
                {Math.round(detection.confidence * 100)}% confidence
              </span>
            )}
          </div>
          {detection.detected_at && (
            <span className="font-mono text-[10px] tracking-wide text-muted">
              {new Date(detection.detected_at).toLocaleString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
              })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
