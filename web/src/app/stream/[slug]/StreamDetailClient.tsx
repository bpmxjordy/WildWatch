"use client";

import Link from "next/link";
import type { Stream, Detection } from "@/lib/supabase/types";
import StreamPlayer from "@/components/StreamPlayer";
import DetectionBadge from "@/components/DetectionBadge";
import DetectionTimeline from "@/components/DetectionTimeline";
import SnapshotGallery from "@/components/SnapshotGallery";
import ActivityMonitor from "@/components/ActivityMonitor";
import SpeciesBreakdown from "@/components/SpeciesBreakdown";

interface Props {
  stream: Stream;
  detections: Detection[];
}

export default function StreamDetailClient({ stream, detections }: Props) {
  return (
    <div>
      <Link
        href="/"
        className="mb-5 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.16em] text-muted hover:text-ink transition-colors"
      >
        &#9666; All cameras
      </Link>

      <div className="mb-5 flex items-end justify-between gap-8">
        <div>
          <span className="mb-2 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-accent-deep before:inline-block before:h-px before:w-4 before:bg-accent-deep">
            {stream.location_name || "Live Feed"}
          </span>
          <h1 className="font-serif text-[clamp(36px,4vw,60px)] font-medium leading-none tracking-tight text-ink">
            {stream.name}
          </h1>
        </div>
      </div>

      <div className="relative mb-5 aspect-video overflow-hidden rounded-md bg-paper-2 shadow-[0_1px_0_rgba(255,255,255,0.6)_inset,0_14px_44px_rgba(0,0,0,0.14)]">
        <StreamPlayer
          embedUrl={stream.embed_url}
          name={stream.name}
          thumbnailUrl={stream.latest_detection_thumbnail_url || stream.thumbnail_url}
          platform={stream.platform}
          sourceUrl={stream.source_url}
        />
      </div>

      {stream.description && (
        <div className="border-y border-rule py-5 mb-9">
          <div className="grid gap-9 lg:grid-cols-[1.4fr_1fr]">
            <p className="max-w-[60ch] text-[15.5px] leading-relaxed text-ink-2">
              {stream.description}
            </p>
            <div className="flex items-center">
              <DetectionBadge
                category={stream.latest_detection_category}
                commonName={stream.latest_detection_common_name}
                confidence={stream.latest_detection_confidence}
                detectedAt={stream.latest_detection_at}
              />
            </div>
          </div>
        </div>
      )}

      {/* Camera Analytics */}
      <div className="mb-5 flex items-baseline justify-between border-b border-rule pb-3.5">
        <h2 className="font-serif text-[26px] font-medium tracking-tight text-ink">
          Camera analytics
        </h2>
        <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
          Automated · Last 7 days
        </span>
      </div>

      <div className="grid gap-10 lg:grid-cols-[1.45fr_1fr] mb-12">
        <ActivityMonitor streamId={stream.id} longitude={stream.longitude} />
        <SpeciesBreakdown streamId={stream.id} />
      </div>

      <div className="mb-5 flex items-baseline justify-between border-b border-rule pb-3.5">
        <h2 className="font-serif text-[26px] font-medium tracking-tight text-ink">
          Recent detections
        </h2>
        <span className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
          Last 24 hours
        </span>
      </div>

      <div className="grid gap-9 lg:grid-cols-2">
        <div>
          <DetectionTimeline detections={detections} loading={false} />
        </div>
        <div>
          <SnapshotGallery detections={detections} />
        </div>
      </div>
    </div>
  );
}
