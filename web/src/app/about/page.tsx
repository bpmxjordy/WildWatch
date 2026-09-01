import { createServerClient } from "@/lib/supabase/server";

export const metadata = {
  title: "About — WildWatch",
  description:
    "How WildWatch uses AI to detect wildlife across public livestream cameras.",
};

// Same cadence as the home page. The figures below are counted rather than
// hardcoded — a typed-in camera count silently goes stale the moment the
// network changes.
export const revalidate = 300;

function Stat({ n, l }: { n: string; l: string }) {
  return (
    <div className="border-l border-rule pl-4 first:border-0 first:pl-0">
      <span className="block font-serif text-[clamp(32px,3vw,48px)] font-medium leading-none tracking-tight text-ink">
        {n}
      </span>
      <span className="mt-2 block font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
        {l}
      </span>
    </div>
  );
}

const STEPS = [
  {
    num: "I.",
    title: "Frame capture",
    desc: "Every camera is sampled once a minute. Most are snapshot endpoints fetched over plain HTTP; the rest are HLS playlists, where ffmpeg resolves the stream and pulls a single frame. Cameras are sampled in parallel, and one that goes offline backs off rather than blocking the rest.",
  },
  {
    num: "II.",
    title: "Detection",
    desc: "Each frame goes to Google's SpeciesNet — MegaDetector v5 finds the animals, then an EfficientNet V2 classifier identifies them, running on a local GPU in batches. Every distinct animal in a frame is recorded, not just the most obvious one.",
  },
  {
    num: "III.",
    title: "Deciding what it is",
    desc: "Classifier confidence is summed up the taxonomic tree, and the deepest rank that clears its threshold wins — so an uncertain guess becomes 'Penguin' rather than flickering between ten lookalike species. A rolling vote across recent frames from the same camera then settles the label, which sharpens as evidence accumulates instead of changing frame to frame.",
  },
  {
    num: "IV.",
    title: "From frames to sightings",
    desc: "A bear standing in a river for twenty minutes is one visit, not twenty discoveries. Consecutive frames showing the same species are folded into a single sighting with a start, an end, and the clearest image captured while it was there. Both views are kept: detections measure how much the camera saw, sightings measure how many animals turned up.",
  },
  {
    num: "V.",
    title: "Serving it",
    desc: "Activity statistics are aggregated once a day per camera and cached, so opening a page is a single read rather than a query per visitor. Snapshots are pruned after two weeks; the much smaller detection records are kept for a year, which is what the long-range charts are drawn from.",
  },
];

const TECH = [
  "Next.js 14",
  "Supabase",
  "SpeciesNet",
  "MegaDetector v5",
  "Tailwind CSS",
  "Vercel",
  "hls.js",
  "ffmpeg",
  "PyTorch + CUDA",
];

export default async function AboutPage() {
  const supabase = await createServerClient();

  const [cameras, sightings, detections] = await Promise.all([
    supabase
      .from("streams")
      .select("id", { count: "exact", head: true })
      .eq("is_active", true),
    supabase.from("species_events").select("id", { count: "exact", head: true }),
    supabase.from("detections").select("id", { count: "exact", head: true }),
  ]);

  const fmt = (n: number | null) =>
    n == null ? "—" : n >= 1000 ? `${Math.floor(n / 1000)}k+` : String(n);

  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero */}
      <div className="mb-10 border-b border-rule pb-10">
        <span className="mb-3 inline-flex items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-accent-deep before:inline-block before:h-px before:w-4 before:bg-accent-deep">
          About
        </span>
        <h1 className="mb-6 font-serif text-[clamp(40px,5vw,72px)] font-medium leading-[0.95] tracking-tight text-ink">
          Watching the wild,{" "}
          <em className="font-normal italic text-accent-deep">quietly</em>,
          together.
        </h1>
        <p className="max-w-[52ch] text-[17px] leading-relaxed text-ink-2">
          WildWatch watches public wildlife cameras so you don&apos;t have to sit
          through the quiet hours. Every camera is checked once a minute, every
          animal that walks into frame is identified and catalogued, and what
          turned up — and when — is there whether or not anyone was looking.
        </p>
      </div>

      {/* Stats */}
      <div className="mb-10 grid grid-cols-2 gap-5 border-b border-rule pb-10 sm:grid-cols-4">
        <Stat n={fmt(cameras.count)} l="Cameras watched" />
        <Stat n={fmt(sightings.count)} l="Sightings logged" />
        <Stat n={fmt(detections.count)} l="Frames with animals" />
        <Stat n="60s" l="Scan interval" />
      </div>

      {/* How it works */}
      <div className="mb-12">
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
          Method
        </span>
        <h2 className="mb-8 mt-1 font-serif text-[28px] font-medium tracking-tight text-ink">
          How a frame becomes a sighting.
        </h2>

        <div className="flex flex-col">
          {STEPS.map((step, i) => (
            <div
              key={step.num}
              className={`grid grid-cols-[56px_1fr] gap-6 border-b border-rule py-5 ${
                i === 0 ? "border-t border-rule" : ""
              }`}
            >
              <span className="font-serif text-[28px] italic text-accent-deep">
                {step.num}
              </span>
              <div>
                <h3 className="mb-1.5 font-serif text-[22px] font-medium tracking-tight text-ink">
                  {step.title}
                </h3>
                <p className="max-w-[56ch] text-[14.5px] leading-relaxed text-ink-2">
                  {step.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Honesty about the model */}
      <div className="mb-12 border-l-2 border-accent-deep/30 pl-6">
        <h3 className="mb-2 font-serif text-[20px] font-medium tracking-tight text-ink">
          What the labels are worth
        </h3>
        <p className="max-w-[58ch] text-[14.5px] leading-relaxed text-ink-2">
          These are automated guesses, not verified records. The model does
          better with a large animal filling the frame than with something small,
          distant, or half-hidden in undergrowth, and it is more confident about
          common species than rare ones. Where it can&apos;t reach a species it
          says so, naming a family or simply &ldquo;Bird&rdquo; rather than
          inventing detail. Boxes are drawn onto each snapshot at the moment of
          inference, so what you see is exactly what the model saw.
        </p>
      </div>

      {/* Credit */}
      <div className="mb-12 border-t border-rule pt-9">
        <h3 className="mb-3 font-mono text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted">
          The cameras
        </h3>
        <p className="max-w-[58ch] text-[14.5px] leading-relaxed text-ink-2">
          WildWatch runs no cameras of its own. Every stream belongs to the zoos,
          reserves and conservation organisations who set them up, maintain them
          and pay for the bandwidth — the work here is only in watching them.
          Each camera page links back to its source, and the best way to see any
          of these animals is on the stream its keepers built.
        </p>
      </div>

      {/* Tech stack */}
      <div className="border-t border-rule pt-9">
        <h3 className="mb-5 font-mono text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted">
          Technology
        </h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {TECH.map((t) => (
            <div
              key={t}
              className="rounded border border-dashed border-rule-2 bg-paper/40 px-4 py-4 text-center font-serif text-[15px] italic text-muted"
            >
              {t}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
