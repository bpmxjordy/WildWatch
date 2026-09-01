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
    desc: "Once a minute, every camera in the network gives up a single frame. Most arrive as plain snapshots over HTTP; the true video feeds are HLS streams that ffmpeg opens just long enough to take one picture. Cameras are polled in parallel, and one that has gone dark is set aside to retry later rather than holding up the line.",
  },
  {
    num: "II.",
    title: "Detection",
    desc: "The frame goes to Google's SpeciesNet, running on a local GPU. MegaDetector v5 draws a box around every animal it can find, and an EfficientNet V2 classifier says what each one is. Everything in the frame is recorded — the fox at the edge as well as the deer in the middle.",
  },
  {
    num: "III.",
    title: "Putting a name to it",
    desc: "A single frame is a poor witness. Classifier confidence is summed up the taxonomic tree, and the deepest rank that clears its bar wins — so a hesitant guess settles at 'Penguin' rather than cycling through ten lookalike species. Recent frames from the same camera then vote among themselves, and the label firms up as the evidence does.",
  },
  {
    num: "IV.",
    title: "From frames to sightings",
    desc: "A bear that fishes the same stretch of river for twenty minutes is one visit, not twenty discoveries. Runs of frames showing the same species collapse into a single sighting: when it arrived, when it left, and the clearest picture taken while it was there. The per-frame record survives alongside it — one number for how busy the camera was, another for how many animals actually came.",
  },
  {
    num: "V.",
    title: "Serving it",
    desc: "Each camera's statistics are totalled once a day and cached, so opening a page costs one read, not a fresh query per visitor. Snapshots live for two weeks. The detection records behind the charts are far smaller, and those are kept for a year.",
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
          Public wildlife cameras stream around the clock, mostly to no one.
          WildWatch keeps them company. Every camera in the network is checked
          once a minute, every animal that steps into frame is named and noted,
          and the record of who came, and when, is waiting here — whether or not
          anyone happened to be watching.
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
          Every label on this site is a machine&apos;s best guess, not a
          verified record. The model is good at a large animal in plain view and
          worse at anything small, distant, or half-behind a branch; it knows
          common species better than rare ones. When it can&apos;t reach a
          species it doesn&apos;t pretend to — it stops at a family, or simply
          says &ldquo;Bird.&rdquo; The boxes are drawn onto each snapshot at the
          moment of inference, so what you see is exactly what the model saw.
        </p>
      </div>

      {/* Credit */}
      <div className="mb-12 border-t border-rule pt-9">
        <h3 className="mb-3 font-mono text-[10.5px] font-medium uppercase tracking-[0.16em] text-muted">
          The cameras
        </h3>
        <p className="max-w-[58ch] text-[14.5px] leading-relaxed text-ink-2">
          WildWatch owns no cameras. Every stream here belongs to a zoo, a
          reserve, or a conservation group that mounted it, aims it, and pays
          for the bandwidth; our part is only the watching. Each camera page
          links back to its source — and if one of these animals is worth your
          time, it&apos;s worth seeing on the stream its keepers built.
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
