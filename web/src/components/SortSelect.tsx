"use client";

export type SortOption = "latest" | "name" | "species";

interface SortSelectProps {
  value: SortOption;
  onChange: (value: SortOption) => void;
}

export default function SortSelect({ value, onChange }: SortSelectProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as SortOption)}
      className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-green-500 focus:outline-none"
    >
      <option value="latest">Sort: Latest detection</option>
      <option value="name">Sort: Name A–Z</option>
      <option value="species">Sort: Species A–Z</option>
    </select>
  );
}
