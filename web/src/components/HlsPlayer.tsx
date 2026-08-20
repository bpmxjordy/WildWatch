"use client";

import { useEffect, useRef, useState } from "react";

interface HlsPlayerProps {
  /** Direct .m3u8 URL (master playlist). */
  src: string;
  name: string;
  poster?: string | null;
  /** Where to send the viewer if playback fails. */
  fallbackUrl?: string;
}

/**
 * Plays an HLS stream inline.
 *
 * Safari (and iOS in particular) plays HLS natively from a plain `src`, and
 * native playback isn't subject to CORS. Everywhere else we need hls.js, which
 * fetches the playlist and segments over XHR and therefore *does* need the
 * origin to send CORS headers — the Smithsonian Wowza endpoints send
 * `Access-Control-Allow-Origin: *`, so no proxy is involved.
 */
export default function HlsPlayer({ src, name, poster, fallbackUrl }: HlsPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    setFailed(false);

    let destroyed = false;
    let hls: import("hls.js").default | null = null;

    const playNatively = () => {
      video.src = src;
      video.play().catch(() => {
        /* autoplay may be refused until the viewer interacts; controls remain */
      });
    };

    // Dynamic import keeps hls.js out of the main bundle — only stream pages
    // that actually need it pay the download.
    import("hls.js").then(({ default: Hls }) => {
      if (destroyed) return;

      // hls.js first wherever MSE exists. Chromium reports "maybe" for the
      // HLS MIME from canPlayType() but cannot actually play it, so trusting
      // canPlayType ahead of Hls.isSupported() silently breaks every non-Safari
      // browser. iOS Safari has no MSE, so it lands on the native path here.
      if (!Hls.isSupported()) {
        if (video.canPlayType("application/vnd.apple.mpegurl")) {
          playNatively();
        } else {
          setFailed(true);
        }
        return;
      }

      hls = new Hls({
        // These are other people's CDNs; don't pull a 6 Mbps 1080p rendition
        // into an 800px player, and don't buffer minutes of live video ahead.
        capLevelToPlayerSize: true,
        maxBufferLength: 15,
      });

      hls.loadSource(src);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {
          /* see above */
        });
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (!data.fatal) return;
        switch (data.type) {
          case Hls.ErrorTypes.NETWORK_ERROR:
            hls?.startLoad();
            break;
          case Hls.ErrorTypes.MEDIA_ERROR:
            hls?.recoverMediaError();
            break;
          default:
            hls?.destroy();
            hls = null;
            setFailed(true);
        }
      });
    });

    return () => {
      destroyed = true;
      hls?.destroy();
    };
  }, [src]);

  if (failed) {
    return (
      <div className="relative aspect-video w-full overflow-hidden rounded-md bg-paper-2">
        {poster ? (
          <img src={poster} alt={name} className="absolute inset-0 h-full w-full object-cover" />
        ) : null}
        <a
          href={fallbackUrl ?? src}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute inset-0 flex items-center justify-center bg-black/40"
        >
          <span className="rounded-md bg-[#1e3320]/90 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.16em] text-white shadow-lg backdrop-blur-sm">
            Stream unavailable — watch on source
          </span>
        </a>
      </div>
    );
  }

  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-md bg-paper-2">
      <video
        ref={videoRef}
        className="absolute inset-0 h-full w-full object-cover"
        poster={poster ?? undefined}
        controls
        muted
        autoPlay
        playsInline
        aria-label={name}
      />
    </div>
  );
}
