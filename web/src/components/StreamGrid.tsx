"use client";

import { useMemo, useState } from "react";
import type { Stream } from "@/lib/supabase/types";
import { useRealtimeDetections } from "@/hooks/useRealtimeDetections";
import { DETECTION_STALE_SECONDS } from "@/lib/constants";
import StreamCard from "./StreamCard";
import FilterBar from "./FilterBar";
import SortSelect, { type SortOption } from "./SortSelect";

interface StreamGridProps {
  initialStreams: Stream[];
}

export default function StreamGrid({ initialStreams }: StreamGridProps) {
  const streams = useRealtimeDetections(initialStreams);
  const [search, setSearch] = useState("");
  const [showAnimalsOnly, setShowAnimalsOnly] = useState(false);
  const [speciesFilter, setSpeciesFilter] = useState("");
  const [sort, setSort] = useState<SortOption>("latest");

  const availableSpecies = useMemo(() => {
    const names = new Set<string>();
    streams.forEach((s) => {
      if (s.latest_detection_common_name) {
        names.add(s.latest_detection_common_name);
      }
    });
    return Array.from(names).sort();
  }, [streams]);

  const filtered = useMemo(() => {
    let result = [...streams];

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.location_name?.toLowerCase().includes(q) ||
          s.latest_detection_common_name?.toLowerCase().includes(q)
      );
    }

    if (showAnimalsOnly) {
      const now = Date.now();
      result = result.filter(
        (s) =>
          s.latest_detection_category === "animal" &&
          s.latest_detection_at &&
          (now - new Date(s.latest_detection_at).getTime()) / 1000 <
            DETECTION_STALE_SECONDS
      );
    }

    if (speciesFilter) {
      result = result.filter(
        (s) => s.latest_detection_common_name === speciesFilter
      );
    }

    switch (sort) {
      case "latest":
        result.sort((a, b) => {
          const aTime = a.latest_detection_at
            ? new Date(a.latest_detection_at).getTime()
            : 0;
          const bTime = b.latest_detection_at
            ? new Date(b.latest_detection_at).getTime()
            : 0;
          return bTime - aTime;
        });
        break;
      case "name":
        result.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case "species":
        result.sort((a, b) =>
          (a.latest_detection_common_name ?? "").localeCompare(
            b.latest_detection_common_name ?? ""
          )
        );
        break;
    }

    return result;
  }, [streams, search, showAnimalsOnly, speciesFilter, sort]);

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <FilterBar
          search={search}
          onSearchChange={setSearch}
          showAnimalsOnly={showAnimalsOnly}
          onToggleAnimals={() => setShowAnimalsOnly((v) => !v)}
          speciesFilter={speciesFilter}
          onSpeciesChange={setSpeciesFilter}
          availableSpecies={availableSpecies}
        />
        <SortSelect value={sort} onChange={setSort} />
      </div>

      {filtered.length === 0 ? (
        <div className="py-20 text-center text-gray-500">
          <p className="text-4xl mb-3">🔭</p>
          <p>No streams match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((stream) => (
            <StreamCard key={stream.id} stream={stream} />
          ))}
        </div>
      )}

      <p className="mt-4 text-center text-xs text-gray-600">
        Showing {filtered.length} of {streams.length} streams
      </p>
    </div>
  );
}
