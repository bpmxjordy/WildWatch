"use client";

interface StreamPlayerProps {
  embedUrl: string;
  name: string;
}

export default function StreamPlayer({ embedUrl, name }: StreamPlayerProps) {
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
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
