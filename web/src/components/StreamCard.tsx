import Link from "next/link";
import type { Stream, Detection } from "@/lib/supabase/types";
import { STREAM_WILDLIFE_CATEGORY, WILDLIFE_CATEGORIES } from "@/lib/constants";
import DetectionBadge from "./DetectionBadge";
import StatusDot from "./StatusDot";
import BoundingBoxOverlay from "./BoundingBoxOverlay";

interface StreamCardProps {
  stream: Stream;
  detections?: Detection[];
}

export default function StreamCard({ stream, detections = [] }: StreamCardProps) {
  const thumbnailUrl =
    stream.latest_detection_thumbnail_url ||
    stream.thumbnail_url ||
    "/placeholder-stream.jpg";

  const wildlifeCat = STREAM_WILDLIFE_CATEGORY[stream.slug];
  const catInfo = wildlifeCat ? WILDLIFE_CATEGORIES[wildlifeCat] : null;

  return (
    <Link
      href={`/stream/${stream.slug}`}
      className="group block cursor-pointer"
    >
      <div className="relative aspect-video overflow-hidden rounded bg-paper-2 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_1px_2px_rgba(0,0,0,0.04),0_6px_18px_rgba(0,0,0,0.05)]">
        <img
          src={thumbnailUrl}
          alt={stream.name}
          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />
        {detections.map((d) => (
          <BoundingBoxOverlay key={d.id} detection={d} showLabel={false} />
        ))}
        <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-3">
          <div className="flex items-start justify-between gap-2">
            <StatusDot
              category={stream.latest_detection_category}
              detectedAt={stream.latest_detection_at}
              isLive={stream.is_live}
            />
            <DetectionBadge
              category={stream.latest_detection_category}
              commonName={stream.latest_detection_common_name}
              confidence={stream.latest_detection_confidence}
              detectedAt={stream.latest_detection_at}
            />
          </div>
          <div className="flex items-end justify-between gap-2">
            {catInfo && (
              <span className="rounded-sm bg-black/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-white/80 backdrop-blur-sm">
                {catInfo.emoji} {catInfo.label}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-start justify-between gap-3 px-0.5 pt-3">
        <div>
          <h3 className="font-serif text-lg font-medium leading-tight tracking-tight text-ink">
            {stream.name}
          </h3>
          {stream.location_name && (
            <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
              {stream.location_name}
            </p>
          )}
        </div>
      </div>
    </Link>
  );
}
