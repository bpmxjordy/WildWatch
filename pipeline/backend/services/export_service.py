"""PDF report generation with rich charts and stats."""
from __future__ import annotations

import base64
import io
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

from extensions import db
from models.detection import Detection
from models.stream import Stream

logger = logging.getLogger(__name__)

RANGE_MAP = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

COLORS = ["#2d7d2d", "#0d9488", "#1565c0", "#6a1b9a", "#ad1457",
          "#e65100", "#3e2723", "#263238", "#558b2f", "#00838f"]


def generate_report(project, range_param: str = "7d") -> bytes:
    from weasyprint import HTML

    delta = RANGE_MAP.get(range_param)
    cutoff = (datetime.now(timezone.utc) - delta) if delta else None
    range_label = {"24h": "24 Hours", "7d": "7 Days", "30d": "30 Days"}.get(range_param, "All Time")

    streams = Stream.query.filter_by(project_id=project.id).all()
    stream_ids = [s.id for s in streams]

    query = Detection.query.filter(Detection.stream_id.in_(stream_ids))
    if cutoff:
        query = query.filter(Detection.detected_at >= cutoff)
    detections = query.order_by(Detection.detected_at.desc()).all()

    # Aggregate stats
    species_counts = Counter()
    species_confidence = defaultdict(list)
    hourly_counts = defaultdict(int)
    dow_hour_counts = defaultdict(int)
    hourly_dist = defaultdict(int)
    stream_det_counts = defaultdict(int)
    stream_species = defaultdict(set)
    daily_counts = defaultdict(int)

    for d in detections:
        name = d.common_name or d.species_label or "Unknown"
        species_counts[name] += 1
        if d.confidence:
            species_confidence[name].append(d.confidence)
        if d.detected_at:
            hour_key = d.detected_at.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] += 1
            dow_hour_counts[(d.detected_at.weekday(), d.detected_at.hour)] += 1
            hourly_dist[d.detected_at.hour] += 1
            daily_counts[d.detected_at.date()] += 1
        stream_det_counts[d.stream_id] += 1
        if d.common_name:
            stream_species[d.stream_id].add(d.common_name)

    stream_stats = []
    for s in streams:
        stream_stats.append({
            "name": s.name, "location": s.location_name or "—",
            "platform": s.platform, "status": s.status,
            "detections": stream_det_counts.get(s.id, 0),
            "species": len(stream_species.get(s.id, set())),
        })
    stream_stats.sort(key=lambda x: x["detections"], reverse=True)

    # Generate all charts
    timeline_img = _chart_timeline(hourly_counts, range_label)
    species_pie_img = _chart_species_pie(species_counts)
    species_bar_img = _chart_species_bar(species_counts, species_confidence)
    heatmap_img = _chart_heatmap(dow_hour_counts)
    hourly_dist_img = _chart_hourly_distribution(hourly_dist)
    daily_trend_img = _chart_daily_trend(daily_counts, range_label)
    confidence_img = _chart_confidence_distribution(detections)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(detections)
    avg_per_day = total / max(1, len(daily_counts))
    peak_hour = max(hourly_dist.items(), key=lambda x: x[1])[0] if hourly_dist else "—"
    peak_hour_label = f"{peak_hour}:00" if isinstance(peak_hour, int) else peak_hour

    html = f"""<!DOCTYPE html><html><head><style>
    @page {{ margin: 1.5cm; size: A4; }}
    body {{ font-family: 'Helvetica','Arial',sans-serif; color: #1a1a1a; font-size: 10px; line-height: 1.5; }}
    h1 {{ color: #2d7d2d; font-size: 22px; margin: 0 0 2px; }}
    h2 {{ color: #2d7d2d; font-size: 14px; margin: 18px 0 6px; border-bottom: 2px solid #d4f0d4; padding-bottom: 3px; }}
    .subtitle {{ color: #6b7280; font-size: 11px; margin-bottom: 16px; }}
    .stats-row {{ display: flex; gap: 10px; margin: 12px 0; }}
    .stat {{ background: #f0faf0; border: 1px solid #d4f0d4; border-radius: 6px; padding: 10px 14px; flex: 1; text-align: center; }}
    .stat .num {{ font-size: 22px; font-weight: 700; color: #2d7d2d; }}
    .stat .lbl {{ font-size: 8px; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7280; margin-top: 2px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0; font-size: 9px; }}
    th {{ background: #f9fafb; text-align: left; padding: 5px 8px; font-size: 8px; text-transform: uppercase; letter-spacing: 0.05em; color: #6b7280; border-bottom: 1px solid #e5e5e5; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #f0f0f0; }}
    .chart {{ text-align: center; margin: 10px 0; }}
    .chart img {{ max-width: 100%; height: auto; }}
    .two-col {{ display: flex; gap: 12px; }}
    .two-col > div {{ flex: 1; }}
    .badge {{ display: inline-block; padding: 1px 5px; border-radius: 3px; font-size: 8px; font-weight: 600; }}
    .badge-green {{ background: #d4f0d4; color: #2d7d2d; }}
    .badge-red {{ background: #fee2e2; color: #b91c1c; }}
    .badge-gray {{ background: #f3f4f6; color: #6b7280; }}
    .footer {{ margin-top: 20px; padding-top: 8px; border-top: 1px solid #e5e5e5; font-size: 8px; color: #9ca3af; text-align: center; }}
    .page-break {{ page-break-before: always; }}
    </style></head><body>

    <h1>WildSight Detection Report</h1>
    <p class="subtitle">{project.name} &mdash; {range_label} &mdash; Generated {now_str}</p>

    <div class="stats-row">
      <div class="stat"><div class="num">{total}</div><div class="lbl">Total Detections</div></div>
      <div class="stat"><div class="num">{len(species_counts)}</div><div class="lbl">Unique Species</div></div>
      <div class="stat"><div class="num">{len(streams)}</div><div class="lbl">Streams</div></div>
      <div class="stat"><div class="num">{avg_per_day:.1f}</div><div class="lbl">Avg/Day</div></div>
      <div class="stat"><div class="num">{peak_hour_label}</div><div class="lbl">Peak Hour</div></div>
    </div>

    <h2>Activity Timeline</h2>
    <div class="chart"><img src="data:image/png;base64,{timeline_img}"></div>

    <h2>Daily Trend</h2>
    <div class="chart"><img src="data:image/png;base64,{daily_trend_img}"></div>

    <div class="two-col">
      <div><h2>Species Distribution</h2><div class="chart"><img src="data:image/png;base64,{species_pie_img}"></div></div>
      <div><h2>Species Counts &amp; Confidence</h2><div class="chart"><img src="data:image/png;base64,{species_bar_img}"></div></div>
    </div>

    <div class="page-break"></div>

    <div class="two-col">
      <div><h2>Activity Heatmap</h2><p style="font-size:8px;color:#6b7280;">Day of week vs hour of day</p><div class="chart"><img src="data:image/png;base64,{heatmap_img}"></div></div>
      <div><h2>Peak Hours</h2><p style="font-size:8px;color:#6b7280;">When are animals most active?</p><div class="chart"><img src="data:image/png;base64,{hourly_dist_img}"></div></div>
    </div>

    <h2>Confidence Distribution</h2>
    <div class="chart"><img src="data:image/png;base64,{confidence_img}"></div>

    <h2>Stream Performance</h2>
    <table><thead><tr><th>Stream</th><th>Location</th><th>Platform</th><th>Status</th><th style="text-align:right">Detections</th><th style="text-align:right">Species</th></tr></thead><tbody>"""

    for ss in stream_stats:
        badge = "badge-green" if ss["status"] == "running" else "badge-red" if ss["status"] in ("error","offline") else "badge-gray"
        html += f'<tr><td><b>{ss["name"]}</b></td><td>{ss["location"]}</td><td><span class="badge badge-gray">{ss["platform"]}</span></td><td><span class="badge {badge}">{ss["status"]}</span></td><td style="text-align:right">{ss["detections"]}</td><td style="text-align:right">{ss["species"]}</td></tr>'

    html += """</tbody></table><h2>Species Summary</h2>
    <table><thead><tr><th>Species</th><th style="text-align:right">Count</th><th style="text-align:right">% of Total</th><th style="text-align:right">Avg Confidence</th></tr></thead><tbody>"""

    for name, count in species_counts.most_common():
        pct = count / max(total, 1) * 100
        avg_c = sum(species_confidence[name]) / len(species_confidence[name]) if species_confidence[name] else 0
        html += f'<tr><td>{name}</td><td style="text-align:right">{count}</td><td style="text-align:right">{pct:.1f}%</td><td style="text-align:right">{avg_c:.0%}</td></tr>'

    html += f'</tbody></table><div class="footer">WildSight Detection Pipeline &mdash; {now_str}</div></body></html>'

    return HTML(string=html).write_pdf()


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _empty_chart(msg: str) -> str:
    fig, ax = plt.subplots(figsize=(4, 2))
    ax.text(0.5, 0.5, msg, ha="center", va="center", fontsize=10, color="#9ca3af")
    ax.axis("off")
    return _fig_to_b64(fig)


