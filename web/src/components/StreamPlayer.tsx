"use client";

interface StreamPlayerProps {
  embedUrl: string;
  name: string;
  thumbnailUrl?: string | null;
  platform?: string | null;
}

/** Platforms where we link out instead of embedding */
const EXTERNAL_PLATFORMS = new Set(["jpeg", "mjpeg"]);

export default function StreamPlayer({ embedUrl, name, thumbnailUrl, platform }: StreamPlayerProps) {
  const isExternal = EXTERNAL_PLATFORMS.has(platform ?? "");

  if (isExternal) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-md bg-paper-2">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={name}
            className="absolute inset-0 h-full w-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="font-serif text-muted italic">No preview available</span>
          </div>
        )}
        <a
          href={embedUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 hover:opacity-100 transition-opacity duration-200"
        >
          <span className="flex items-center gap-2.5 rounded-md bg-[#1e3320]/90 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.16em] text-white shadow-lg backdrop-blur-sm">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Watch live on HDOnTap
          </span>
        </a>
      </div>
    );
  }

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-md bg-paper-2">
      <iframe
        src={embedUrl + (embedUrl.includes("?") ? "&" : "?") + "autoplay=1&mute=1"}
        title={name}
        className="absolute inset-0 h-full w-full"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    </div>
  );
}
