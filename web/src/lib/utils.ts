import { SPECIES_EMOJI } from "./constants";

export function timeAgo(dateString: string | null): string {
  if (!dateString) return "Never";
  const seconds = Math.floor(
    (Date.now() - new Date(dateString).getTime()) / 1000
  );
  if (seconds < 10) return "Just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function formatSpeciesName(label: string | null): string | null {
  if (!label) return null;
  const parts = label.split(";");
  const name = parts[parts.length - 1]?.trim();
  if (!name) return null;
  return name
    .split(" ")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export function getSpeciesEmoji(commonName: string | null): string {
  if (!commonName) return SPECIES_EMOJI.default;
  const lower = commonName.toLowerCase();
  for (const [key, emoji] of Object.entries(SPECIES_EMOJI)) {
    if (key !== "default" && lower.includes(key)) return emoji;
  }
  return SPECIES_EMOJI.default;
}

export function confidencePercent(confidence: number | null): string {
  if (confidence === null || confidence === undefined) return "";
  return `${Math.round(confidence * 100)}%`;
}
