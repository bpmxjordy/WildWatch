import Link from "next/link";
import type { Stream } from "@/lib/supabase/types";
import DetectionBadge from "./DetectionBadge";
import StatusDot from "./StatusDot";

interface StreamCardProps {
  stream: Stream;
}

export default function StreamCard({ stream }: StreamCardProps) {
  const thumbnailUrl =
    stream.latest_detection_thumbnail_url ||
    stream.thumbnail_url ||
    "/placeholder-stream.jpg";

  return (
    <Link
      href={`/stream/${stream.slug}`}
      className="group block overflow-hidden rounded-xl border border-gray-800 bg-gray-900 transition-all hover:border-gray-600 hover:shadow-lg hover:shadow-green-900/10"
    >
      <div className="relative aspect-video overflow-hidden bg-gray-800">
        <img
          src={thumbnailUrl}
          alt={stream.name}
          className="h-full w-full object-cover transition-transform group-hover:scale-105"
          loading="lazy"
        />
        <div className="absolute right-2 top-2">
          <StatusDot
            category={stream.latest_detection_category}
            detectedAt={stream.latest_detection_at}
            isLive={stream.is_live}
          />
        </div>
      </div>
      <div className="p-3">
        <h3 className="mb-1 text-sm font-semibold text-white truncate">
          {stream.name}
        </h3>
        {stream.location_name && (
          <p className="mb-2 text-xs text-gray-500 truncate">
            📍 {stream.location_name}
          </p>
        )}
        <DetectionBadge
          category={stream.latest_detection_category}
          commonName={stream.latest_detection_common_name}
          confidence={stream.latest_detection_confidence}
          detectedAt={stream.latest_detection_at}
        />
      </div>
    </Link>
  );
}
