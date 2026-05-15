import { getSpeciesEmoji, timeAgo, confidencePercent } from "@/lib/utils";

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
  detectedAt,
}: DetectionBadgeProps) {
  if (!category || category === "blank") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-gray-800 px-3 py-1 text-xs text-gray-400">
        No animal detected
      </span>
    );
  }

  if (category === "person") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-blue-900/50 px-3 py-1 text-xs text-blue-300">
        👤 Person detected
      </span>
    );
  }

  if (category === "vehicle") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-900/50 px-3 py-1 text-xs text-yellow-300">
        🚗 Vehicle detected
      </span>
    );
  }

  const emoji = getSpeciesEmoji(commonName);
  const name = commonName || "Unknown animal";
  const conf = confidencePercent(confidence);
  const time = timeAgo(detectedAt);

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-900/50 px-3 py-1 text-xs text-green-300">
      <span>{emoji}</span>
      <span className="font-medium">{name}</span>
      {conf && <span className="text-green-400/70">{conf}</span>}
      <span className="text-green-400/50">— {time}</span>
    </span>
  );
}
