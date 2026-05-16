import { DETECTION_STALE_SECONDS } from "@/lib/constants";

interface StatusDotProps {
  category: string | null;
  detectedAt: string | null;
  isLive: boolean;
}

export default function StatusDot({ category, detectedAt, isLive }: StatusDotProps) {
  if (!isLive) {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-sm bg-black/45 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white/70 backdrop-blur-sm"
        title="Offline"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-muted-2" />
        Offline
      </span>
    );
  }

  const isRecent =
    detectedAt &&
    (Date.now() - new Date(detectedAt).getTime()) / 1000 < DETECTION_STALE_SECONDS;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-sm bg-black/55 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-white backdrop-blur-sm"
      title={category === "animal" && isRecent ? "Animal detected" : "Live"}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{
          background: "var(--live)",
          boxShadow: "0 0 0 0 rgba(217,64,64,0.6)",
          animation: "live-pulse 1.8s ease-in-out infinite",
        }}
      />
      Live
    </span>
  );
}
