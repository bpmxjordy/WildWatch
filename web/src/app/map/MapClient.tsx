"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Stream } from "@/lib/supabase/types";
import { STREAM_WILDLIFE_CATEGORY, WILDLIFE_CATEGORIES } from "@/lib/constants";

interface MapClientProps {
  streams: Stream[];
}

export default function MapClient({ streams }: MapClientProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const [ready, setReady] = useState(false);
  const [selectedStream, setSelectedStream] = useState<Stream | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    Promise.all([
      import("leaflet"),
      import("leaflet.markercluster"),
    ]).then(([L]) => {
      const withCoords = streams.filter((s) => s.latitude && s.longitude);

      let center: [number, number] = [30, 0];
      let zoom = 2;
      if (withCoords.length === 1) {
        center = [withCoords[0].latitude!, withCoords[0].longitude!];
        zoom = 10;
      } else if (withCoords.length > 1) {
        const lats = withCoords.map((s) => s.latitude!);
        const lngs = withCoords.map((s) => s.longitude!);
        center = [
          (Math.min(...lats) + Math.max(...lats)) / 2,
          (Math.min(...lngs) + Math.max(...lngs)) / 2,
        ];
        zoom = 3;
      }

      const map = L.map(mapRef.current!, {
        zoomControl: false,
        attributionControl: false,
      }).setView(center, zoom);

      L.control.zoom({ position: "topright" }).addTo(map);
      L.control
        .attribution({ position: "bottomright", prefix: false })
        .addAttribution('&copy; <a href="https://carto.com/">CARTO</a>')
        .addTo(map);

      L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        { subdomains: "abcd", maxZoom: 19 }
      ).addTo(map);

      // Marker cluster group with custom cluster icons
      const clusterGroup = (L as any).markerClusterGroup({
        maxClusterRadius: 50,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        iconCreateFunction: (cluster: any) => {
          const count = cluster.getChildCount();
          const size = count > 10 ? 44 : count > 5 ? 38 : 32;
          return L.divIcon({
            className: "",
            html: `<div style="
              width:${size}px;height:${size}px;border-radius:50%;
              background:radial-gradient(circle at 35% 35%, #7db86a, #3d6b32);
              border:3px solid rgba(245,247,242,0.8);
              box-shadow:0 0 12px rgba(106,155,90,0.6), 0 0 24px rgba(106,155,90,0.3);
              display:flex;align-items:center;justify-content:center;
              font-family:'JetBrains Mono',monospace;font-size:${count > 10 ? 13 : 11}px;
              font-weight:600;color:#f5f7f2;
              text-shadow:0 1px 2px rgba(0,0,0,0.4);
              cursor:pointer;transition:transform 0.15s;
            ">${count}</div>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2],
          });
        },
      });

      // Individual markers
      withCoords.forEach((s) => {
        const isLive = s.is_live;
        const hasDetection = !!s.latest_detection_at;
        const color = isLive
          ? hasDetection
            ? "#6a9b5a"
            : "#507a42"
          : "#5a7a5e";
        const glow = isLive ? `0 0 8px ${color}, 0 0 16px ${color}44` : "none";
        const size = isLive ? 12 : 10;

        const icon = L.divIcon({
          className: "",
          html: `<div style="
            width:${size}px;height:${size}px;border-radius:50%;
            background:${color};
            border:2px solid rgba(245,247,242,0.7);
            box-shadow:${glow};
          "></div>`,
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
        });

        const marker = L.marker([s.latitude!, s.longitude!], { icon });

        const catInfo = STREAM_WILDLIFE_CATEGORY[s.slug]
          ? WILDLIFE_CATEGORIES[STREAM_WILDLIFE_CATEGORY[s.slug]]
          : null;

        const thumbnailUrl =
          s.latest_detection_thumbnail_url || s.thumbnail_url || "";
        const detectionLine = s.latest_detection_common_name
          ? `<div style="margin-top:6px;font-size:10px;">
               <span style="color:#6a9b5a;font-weight:600;text-transform:uppercase;font-size:9px;letter-spacing:0.05em;">${s.latest_detection_common_name}</span>
               <span style="color:#5a7a5e;margin:0 4px;">&middot;</span>
               <span style="font-size:9px;color:#5a7a5e;">${s.latest_detection_confidence ? Math.round(s.latest_detection_confidence * 100) + "%" : ""}</span>
             </div>`
          : "";

        marker.bindPopup(
          `<div style="min-width:180px;font-family:'DM Sans',sans-serif;">
            ${thumbnailUrl ? `<img src="${thumbnailUrl}" style="width:100%;height:100px;object-fit:cover;border-radius:4px;margin-bottom:6px;" onerror="this.style.display='none'">` : ""}
            <div style="font-weight:600;font-size:13px;color:#1e3320;">${s.name}</div>
            <div style="font-size:10px;color:#5a7a5e;text-transform:uppercase;letter-spacing:0.06em;margin-top:2px;">${s.location_name || ""}</div>
            ${catInfo ? `<span style="display:inline-block;margin-top:4px;font-size:9px;color:#5a7a5e;">${catInfo.emoji} ${catInfo.label}</span>` : ""}
            ${detectionLine}
            <a href="/stream/${s.slug}" style="display:inline-block;margin-top:8px;font-size:11px;color:#507a42;font-weight:500;text-decoration:none;">View stream &rarr;</a>
          </div>`,
          { className: "wildwatch-popup" }
        );

        marker.on("click", () => setSelectedStream(s));
        clusterGroup.addLayer(marker);
      });

      map.addLayer(clusterGroup);

      // Fit bounds to show all markers
      if (withCoords.length > 1) {
        const bounds = L.latLngBounds(
          withCoords.map((s) => [s.latitude!, s.longitude!] as [number, number])
        );
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
      }

      mapInstance.current = map;
      setReady(true);

      setTimeout(() => map.invalidateSize(), 100);
    });

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const withCoords = streams.filter((s) => s.latitude && s.longitude);
  const liveCount = streams.filter((s) => s.is_live).length;
  const detectedCount = streams.filter(
    (s) => s.latest_detection_common_name
  ).length;

  return (
    <div className="-mx-7 -mt-9">
      {/* Header bar */}
      <div className="border-b border-rule bg-[var(--bg)] px-7 py-5">
        <div className="mx-auto flex max-w-page items-end justify-between">
          <div>
            <span className="mb-2 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-accent-deep before:inline-block before:h-px before:w-4 before:bg-accent-deep">
              Geographic view
            </span>
            <h1 className="font-serif text-[clamp(28px,3vw,44px)] font-medium leading-none tracking-tight text-ink">
              Camera <em className="font-normal not-italic text-accent-deep">Map</em>
            </h1>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                Cameras
              </p>
              <p className="font-serif text-2xl font-medium text-ink">
                {withCoords.length}
              </p>
            </div>
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                Live
              </p>
              <p className="font-serif text-2xl font-medium text-detect">
                {liveCount}
              </p>
            </div>
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted">
                Detections
              </p>
              <p className="font-serif text-2xl font-medium text-accent">
                {detectedCount}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="relative" style={{ height: "calc(100vh - 220px)" }}>
        <div ref={mapRef} className="h-full w-full" />

        {/* Legend */}
        <div className="absolute bottom-6 left-6 z-[1000] rounded-lg border border-rule/30 bg-[#1a1f1a]/90 px-4 py-3 backdrop-blur-md">
          <p className="mb-2 font-mono text-[9px] uppercase tracking-wider text-[#b4ceaa]">
            Legend
          </p>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{
                  background: "#6a9b5a",
                  boxShadow: "0 0 6px rgba(106,155,90,0.6)",
                }}
              />
              <span className="text-[10px] text-[#d4e2cd]">
                Live + Detection
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{
                  background: "#507a42",
                  boxShadow: "0 0 6px rgba(80,122,66,0.4)",
                }}
              />
              <span className="text-[10px] text-[#d4e2cd]">Live</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-full bg-[#5a7a5e]" />
              <span className="text-[10px] text-[#d4e2cd]">Offline</span>
            </div>
            <div className="flex items-center gap-2 mt-1 pt-1 border-t border-[#2d4a30]">
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-[8px] font-bold text-[#f5f7f2]"
                style={{
                  background: "radial-gradient(circle at 35% 35%, #7db86a, #3d6b32)",
                  border: "2px solid rgba(245,247,242,0.8)",
                }}
              >
                3
              </span>
              <span className="text-[10px] text-[#d4e2cd]">Cluster (click to zoom)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stream list below map */}
      <div className="border-t border-rule bg-[var(--bg)] px-7 py-6">
        <div className="mx-auto max-w-page">
          <h2 className="mb-4 font-serif text-lg font-medium text-ink">
            All Cameras
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {streams
              .filter((s) => s.latitude && s.longitude)
              .map((s) => (
                <Link
                  key={s.id}
                  href={`/stream/${s.slug}`}
                  className="group flex items-center gap-3 rounded-lg border border-rule bg-paper-2/50 px-3 py-2.5 transition-colors hover:bg-paper-2"
                >
                  <span
                    className="h-2 w-2 flex-shrink-0 rounded-full"
                    style={{
                      background: s.is_live ? "#6a9b5a" : "#5a7a5e",
                      boxShadow: s.is_live
                        ? "0 0 6px rgba(106,155,90,0.5)"
                        : "none",
                    }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[13px] font-medium text-ink group-hover:text-accent-deep">
                      {s.name}
                    </p>
                    <p className="truncate font-mono text-[9px] uppercase tracking-wider text-muted">
                      {s.location_name}
                    </p>
                  </div>
                  {s.latest_detection_common_name && (
                    <span className="flex-shrink-0 rounded-sm bg-detect/20 px-1.5 py-0.5 font-mono text-[8px] uppercase tracking-wider text-detect">
                      {s.latest_detection_common_name}
                    </span>
                  )}
                </Link>
              ))}
          </div>
        </div>
      </div>

      {/* Custom popup & cluster styles */}
      <style jsx global>{`
        .wildwatch-popup .leaflet-popup-content-wrapper {
          background: #f5f7f2;
          border: 1px solid #d4e2cd;
          border-radius: 8px;
          box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
          padding: 0;
        }
        .wildwatch-popup .leaflet-popup-content {
          margin: 10px 12px;
        }
        .wildwatch-popup .leaflet-popup-tip {
          background: #f5f7f2;
          border: 1px solid #d4e2cd;
        }
        .leaflet-control-zoom a {
          background: #1a1f1a !important;
          color: #d4e2cd !important;
          border-color: #2d4a30 !important;
        }
        .leaflet-control-zoom a:hover {
          background: #2d4a30 !important;
          color: #f5f7f2 !important;
        }
        .marker-cluster-small,
        .marker-cluster-medium,
        .marker-cluster-large {
          background: none !important;
        }
        .marker-cluster-small div,
        .marker-cluster-medium div,
        .marker-cluster-large div {
          background: none !important;
        }
      `}</style>
    </div>
  );
}