def _chart_timeline(hourly_counts, range_label):
    if not hourly_counts:
        return _empty_chart("No activity data")
    hours = sorted(hourly_counts.keys())
    counts = [hourly_counts[h] for h in hours]
    fig, ax = plt.subplots(figsize=(7, 2.2))
    ax.bar(hours, counts, width=0.03, color="#2d7d2d", alpha=0.7)
    ax.set_ylabel("Detections", fontsize=8)
    ax.set_title(f"Hourly Activity ({range_label})", fontsize=10, fontweight="bold")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(axis="y", alpha=0.3)
    return _fig_to_b64(fig)


def _chart_daily_trend(daily_counts, range_label):
    if not daily_counts:
        return _empty_chart("No daily data")
    days = sorted(daily_counts.keys())
    counts = [daily_counts[d] for d in days]
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.fill_between(days, counts, alpha=0.3, color="#2d7d2d")
    ax.plot(days, counts, color="#2d7d2d", linewidth=1.5)
    ax.set_ylabel("Detections", fontsize=8)
    ax.set_title(f"Daily Trend ({range_label})", fontsize=10, fontweight="bold")
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.autofmt_xdate()
    return _fig_to_b64(fig)


def _chart_species_pie(species_counts):
    if not species_counts:
        return _empty_chart("No species data")
    top = species_counts.most_common(8)
    names = [n for n, _ in top]
    counts = [c for _, c in top]
    fig, ax = plt.subplots(figsize=(3.5, 3))
    ax.pie(counts, labels=names, colors=COLORS[:len(names)], autopct="%1.0f%%",
           textprops={"fontsize": 7}, startangle=90)
    ax.set_title("Species Distribution", fontsize=10, fontweight="bold")
    return _fig_to_b64(fig)


