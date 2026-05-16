// pages.jsx — MainPage, StreamPage, AboutPage

function FilterBar({ allCount, liveCount, species, activeSpecies, setActiveSpecies, activeOnly, setActiveOnly }) {
  return (
    <div className="ww-filterbar">
      <h2>
        All Cameras
        <span className="count">{allCount} TOTAL · {liveCount} LIVE</span>
      </h2>
      <div className="ww-pills">
        <button
          className="ww-pill"
          aria-pressed={!activeSpecies}
          onClick={() => setActiveSpecies(null)}
        >
          All species
          <span className="ct">{allCount}</span>
        </button>
        {species.map((sp) => (
          <button
            key={sp.key}
            className="ww-pill"
            aria-pressed={activeSpecies === sp.key}
            onClick={() => setActiveSpecies(activeSpecies === sp.key ? null : sp.key)}
          >
            {sp.name}
            <span className="ct">{sp.count}</span>
          </button>
        ))}
      </div>
      <label
        className="ww-toggle"
        aria-pressed={activeOnly}
        onClick={() => setActiveOnly(!activeOnly)}
      >
        Active detections only
        <span className="ww-toggle-sw"></span>
      </label>
    </div>
  );
}

function MainPage({ tweaks, onOpenStream }) {
  const [activeSpecies, setActiveSpecies] = React.useState(null);
  const [activeOnly, setActiveOnly] = React.useState(false);

  const featured = STREAMS.find((s) => s.featured);

  // Build species filter list from detected animals
  const speciesList = React.useMemo(() => {
    const m = new Map();
    STREAMS.forEach((s) => {
      if (s.detected) m.set(s.detected, (m.get(s.detected) || 0) + 1);
    });
    return [...m.entries()].map(([key, count]) => ({
      key,
      name: SPECIES[key].name,
      count,
    }));
  }, []);

  const gridStreams = STREAMS.filter((s) => s.id !== featured.id);
  const visibleStreams = gridStreams.filter((s) => {
    if (activeSpecies && s.detected !== activeSpecies) return false;
    if (activeOnly && !s.detected) return false;
    return true;
  });

  const liveCount = STREAMS.filter((s) => s.online).length;

  return (
    <div className="ww-page">
      {/* Hero */}
      <section className="ww-hero">
        <div onClick={() => onOpenStream(featured)} style={{ cursor: "pointer" }}>
          <StreamMedia stream={featured} variant={tweaks.detection} big />
        </div>
        <div className="ww-hero-side">
          <div>
            <span className="ww-kicker">Featured · Maasai Mara</span>
            <h1 className="ww-hero-title">
              An elephant family <em>has arrived</em> at the watering hole.
            </h1>
            <p className="ww-hero-blurb">
              Three individuals — a matriarch and two calves — drinking just before
              dusk. Camera one of the Mara conservancy network has been tracking this
              herd's movement across the conservancy for the past 14 days.
            </p>
          </div>
          <dl className="ww-hero-meta">
            <div><dt>Location</dt><dd>{featured.region}</dd></div>
            <div><dt>Operator</dt><dd>{featured.operator}</dd></div>
            <div><dt>Detected now</dt><dd>{SPECIES[featured.detected].name} ×{featured.count}</dd></div>
            <div><dt>Confidence</dt><dd>{Math.round(featured.confidence * 100)}%</dd></div>
          </dl>
        </div>
      </section>

      <FilterBar
        allCount={STREAMS.length}
        liveCount={liveCount}
        species={speciesList}
        activeSpecies={activeSpecies}
        setActiveSpecies={setActiveSpecies}
        activeOnly={activeOnly}
        setActiveOnly={setActiveOnly}
      />

      <div className="ww-grid" data-density={tweaks.density}>
        {visibleStreams.map((s) => (
          <Tile
            key={s.id}
            stream={s}
            variant={tweaks.detection}
            onOpen={onOpenStream}
            dimmed={activeOnly && !s.detected}
          />
        ))}
      </div>
    </div>
  );
}

