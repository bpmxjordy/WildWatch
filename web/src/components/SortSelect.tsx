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
      className="h-8 shrink-0 appearance-none rounded-full border border-rule-2 bg-paper py-0 pl-3 pr-8 text-[12.5px] text-ink-2 focus:border-accent focus:outline-none"
      style={{
        backgroundImage: `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'><path fill='%235a7a5e' d='M0 0h10L5 6z'/></svg>")`,
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 10px center",
      }}
    >
      <option value="latest">Sort: Latest</option>
      <option value="name">Sort: Name A-Z</option>
      <option value="species">Sort: Species A-Z</option>
    </select>
  );
}
