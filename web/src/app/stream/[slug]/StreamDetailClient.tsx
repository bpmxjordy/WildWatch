"use client";

import Link from "next/link";
import type { Stream } from "@/lib/supabase/types";
import { useStreamDetections } from "@/hooks/useStreamDetections";
import StreamPlayer from "@/components/StreamPlayer";
import DetectionBadge from "@/components/DetectionBadge";
import DetectionTimeline from "@/components/DetectionTimeline";
import SnapshotGallery from "@/components/SnapshotGallery";

interface Props {
  stream: Stream;
}

export default function StreamDetailClient({ stream }: Props) {
  const { detections, loading } = useStreamDetections(stream.id);

  return (
    <div>
      <Link
        href="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-gray-400 hover:text-white"
      >
        ← Back to streams
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">{stream.name}</h1>
        {stream.location_name && (
          <p className="mt-1 text-sm text-gray-400">📍 {stream.location_name}</p>
        )}
        {stream.description && (
          <p className="mt-2 text-sm text-gray-500">{stream.description}</p>
        )}
      </div>

      <div className="mb-4">
        <StreamPlayer embedUrl={stream.embed_url} name={stream.name} />
      </div>

      <div className="mb-6">
        <DetectionBadge
          category={stream.latest_detection_category}
          commonName={stream.latest_detection_common_name}
          confidence={stream.latest_detection_confidence}
          detectedAt={stream.latest_detection_at}
        />
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h2 className="mb-4 text-lg font-semibold text-white">
            Detection History
          </h2>
          <DetectionTimeline detections={detections} loading={loading} />
        </div>
        <div>
          <h2 className="mb-4 text-lg font-semibold text-white">
            Recent Snapshots
          </h2>
          <SnapshotGallery detections={detections} />
        </div>
      </div>
    </div>
  );
}
