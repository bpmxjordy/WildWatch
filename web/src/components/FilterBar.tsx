"use client";

interface FilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  showAnimalsOnly: boolean;
  onToggleAnimals: () => void;
  speciesFilter: string;
  onSpeciesChange: (value: string) => void;
  availableSpecies: string[];
}

export default function FilterBar({
  search,
  onSearchChange,
  showAnimalsOnly,
  onToggleAnimals,
  speciesFilter,
  onSpeciesChange,
  availableSpecies,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <input
        type="text"
        placeholder="Search streams..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
      />
      <button
        onClick={onToggleAnimals}
        className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
          showAnimalsOnly
            ? "bg-green-600 text-white"
            : "border border-gray-700 bg-gray-800 text-gray-300 hover:border-gray-600"
        }`}
      >
        🐾 Animals visible now
      </button>
      {availableSpecies.length > 0 && (
        <select
          value={speciesFilter}
          onChange={(e) => onSpeciesChange(e.target.value)}
          className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-green-500 focus:outline-none"
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
