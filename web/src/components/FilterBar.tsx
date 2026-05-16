"use client";

import { WILDLIFE_CATEGORIES, type WildlifeCategory } from "@/lib/constants";

interface FilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  showAnimalsOnly: boolean;
  onToggleAnimals: () => void;
  categoryFilter: WildlifeCategory | "";
  onCategoryChange: (value: WildlifeCategory | "") => void;
  speciesFilter: string;
  onSpeciesChange: (value: string) => void;
  availableSpecies: string[];
}

export default function FilterBar({
  search,
  onSearchChange,
  showAnimalsOnly,
  onToggleAnimals,
  categoryFilter,
  onCategoryChange,
  speciesFilter,
  onSpeciesChange,
  availableSpecies,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <input
        type="text"
        placeholder="Search streams..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="rounded-full border border-rule-2 bg-paper px-4 py-1.5 text-[12.5px] text-ink placeholder-muted focus:border-accent focus:outline-none"
      />

      <button
        onClick={onToggleAnimals}
        aria-pressed={showAnimalsOnly}
        className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12.5px] font-medium transition-colors ${
          showAnimalsOnly
            ? "border-ink bg-ink text-[var(--bg)]"
            : "border-rule-2 text-ink-2 hover:bg-paper-2"
        }`}
      >
        Active detections only
        <span
          className={`relative inline-block h-[18px] w-8 rounded-full transition-colors ${
            showAnimalsOnly ? "bg-detect" : "bg-rule-2"
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 h-3.5 w-3.5 rounded-full bg-paper shadow-sm transition-transform ${
              showAnimalsOnly ? "translate-x-3.5" : ""
            }`}
          />
        </span>
      </button>

      <div className="flex items-center gap-1.5">
        {(
          Object.entries(WILDLIFE_CATEGORIES) as [
            WildlifeCategory,
            { label: string; emoji: string },
          ][]
        ).map(([key, { label, emoji }]) => (
          <button
            key={key}
            onClick={() => onCategoryChange(categoryFilter === key ? "" : key)}
            aria-pressed={categoryFilter === key}
            className={`rounded-full border px-3 py-1.5 text-[12.5px] transition-colors ${
              categoryFilter === key
                ? "border-ink bg-ink text-[var(--bg)]"
                : "border-rule-2 text-ink-2 hover:bg-paper-2"
            }`}
          >
            {emoji} {label}
          </button>
        ))}
      </div>

      {availableSpecies.length > 0 && (
        <select
          value={speciesFilter}
          onChange={(e) => onSpeciesChange(e.target.value)}
          className="rounded-full border border-rule-2 bg-paper px-3 py-1.5 text-[12.5px] text-ink focus:border-accent focus:outline-none"
        >
          <option value="">All species</option>
          {availableSpecies.map((sp) => (
            <option key={sp} value={sp}>
              {sp}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
