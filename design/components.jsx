// components.jsx — atomic components for WildWatch

function Placeholder({ label }) {
  return (
    <div className="ww-placeholder">
      <span>{label}</span>
    </div>
  );
}

// Detection overlay — variant selected via tweak
function DetectionOverlay({ stream, variant }) {
  if (!stream.detected) return null;
  const sp = SPECIES[stream.detected];
  const conf = Math.round((stream.confidence ?? 0.9) * 100);

  if (variant === "badge") {
    return (
      <div className="ww-frame">
        <div className="ww-frame-top">
          <span className="ww-live">Live</span>
          <span className="ww-det-badge">
            <span className="glyph">{sp.glyph}</span>
            {sp.name}
            <span className="conf">{conf}%</span>
          </span>
        </div>
        <div className="ww-frame-bot">
          <span></span>
          <span className="ww-tag-time">CAM·01 · 16:42</span>
        </div>
      </div>
    );
  }

  if (variant === "led") {
    return (
      <div className="ww-frame">
        <div className="ww-frame-top">
          <span className="ww-live">Live</span>
          <span className="ww-det-led">{sp.name}</span>
        </div>
        <div className="ww-frame-bot">
          <span></span>
          <span className="ww-tag-time">CAM·01 · 16:42</span>
        </div>
      </div>
    );
  }

  if (variant === "bbox") {
    const b = stream.bbox || { x: 0.3, y: 0.3, w: 0.4, h: 0.4 };
    return (
      <>
        <div
          className="ww-det-bbox"
          data-label={`${sp.name} · ${conf}%`}
          style={{
            left: `${b.x * 100}%`,
            top: `${b.y * 100}%`,
            width: `${b.w * 100}%`,
            height: `${b.h * 100}%`,
          }}
        >
          <div className="ww-bbox-corners">
            <span></span><span></span><span></span><span></span>
          </div>
        </div>
        <div className="ww-frame">
          <div className="ww-frame-top">
            <span className="ww-live">Live</span>
            <span></span>
          </div>
          <div className="ww-frame-bot">
            <span></span>
            <span className="ww-tag-time">CAM·01 · 16:42</span>
          </div>
        </div>
      </>
    );
  }

  if (variant === "pulse") {
    const p = stream.pulseAt || { x: 0.5, y: 0.5 };
    return (
      <>
        <div
          className="ww-det-pulse"
          style={{
            position: "absolute",
            left: `${p.x * 100}%`,
            top: `${p.y * 100}%`,
            transform: "translate(-50%,-50%)",
          }}
        >
          <span className="ring"><span className="dot"></span></span>
          <span className="lbl">{sp.name}</span>
        </div>
        <div className="ww-frame">
          <div className="ww-frame-top">
            <span className="ww-live">Live</span>
            <span></span>
          </div>
          <div className="ww-frame-bot">
            <span></span>
            <span className="ww-tag-time">CAM·01 · 16:42</span>
          </div>
        </div>
      </>
    );
  }
  return null;
}

function StreamMedia({ stream, variant, big }) {
  return (
    <div className={big ? "ww-bigmedia" : "ww-tile-media"}>
      <Placeholder label={stream.placeholder || "live feed"} />
      {stream.online ? (
        <DetectionOverlay stream={stream} variant={variant} />
      ) : (
        <div className="ww-frame">
          <div className="ww-frame-top">
            <span className="ww-live ww-offline">Offline</span>
            <span></span>
          </div>
          <div className="ww-frame-bot">
            <span></span>
            <span className="ww-tag-time" style={{ opacity: 0.6 }}>
              {stream.placeholder}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function Tile({ stream, variant, onOpen, dimmed }) {
  const sp = stream.detected ? SPECIES[stream.detected] : null;
  return (
    <article className={`ww-tile${dimmed ? " dim" : ""}`} onClick={() => onOpen?.(stream)}>
      <StreamMedia stream={stream} variant={variant} />
      <div className="ww-tile-info">
        <div>
          <h3 className="ww-tile-name">{stream.name}</h3>
          <div className="ww-tile-region">
            {HABITAT[stream.habitat]} · {stream.region}
          </div>
        </div>
        <div className="ww-tile-viewers">
          {stream.online ? (
            <>
              <span style={{ color: "var(--live)" }}>●</span>{" "}
              {stream.viewers.toLocaleString()} viewing
            </>
          ) : (
            <span style={{ opacity: 0.6 }}>offline</span>
          )}
        </div>
      </div>
      {sp && (
        <div
          style={{
            marginTop: 8,
            paddingLeft: 2,
            fontFamily: "var(--mono)",
            fontSize: 10.5,
            letterSpacing: "0.08em",
            color: "var(--accent-deep)",
            textTransform: "uppercase",
          }}
        >
          ▸ {sp.name}
          {stream.count > 1 ? ` · ×${stream.count}` : ""}
        </div>
      )}
    </article>
  );
}

Object.assign(window, { Placeholder, DetectionOverlay, StreamMedia, Tile });
