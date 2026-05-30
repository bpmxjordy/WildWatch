"""
HDOnTap Wildlife Camera Snapshot URL Extractor

This script visits each HDOnTap wildlife camera page, finds the snapshot URL
by inspecting network requests, and outputs the results as a CSV.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    python scrape_hdontap.py

Output:
    hdontap_cameras.csv — with columns: name, location, snapshot_url, stream_url
"""

import asyncio
import csv
import re
from playwright.async_api import async_playwright

# All known HDOnTap wildlife/nature cameras
# Format: (name, location, country_code, stream_path)
CAMERAS = [
    # African / International Wildlife
    ("Namibia Africa Waterhole", "Hardap Region, Namibia", "NA", "/stream/162979/"),
    ("UK White Stork Nest", "West Grinstead, England", "GB", "/stream/283808/"),
    ("Tennessee Elk", "Morley, Tennessee", "US", "/stream/359514/"),
    ("Montana Bison", "Malta, Montana", "US", "/stream/102875/"),
    ("Montana Grasslands Bison", "Malta, Montana", "US", "/stream/429152/"),
    ("SW Florida River Wildlife", "Southwest Florida", "US", "/stream/473717/"),
    ("Kodiak Alaska Brown Bears", "Kodiak, Alaska", "US", "/stream/710132/"),

    # Eagles
    ("PA Farm Country Eagles", "Pennsylvania", "US", "/stream/795150/"),
    ("Cardinal Land Eagles", "Cincinnati, Ohio", "US", "/stream/114839/"),
    ("VINS Eagles", "Quechee, Vermont", "US", "/stream/978254/"),
    ("West Michigan Eagles Nest", "Michigan", "US", "/stream/025882/"),
    ("NE Florida Eagles", "NE Florida", "US", "/stream/190216/"),
    ("Hanover Eagles", "Pennsylvania", "US", "/stream/204942/"),
    ("Hilton Head Island Eagles", "South Carolina", "US", "/stream/863293/"),

    # Owls
    ("North Carolina Barn Owls", "North Carolina", "US", "/stream/548562/"),
    ("Great Horned Owls Nest", "SW Florida", "US", "/stream/603901/"),
    ("Eastern Screech Owl", "Grapevine, Texas", "US", "/stream/117946/"),

    # Ospreys
    ("Mashpee Ospreys", "Massachusetts", "US", "/stream/237342/"),
    ("San Francisco Bay Osprey", "Richmond, California", "US", "/stream/202376/"),
    ("Golden Gate Ospreys", "Richmond, California", "US", "/stream/181512/"),
    ("City of Loveland Ospreys", "Colorado", "US", "/stream/557550/"),
    ("Coeur d'Alene Ospreys", "Idaho", "US", "/stream/579264/"),

    # Falcons
    ("Reston Town Center Falcons", "Reston, Virginia", "US", "/stream/271048/"),
    ("Richmond Virginia Falcons", "Richmond, Virginia", "US", "/stream/397338/"),
    ("PA Peregrine Falcons", "Harrisburg, PA", "US", "/stream/241333/"),
    ("Utica Falcons", "Utica, New York", "US", "/stream/252045/"),
    ("Briess Falcons", "Manitowoc, Wisconsin", "US", "/stream/205642/"),

    # Other Birds
    ("Red-Tailed Hawk", "San Diego, California", "US", "/stream/200137/"),
    ("Blackwater Raptor Nest", "Church Creek, Maryland", "US", "/stream/477623/"),
    ("Blackwater Waterfowl", "Church Creek, Maryland", "US", "/stream/205526/"),
    ("Hummingbird Feeders CA", "Los Angeles, California", "US", "/stream/630308/"),
    ("Bird Rehabilitation Pool", "Napa, California", "US", "/stream/214731/"),
    ("Bird Island Standley Lake", "Westminster, Colorado", "US", "/stream/104809/"),
    ("PA Snow Geese", "Newmanstown, PA", "US", "/stream/387619/"),
    ("Ohio Bird Feeder", "Akron, Ohio", "US", "/stream/799760/"),

    # Zoo / Aquarium
    ("Kelp Forest Birch Aquarium", "San Diego, California", "US", "/stream/162646/"),
    ("Reid Park Zoo Lions", "Tucson, Arizona", "US", "/stream/278524/"),
    ("Reid Park Zoo Elephants", "Tucson, Arizona", "US", "/stream/259797/"),
    ("Reid Park Zoo Giraffes", "Tucson, Arizona", "US", "/stream/129493/"),
    ("Reid Park Zoo Flamingos", "Tucson, Arizona", "US", "/stream/269273/"),
    ("Reid Park Zoo Bears", "Tucson, Arizona", "US", "/stream/295116/"),
    ("Reid Park Zoo Lemurs", "Tucson, Arizona", "US", "/stream/103166/"),
    ("Reid Park Zoo Sloth", "Tucson, Arizona", "US", "/stream/237339/"),
    ("Seadragons Birch Aquarium", "San Diego, California", "US", "/stream/249299/"),
    ("Red Wolves", "South Salem, New York", "US", "/stream/191785/"),
    ("Red Wolves Wolf Center", "South Salem, New York", "US", "/stream/696039/"),
    ("Black-Footed Ferret Cam 1", "Severance, Colorado", "US", "/stream/135660/"),
    ("Black-Footed Ferret Cam 2", "Severance, Colorado", "US", "/stream/714900/"),
]

