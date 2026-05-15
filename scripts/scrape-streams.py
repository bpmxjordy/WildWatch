"""Helper to validate wildlife livestream URLs and check if they're live."""

import subprocess
import sys
import json


def check_stream(url: str) -> dict:
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return {"url": url, "status": "error", "error": result.stderr.strip()[:200]}

        info = json.loads(result.stdout)
        return {
            "url": url,
            "status": "live" if info.get("is_live") else "not_live",
            "title": info.get("title", ""),
            "channel": info.get("channel", ""),
            "thumbnail": info.get("thumbnail", ""),
        }
    except subprocess.TimeoutExpired:
        return {"url": url, "status": "timeout"}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape-streams.py <url1> [url2] ...")
        print("  Checks if YouTube/stream URLs are live and extracts metadata.")
        sys.exit(1)

    for url in sys.argv[1:]:
        result = check_stream(url)
        print(json.dumps(result, indent=2))
        print()


if __name__ == "__main__":
    main()
