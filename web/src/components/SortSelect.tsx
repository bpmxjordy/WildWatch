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
      className="rounded-full border border-rule-2 bg-paper px-3 py-1.5 text-[12.5px] text-ink focus:border-accent focus:outline-none"
    >
      <option value="latest">Sort: Latest detection</option>
      <option value="name">Sort: Name A-Z</option>
      <option value="species">Sort: Species A-Z</option>
    </select>
  );
}
