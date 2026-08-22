"use client";

import { useMemo, useState } from "react";
import type { Stream } from "@/lib/supabase/types";
import {
  DETECTION_STALE_SECONDS,
  STREAM_WILDLIFE_CATEGORY,
  type WildlifeCategory,
} from "@/lib/constants";
import StreamCard from "./StreamCard";
import FilterBar from "./FilterBar";
import SortSelect, { type SortOption } from "./SortSelect";
import FeaturedStreams from "./FeaturedStreams";

interface StreamGridProps {
  initialStreams: Stream[];
}

export default function StreamGrid({ initialStreams }: StreamGridProps) {
  const streams = initialStreams;
  const [search, setSearch] = useState("");
  const [showAnimalsOnly, setShowAnimalsOnly] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<WildlifeCategory | "">("");
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

    if (categoryFilter) {
      result = result.filter(
        (s) => STREAM_WILDLIFE_CATEGORY[s.slug] === categoryFilter
      );
    }

    if (showAnimalsOnly) {
      const now = Date.now();
      result = result.filter((s) => {
        if (
          s.latest_detection_category !== "animal" ||
          !s.latest_detection_at ||
          !s.latest_detection_common_name
        ) {
          return false;
        }
        const age = (now - new Date(s.latest_detection_at).getTime()) / 1000;
        return age < DETECTION_STALE_SECONDS;
      });
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
  }, [streams, search, showAnimalsOnly, categoryFilter, speciesFilter, sort]);

  // Cameras that play inline here rather than linking out.
  const featured = useMemo(
    () => streams.filter((s) => s.platform === "hls" && s.source_url),
    [streams]
  );

  // Any narrowing of the list hides the featured row -- once the visitor has
  // said what they're after, a fixed set of cameras is just in the way. Sort
  // doesn't count: it reorders rather than narrows.
  const isFiltered = Boolean(
    search || categoryFilter || speciesFilter || showAnimalsOnly
  );

  return (
    <div>
      {!isFiltered && <FeaturedStreams streams={featured} />}

      <div className="border-y border-rule py-4 mb-7">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <FilterBar
            search={search}
            onSearchChange={setSearch}
            showAnimalsOnly={showAnimalsOnly}
            onToggleAnimals={() => setShowAnimalsOnly((v) => !v)}
            categoryFilter={categoryFilter}
            onCategoryChange={setCategoryFilter}
            speciesFilter={speciesFilter}
            onSpeciesChange={setSpeciesFilter}
            availableSpecies={availableSpecies}
          />
          <SortSelect value={sort} onChange={setSort} />
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="py-20 text-center text-muted">
          <p className="text-4xl mb-3">🔭</p>
          <p className="font-serif text-lg italic">No streams match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((stream) => (
            <StreamCard key={stream.id} stream={stream} />
          ))}
        </div>
      )}

      <p className="mt-6 text-center font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
        Showing {filtered.length} of {streams.length} streams
      </p>
    </div>
  );
}
