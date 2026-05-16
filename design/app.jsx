// app.jsx — WildWatch shell

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "palette": "ivory",
  "density": "comfy",
  "detection": "badge"
}/*EDITMODE-END*/;

function TopBar({ page, onNav, liveCount }) {
  return (
    <header className="ww-topbar">
      <div className="ww-topbar-inner">
        <div className="ww-brand">
          <span className="ww-mark">Wild<i>Watch</i></span>
          <span className="ww-mark-sub">Est. 2019 · Field network</span>
        </div>
        <nav className="ww-nav">
          <a
            className="ww-nav-item"
            aria-current={page === "main" || page === "stream"}
            onClick={() => onNav("main")}
          >
            Live cameras
          </a>
          <a
            className="ww-nav-item"
            aria-current={page === "about"}
            onClick={() => onNav("about")}
          >
            About
          </a>
        </nav>
        <div className="ww-topstat">
          <span><span className="live-dot"></span>{liveCount} cameras live</span>
          <span>16:42 UTC</span>
        </div>
      </div>
    </header>
  );
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [page, setPage] = React.useState("main");
  const [activeStream, setActiveStream] = React.useState(null);

  // Apply palette via data attribute on body
  React.useEffect(() => {
    document.body.dataset.palette = t.palette;
  }, [t.palette]);

  const liveCount = STREAMS.filter((s) => s.online).length;

  const openStream = (s) => {
    setActiveStream(s);
    setPage("stream");
    window.scrollTo({ top: 0 });
  };

  let pageEl;
  if (page === "main") {
    pageEl = (
      <div data-screen-label="01 All cameras">
        <MainPage tweaks={t} onOpenStream={openStream} />
      </div>
    );
  } else if (page === "stream") {
    pageEl = (
      <div data-screen-label="02 Stream detail">
        <StreamPage
          stream={activeStream || STREAMS.find((s) => s.featured)}
          tweaks={t}
          onBack={() => setPage("main")}
        />
      </div>
    );
  } else {
    pageEl = (
      <div data-screen-label="03 About">
        <AboutPage />
      </div>
    );
  }

  return (
    <div className="ww-app">
      <TopBar
        page={page}
        onNav={(p) => { setPage(p); window.scrollTo({ top: 0 }); }}
        liveCount={liveCount}
      />
      {pageEl}
      <footer className="ww-foot">
        <b>WildWatch</b> · open wildlife camera network · {STREAMS.length} cameras · CC-BY 4.0 dataset
      </footer>

      <TweaksPanel>
        <TweakSection label="Palette" />
        <TweakSelect
          label="Theme"
          value={t.palette}
          options={[
            { value: "ivory", label: "Ivory Field" },
            { value: "sage",  label: "Sage Forest" },
            { value: "night", label: "Midnight Expedition" },
          ]}
          onChange={(v) => setTweak("palette", v)}
        />

        <TweakSection label="Grid" />
        <TweakRadio
          label="Density"
          value={t.density}
          options={["comfy", "dense"]}
          onChange={(v) => setTweak("density", v)}
        />

        <TweakSection label="Detection indicator" />
        <TweakSelect
          label="Style"
          value={t.detection}
          options={[
            { value: "badge", label: "Badge · pill + name" },
            { value: "led", label: "LED · pulsing dot" },
            { value: "bbox", label: "Bounding box · overlay" },
            { value: "pulse", label: "Pulse · ring + label" },
          ]}
          onChange={(v) => setTweak("detection", v)}
        />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