def _chart_species_bar(species_counts, species_confidence):
    if not species_counts:
        return _empty_chart("No species data")
    top = species_counts.most_common(10)
    names = [n for n, _ in top]
    counts = [c for _, c in top]
    confs = [sum(species_confidence[n])/len(species_confidence[n]) if species_confidence[n] else 0 for n in names]

    fig, ax1 = plt.subplots(figsize=(3.5, 3))
    y_pos = range(len(names))
    ax1.barh(y_pos, counts, color="#2d7d2d", alpha=0.7, height=0.6)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names, fontsize=7)
    ax1.set_xlabel("Count", fontsize=8)
    ax1.invert_yaxis()

    ax2 = ax1.twiny()
    ax2.plot(confs, y_pos, "o-", color="#e65100", markersize=3, linewidth=1)
    ax2.set_xlabel("Avg Confidence", fontsize=7, color="#e65100")
    ax2.set_xlim(0, 1)
    ax2.tick_params(axis="x", labelsize=6, colors="#e65100")
    ax1.set_title("Count & Confidence", fontsize=9, fontweight="bold", pad=20)
    return _fig_to_b64(fig)


def _chart_heatmap(dow_hour_counts):
    if not dow_hour_counts:
        return _empty_chart("No heatmap data")
    grid = np.zeros((7, 24))
    for (dow, hour), count in dow_hour_counts.items():
        grid[dow][hour] = count
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    im = ax.imshow(grid, cmap="YlGn", aspect="auto")
    ax.set_yticks(range(7))
    ax.set_yticklabels(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], fontsize=7)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 3)], fontsize=6)
    ax.set_xlabel("Hour", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Detections")
    ax.set_title("Day x Hour Heatmap", fontsize=9, fontweight="bold")
    return _fig_to_b64(fig)


def _chart_hourly_distribution(hourly_dist):
    if not hourly_dist:
        return _empty_chart("No hourly data")
    hours = list(range(24))
    counts = [hourly_dist.get(h, 0) for h in hours]
    max_c = max(counts) if counts else 1
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    colors_list = [plt.cm.YlGn(0.3 + 0.7 * c / max(max_c, 1)) for c in counts]
    ax.bar(hours, counts, color=colors_list, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Hour of Day", fontsize=7)
    ax.set_ylabel("Detections", fontsize=7)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xticklabels([f"{h:02d}" for h in range(0, 24, 2)], fontsize=6)
    ax.tick_params(axis="y", labelsize=6)
    ax.grid(axis="y", alpha=0.3)
    ax.set_title("Peak Hours", fontsize=9, fontweight="bold")
    return _fig_to_b64(fig)


def _chart_confidence_distribution(detections):
    confs = [d.confidence for d in detections if d.confidence]
    if not confs:
        return _empty_chart("No confidence data")
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.hist(confs, bins=20, color="#2d7d2d", alpha=0.7, edgecolor="white")
    mean_c = sum(confs)/len(confs)
    ax.axvline(mean_c, color="#e65100", linestyle="--", linewidth=1, label=f"Mean: {mean_c:.0%}")
    ax.set_xlabel("Confidence", fontsize=8)
    ax.set_ylabel("Count", fontsize=8)
    ax.set_title("Detection Confidence Distribution", fontsize=10, fontweight="bold")
    ax.legend(fontsize=7)
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(axis="y", alpha=0.3)
    return _fig_to_b64(fig)
