import { createServerClient } from "@/lib/supabase/server";
import Link from "next/link";
import { getSpeciesEmoji } from "@/lib/utils";

export const revalidate = 0;

export const metadata = {
  title: "Species Index — WildWatch",
  description: "Browse all species detected across wildlife livestreams.",
};

export default async function SpeciesPage() {
  const supabase = await createServerClient();
  const { data: events } = await supabase
    .from("species_events")
    .select("common_name, stream_id")
    .order("common_name");

  const speciesMap = new Map<string, number>();
  events?.forEach((e) => {
    speciesMap.set(e.common_name, (speciesMap.get(e.common_name) ?? 0) + 1);
  });

  const species = Array.from(speciesMap.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <div>
      <h1 className="mb-2 text-3xl font-bold text-white">Species Index</h1>
      <p className="mb-8 text-gray-400">
        All species detected across our wildlife camera network.
      </p>

      {species.length === 0 ? (
        <div className="py-20 text-center text-gray-500">
          <p className="text-4xl mb-3">🔬</p>
          <p>No species detected yet. The agent needs to run first.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {species.map((sp) => (
            <Link
              key={sp.name}
              href={`/species/${encodeURIComponent(sp.name)}`}
              className="flex items-center gap-3 rounded-xl border border-gray-800 bg-gray-900 p-4 transition-colors hover:border-gray-600"
            >
              <span className="text-3xl">{getSpeciesEmoji(sp.name)}</span>
              <div>
                <p className="font-semibold text-white">{sp.name}</p>
                <p className="text-xs text-gray-500">
                  {sp.count} sighting{sp.count !== 1 ? "s" : ""}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
