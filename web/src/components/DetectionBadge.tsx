import { getSpeciesEmoji, confidencePercent } from "@/lib/utils";

interface DetectionBadgeProps {
  category: string | null;
  commonName: string | null;
  confidence: number | null;
  detectedAt: string | null;
}

export default function DetectionBadge({
  category,
  commonName,
  confidence,
}: DetectionBadgeProps) {
  if (!category || category === "blank") {
    return null;
  }

  if (category === "person") {
    return (
      <span className="pointer-events-auto inline-flex items-center gap-2 rounded-full bg-[var(--bg)] px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-[0_2px_6px_rgba(0,0,0,0.25)]">
        <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-blue-400 text-[11px] font-bold text-blue-950">
          P
        </span>
        Person
      </span>
    );
  }

  if (category === "vehicle") {
    return (
      <span className="pointer-events-auto inline-flex items-center gap-2 rounded-full bg-[var(--bg)] px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-[0_2px_6px_rgba(0,0,0,0.25)]">
        <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-yellow-400 text-[11px] font-bold text-yellow-950">
          V
        </span>
        Vehicle
      </span>
    );
  }

  const emoji = getSpeciesEmoji(commonName);
  const name = commonName || "Unknown";
  const conf = confidencePercent(confidence);

  return (
    <span className="pointer-events-auto inline-flex items-center gap-2 rounded-full bg-[var(--bg)] px-2.5 py-1.5 text-[11px] font-medium text-ink shadow-[0_2px_6px_rgba(0,0,0,0.25)]">
      <span className="flex h-[18px] w-[18px] items-center justify-center rounded-full bg-detect text-[11px] font-bold text-[#1a2e1a]">
        {emoji}
      </span>
      {name}
      {conf && (
        <span className="font-mono text-[9.5px] tracking-wide text-muted">
          {conf}
        </span>
      )}
    </span>
  );
}