function StreamPage({ stream, tweaks, onBack }) {
  // Pair detections with snapshots (same source data — pick first 8)
  const log = DETECTIONS.slice(0, 10);
  const [active, setActive] = React.useState(0);
  const sp = stream.detected ? SPECIES[stream.detected] : null;

  return (
    <div className="ww-page">
      <span className="ww-back" onClick={onBack}>
        ◂ All cameras
      </span>

      <div className="ww-stream-hd">
        <div>
          <span className="ww-kicker">{HABITAT[stream.habitat]}</span>
          <h1>{stream.name}</h1>
        </div>
        <div className="ww-stream-meta">
          <div>Coordinates<small>{stream.coords}</small></div>
          <div>Operator<small>{stream.operator}</small></div>
          <div>Viewers<small>{stream.viewers.toLocaleString()} now</small></div>
        </div>
      </div>

      <StreamMedia stream={stream} variant={tweaks.detection} big />

      <div className="ww-stream-blurb">
        <p>
          {stream.blurb ||
            `Camera in ${HABITAT[stream.habitat].toLowerCase()} habitat. Continuous live feed with on-device species detection; classifications are reviewed weekly by a partner biologist before being added to the open dataset.`}
        </p>
        <dl className="ww-stream-stats">
          <div>
            <dt>Detections today</dt>
            <dd>34</dd>
          </div>
          <div>
            <dt>Species observed (7d)</dt>
            <dd>6</dd>
          </div>
          <div>
            <dt>Uptime (30d)</dt>
            <dd>99.2%</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd style={{ fontSize: 14, fontFamily: "var(--mono)", letterSpacing: "0.04em" }}>
              MegaDetector v5.1
            </dd>
          </div>
        </dl>
      </div>

      <div className="ww-section-hd">
        <h2>Recent detections</h2>
        <div className="meta">LAST 24 HOURS · {log.length} EVENTS</div>
      </div>

      <div className="ww-det-layout">
        {/* Classifications log */}
        <div className="ww-log">
          {log.map((d, i) => {
            const s = SPECIES[d.species];
            return (
              <div
                key={i}
                className={`ww-log-row${active === i ? " active" : ""}`}
                onClick={() => setActive(i)}
              >
                <div className="ww-log-time">
                  <span className="date">{d.date}</span>
                  {d.t}
                </div>
                <div className="ww-log-species">
                  <span className="name">
                    {s.name}
                    <em>{s.latin}</em>
                  </span>
                  {d.count > 1 && <span className="count">×{d.count}</span>}
                  {d.note && (
                    <span style={{
                      flexBasis: "100%",
                      fontSize: 13,
                      color: "var(--muted)",
                      marginTop: 2,
                    }}>
                      {d.note}
                    </span>
                  )}
                </div>
                <div className="ww-log-conf">
                  <span>{Math.round(d.conf * 100)}%</span>
                  <span className="ww-conf-bar">
                    <i style={{ width: `${Math.round(d.conf * 100)}%` }}></i>
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Snapshots */}
        <div className="ww-gallery">
          {log.map((d, i) => {
            const s = SPECIES[d.species];
            return (
              <div
                key={i}
                className={`ww-snap${active === i ? " active" : ""}`}
                onClick={() => setActive(i)}
              >
                <Placeholder label={`SNAP · ${s.glyph}`} />
                <span className="ww-snap-tag">{s.name}</span>
                <span className="ww-snap-time">{d.date} · {d.t.slice(0, 5)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function AboutPage() {
  return (
    <div className="ww-page">
      <section className="ww-about-hero">
        <div>
          <span className="ww-kicker">About</span>
          <h1>
            Watching the wild, <em>quietly</em>, together.
          </h1>
        </div>
        <div>
          <p>
            WildWatch is a network of 412 wildlife cameras in 38 countries, run by
            biologists, park rangers, and volunteers. Every camera streams live,
            free, to anyone with an internet connection — and every animal that
            walks into frame is automatically catalogued and added to an open
            scientific dataset.
          </p>
          <p style={{ marginTop: 18 }}>
            We do not relocate, bait, or interfere with the wildlife we observe.
            The best cameras are the ones the animals forget are there.
          </p>
        </div>
      </section>

      <section className="ww-stats">
        <div><span className="n">412</span><span className="l">Cameras Live</span></div>
        <div><span className="n">38</span><span className="l">Countries</span></div>
        <div><span className="n">2,140</span><span className="l">Species Catalogued</span></div>
        <div><span className="n">4.6M</span><span className="l">Detections / yr</span></div>
      </section>

      <section className="ww-howit">
        <div>
          <span className="ww-eyebrow">Method</span>
          <h3>How a detection becomes a data point.</h3>
          <p style={{ color: "var(--ink-2)", marginTop: 14, maxWidth: "30ch" }}>
            A four-stage pipeline from photon to peer-reviewed dataset.
          </p>
        </div>
        <div className="ww-steps">
          <div className="ww-step">
            <span className="num">I.</span>
            <div>
              <h4>Edge detection</h4>
              <p>
                On-device computer vision flags motion and runs a lightweight
                species classifier (MegaDetector v5.1) before anything leaves the
                camera. Empty frames are discarded — bandwidth and battery stay low.
              </p>
            </div>
          </div>
          <div className="ww-step">
            <span className="num">II.</span>
            <div>
              <h4>Cloud classification</h4>
              <p>
                Candidate frames are uploaded to a second-stage model fine-tuned
                per region. Confidence below 70% is routed to volunteer reviewers
                from the Cornell Lab and iNaturalist communities.
              </p>
            </div>
          </div>
          <div className="ww-step">
            <span className="num">III.</span>
            <div>
              <h4>Biologist verification</h4>
              <p>
                A partner biologist reviews each species' weekly roll-up. Behavior
                notes (mating, hunting, herd movement) are added by hand before
                the week is closed.
              </p>
            </div>
          </div>
          <div className="ww-step">
            <span className="num">IV.</span>
            <div>
              <h4>Open dataset</h4>
              <p>
                Verified detections — timestamp, species, count, confidence,
                snapshot — are published under CC-BY 4.0 and mirrored to GBIF
                within 30 days. The full archive is free to download.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="ww-partners">
        <h3>Field partners</h3>
        <div className="ww-partner-grid">
          <div className="ww-partner">Kenya Wildlife Service</div>
          <div className="ww-partner">SANParks</div>
          <div className="ww-partner">Parks Canada</div>
          <div className="ww-partner">Norsk Polarinstitutt</div>
          <div className="ww-partner">AIMS Australia</div>
          <div className="ww-partner">Cornell Lab of Ornithology</div>
          <div className="ww-partner">WWF-Malaysia</div>
          <div className="ww-partner">Cloud Forest Trust</div>
          <div className="ww-partner">Northern Rangelands Trust</div>
          <div className="ww-partner">Conservation Intl.</div>
        </div>
      </section>
    </div>
  );
}

Object.assign(window, { MainPage, StreamPage, AboutPage });
