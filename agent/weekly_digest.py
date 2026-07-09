"""
Generate a "Weekly Wild Report" from the pre-computed stream_stats table.

Reads the 7-day activity window across all active cameras and produces:
  1. A LinkedIn-ready text digest (printed + saved to digest_output/)
  2. A branded square stat-card PNG for the post image

Usage:
    python weekly_digest.py            # text + image
    python weekly_digest.py --no-image # text only

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (same as the agent).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from supabase import create_client

from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "digest_output")
SITE_URL = "thewildwatch.vercel.app"

# Compact species -> emoji map (mirrors the web app's SPECIES_EMOJI).
SPECIES_EMOJI = {
    "polar bear": "🐻‍❄️", "bear": "🐻", "deer": "🦌", "eagle": "🦅", "owl": "🦉",
    "wolf": "🐺", "elephant": "🐘", "lion": "🦁", "panda": "🐼", "penguin": "🐧",
    "heron": "🪿", "hawk": "🦅", "fox": "🦊", "rabbit": "🐇", "raccoon": "🦝",
    "moose": "🫎", "bison": "🦬", "whale": "🐋", "dolphin": "🐬", "turtle": "🐢",
    "fish": "🐟", "bird": "🐦", "osprey": "🦅", "jellyfish": "🪼", "koala": "🐨",
    "manatee": "🦭", "puffin": "🐦", "falcon": "🦅", "rhino": "🦏", "zebra": "🦓",
    "gorilla": "🦍", "flamingo": "🦩", "lemur": "🐒", "giraffe": "🦒", "hippo": "🦛",
    "leopard": "🐆", "cheetah": "🐆", "otter": "🦦", "goat": "🐐", "elk": "🫎",
}


def species_emoji(name: str | None) -> str:
    if not name:
        return "🐾"
    lower = name.lower()
    for key, emoji in SPECIES_EMOJI.items():
        if key in lower:
            return emoji
    return "🐾"


def fmt_hour(h: int) -> str:
    ampm = "AM" if h < 12 else "PM"
    hh = h % 12 or 12
    return f"{hh}{ampm}"


def utc_offset(longitude: float | None) -> int:
    if longitude is None:
        return 0
    return round(longitude / 15)


def peak_window(hourly: list[int], longitude: float | None) -> str | None:
    """Return a human 2-hour window (local time) for the busiest stretch."""
    if not hourly or sum(hourly) == 0:
        return None
    offset = utc_offset(longitude)
    # Shift UTC hourly into local hours
    local = [0] * 24
    for utc_h, v in enumerate(hourly):
        local[(utc_h + offset) % 24] += v
    # Find the best 2-hour window
    best_start, best_sum = 0, -1
    for start in range(24):
        s = local[start] + local[(start + 1) % 24]
        if s > best_sum:
            best_sum, best_start = s, start
    return f"{fmt_hour(best_start)}–{fmt_hour((best_start + 2) % 24)}"


def load_stats(supabase) -> tuple[list[dict], dict[str, dict]]:
    streams = (
        supabase.table("streams")
        .select("id, name, slug, location_name, longitude, latest_detection_thumbnail_url")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )
    stats_rows = supabase.table("stream_stats").select("*").execute().data or []
    stats_by_id: dict[str, dict] = {}
    for row in stats_rows:
        raw = row["stats"]
        stats_by_id[row["stream_id"]] = json.loads(raw) if isinstance(raw, str) else raw
    return streams, stats_by_id


def build_digest(streams: list[dict], stats_by_id: dict[str, dict]) -> dict:
    """Aggregate the 7-day window into a set of report figures."""
    week_total = 0
    species_totals: dict[str, int] = {}
    most_active = None  # (total, stream, its 7d stats)
    active_cameras = 0

    for s in streams:
        st = stats_by_id.get(s["id"])
        wk = (st or {}).get("7d")
        if not wk:
            continue
        total = wk.get("total", 0)
        if total > 0:
            active_cameras += 1
        week_total += total
        for sp in wk.get("species", []):
            species_totals[sp["common_name"]] = (
                species_totals.get(sp["common_name"], 0) + sp["count"]
            )
        if most_active is None or total > most_active[0]:
            most_active = (total, s, wk)

    top_species = sorted(species_totals.items(), key=lambda kv: kv[1], reverse=True)

    insight = None
    if most_active and most_active[0] > 0:
        _, cam, wk = most_active
        cam_species = wk.get("species", [])
        window = peak_window(wk.get("hourly", []), cam.get("longitude"))
        if cam_species and window:
            sp_name = cam_species[0]["common_name"]
            insight = (
                f"{species_emoji(sp_name)} At {cam['name']}, {sp_name} activity "
                f"peaked around {window}."
            )
        elif window:
            insight = f"🔥 {cam['name']} was busiest around {window}."

    return {
        "week_total": week_total,
        "distinct_species": len(species_totals),
        "active_cameras": active_cameras,
        "total_cameras": len(streams),
        "most_active_name": most_active[1]["name"] if most_active else None,
        "most_active_total": most_active[0] if most_active else 0,
        "most_active_thumb": most_active[1].get("latest_detection_thumbnail_url") if most_active else None,
        "top_species": top_species[:5],
        "insight": insight,
    }


def render_text(d: dict, date_range: str) -> str:
    lines = [
        f"🌍 WildWatch Weekly Wild Report — {date_range}",
        "",
        f"This week across {d['active_cameras']} active wildlife cameras:",
        "",
        f"📸 {d['week_total']:,} detections",
        f"🦋 {d['distinct_species']} species identified",
    ]
    if d["most_active_name"]:
        lines.append(
            f"🔥 Most active: {d['most_active_name']} "
            f"({d['most_active_total']:,} detections)"
        )
    if d["insight"]:
        lines += ["", d["insight"]]
    if d["top_species"]:
        lines += ["", "Top species this week:"]
        for i, (name, count) in enumerate(d["top_species"], 1):
            lines.append(f"{i}. {species_emoji(name)} {name} — {count:,}")
    lines += [
        "",
        f"Watch it live 👉 {SITE_URL}",
        "",
        "#WildWatch #Wildlife #Conservation #ComputerVision #ConservationTech",
    ]
    return "\n".join(lines)


def render_image(d: dict, date_range: str, path: str) -> bool:
    """Best-effort branded stat card. Returns True on success."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False

    W = H = 1080
    bg = (12, 19, 12)
    accent = (125, 184, 106)
    ink = (238, 245, 233)
    muted = (143, 176, 133)

    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    def font(size: int, bold: bool = False):
        candidates = (
            [
                r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
            ]
            + [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
                if bold
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
            ]
        )
        for c in candidates:
            try:
                return ImageFont.truetype(c, size)
            except (OSError, IOError):
                continue
        return ImageFont.load_default()

    # Subtle radial glow top
    for r in range(400, 0, -8):
        alpha = int(18 * (r / 400))
        draw.ellipse(
            [W / 2 - r, -r + 120, W / 2 + r, r + 120],
            fill=(bg[0] + alpha // 3, bg[1] + alpha, bg[2] + alpha // 3),
        )

    # Header
    draw.text((80, 90), "WILDWATCH", font=font(52, bold=True), fill=ink)
    draw.text((80, 158), "WEEKLY WILD REPORT", font=font(26, bold=True), fill=accent)
    draw.text((80, 200), date_range, font=font(22), fill=muted)
    draw.line([(80, 250), (W - 80, 250)], fill=(40, 60, 40), width=2)

    # Big stats
    stats = [
        (f"{d['week_total']:,}", "DETECTIONS"),
        (str(d["distinct_species"]), "SPECIES"),
        (str(d["active_cameras"]), "ACTIVE CAMS"),
    ]
    y = 300
    for value, label in stats:
        draw.text((80, y), value, font=font(72, bold=True), fill=accent)
        draw.text((80, y + 88), label, font=font(24, bold=True), fill=muted)
        y += 150

    # Top species
    draw.text((80, y + 10), "TOP SPECIES", font=font(24, bold=True), fill=muted)
    y += 55
    for i, (name, count) in enumerate(d["top_species"][:4], 1):
        draw.text((80, y), f"{i}.  {name}", font=font(30), fill=ink)
        draw.text((W - 80, y), f"{count:,}", font=font(30, bold=True), fill=accent, anchor="ra")
        y += 48

    # Footer
    draw.text((80, H - 80), SITE_URL, font=font(26, bold=True), fill=accent)

    img.save(path, "PNG")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-image", action="store_true", help="Skip the stat-card image")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    streams, stats_by_id = load_stats(supabase)

    if not stats_by_id:
        print(
            "No stream_stats found yet. Start the agent so it runs its daily "
            "maintenance pass, then try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    date_range = f"{start.strftime('%b %d')}–{now.strftime('%b %d, %Y')}"

    d = build_digest(streams, stats_by_id)
    text = render_text(d, date_range)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = now.strftime("%Y%m%d")
    txt_path = os.path.join(OUTPUT_DIR, f"weekly_digest_{stamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")
    print(f"Saved text  -> {txt_path}")

    if not args.no_image:
        img_path = os.path.join(OUTPUT_DIR, f"weekly_digest_{stamp}.png")
        if render_image(d, date_range, img_path):
            print(f"Saved image -> {img_path}")
        else:
            print("Image skipped (Pillow unavailable).")


if __name__ == "__main__":
    main()