BASE_URL = "https://www.hdontap.com"


async def extract_snapshot_id(page, name: str, path: str) -> str | None:
    """Visit an HDOnTap camera page and extract the snapshot URL from network traffic."""
    url = BASE_URL + path
    snapshot_url = None

    # Listen for network requests to find snapshot URLs
    async def handle_response(response):
        nonlocal snapshot_url
        req_url = response.url
        if "snapshot" in req_url and "hdontap.com" in req_url:
            snapshot_url = req_url

    page.on("response", handle_response)

    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Wait a bit for any lazy-loaded snapshot requests
        await page.wait_for_timeout(5000)
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")

    page.remove_listener("response", handle_response)

    # Also try to find snapshot URL in page source
    if not snapshot_url:
        try:
            content = await page.content()
            # Look for snapshot patterns in the HTML/JS
            patterns = [
                r'https?://portal\.hdontap\.com/snapshot/[a-zA-Z0-9_\-]+',
                r'snapshot["\s:=]+["\']([a-zA-Z0-9_\-]+)["\']',
                r'snapshotId["\s:=]+["\']([a-zA-Z0-9_\-]+)["\']',
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    found = match.group(0) if "http" in match.group(0) else None
                    if found:
                        snapshot_url = found
                        break
                    elif match.lastindex and match.lastindex >= 1:
                        snapshot_url = f"https://portal.hdontap.com/snapshot/{match.group(1)}"
                        break
        except Exception:
            pass

    return snapshot_url


async def main():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for i, (name, location, country_code, path) in enumerate(CAMERAS):
            print(f"[{i+1}/{len(CAMERAS)}] {name}...")
            snapshot_url = await extract_snapshot_id(page, name, path)

            if snapshot_url:
                print(f"  FOUND: {snapshot_url}")
                results.append({
                    "name": name,
                    "location": location,
                    "country_code": country_code,
                    "stream_page": BASE_URL + path,
                    "snapshot_url": snapshot_url,
                    "platform": "jpeg",
                })
            else:
                print(f"  NOT FOUND — may be offline or require different extraction")

        await browser.close()

    # Write CSV output
    output_file = "hdontap_cameras.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "location", "country_code", "stream_page", "snapshot_url", "platform"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"Done! Found {len(results)}/{len(CAMERAS)} snapshot URLs")
    print(f"Results saved to {output_file}")
    print(f"{'='*60}\n")

    # Also print as a ready-to-use list
    if results:
        print("Ready to add to WildWatch:")
        print("-" * 40)
        for r in results:
            print(f"  {r['name']}")
            print(f"    URL: {r['snapshot_url']}")
            print(f"    Location: {r['location']} ({r['country_code']})")
            print(f"    Platform: jpeg")
            print()


if __name__ == "__main__":
    asyncio.run(main())
