import { DETECTION_STALE_SECONDS } from "@/lib/constants";

interface StatusDotProps {
  category: string | null;
  detectedAt: string | null;
  isLive: boolean;
}

export default function StatusDot({ category, detectedAt, isLive }: StatusDotProps) {
  if (!isLive) {
    return <span className="inline-block h-2.5 w-2.5 rounded-full bg-red-500" title="Offline" />;
  }

  const isRecent =
    detectedAt &&
    (Date.now() - new Date(detectedAt).getTime()) / 1000 < DETECTION_STALE_SECONDS;

  if (category === "animal" && isRecent) {
    return (
      <span className="relative inline-block h-2.5 w-2.5" title="Animal detected">
        <span className="absolute inset-0 animate-ping rounded-full bg-green-400 opacity-75" />
        <span className="relative inline-block h-2.5 w-2.5 rounded-full bg-green-500" />
      </span>
    );
  }

  return <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-500" title="No animal" />;
}
