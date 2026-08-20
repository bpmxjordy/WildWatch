#!/usr/bin/env python3
"""Emergency cleanup for the `thumbnails` storage bucket.

The agent's built-in pruner (`uploader.prune_old_images`) calls Storage's
`list()` without pagination, so it only ever sees the first 100 objects per
camera folder while ~1,440 arrive per camera per day. This script pages through
every folder properly and clears the backlog.

Only timestamped snapshots (`YYYYMMDD_HHMMSS.jpg`) are ever considered for
deletion. `latest.jpg` -- which the stream cards point at -- and anything else
that doesn't match that pattern are always left alone.

Dry run by default; pass --apply to actually delete.

    python scripts/cleanup-storage.py                 # show what would go
    python scripts/cleanup-storage.py --days 2        # keep the last 2 days
    python scripts/cleanup-storage.py --apply         # delete (keeps 1 day)
    python scripts/cleanup-storage.py --all --apply   # delete every snapshot
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv
# NB: import ClientOptions from the package root -- `supabase.lib.client_options`
# also exports a base class of the same name that the sync client rejects.
from supabase import ClientOptions, create_client

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The agent keeps its credentials in agent/.env; fall back to the repo root.
for candidate in (os.path.join(REPO_ROOT, "agent", ".env"), os.path.join(REPO_ROOT, ".env")):
    if os.path.exists(candidate):
        load_dotenv(candidate)

SNAPSHOT_RE = re.compile(r"^(\d{8})_(\d{6})\.jpg$")

# Folders with tens of thousands of objects make Storage's list endpoint slow,
# so pages are kept modest and shrink further if the server times out anyway.
DEFAULT_PAGE_SIZE = 500
MIN_PAGE_SIZE = 50
REMOVE_CHUNK = 100


def human(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def list_page(bucket, path: str | None, limit: int, offset: int) -> list[dict]:
    """One list call, retrying on both transport timeouts and Storage's own
    DatabaseTimeout (statusCode 544), which comes back as a normal response
    rather than an httpx exception."""
    for attempt in range(6):
        try:
            return bucket.list(
                path,
                {
                    "limit": limit,
                    "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                },
            )
        except Exception as exc:  # noqa: BLE001 - transport and API errors alike
            if attempt == 5:
                raise
            if limit > MIN_PAGE_SIZE:
                limit = max(MIN_PAGE_SIZE, limit // 2)
            wait = 2**attempt
            print(f"    list({path or '/'}, offset={offset}) failed ({type(exc).__name__}); retrying with limit={limit} in {wait}s", file=sys.stderr, flush=True)
            time.sleep(wait)
    return []


def page_through(bucket, path: str | None, page_size: int) -> list[dict]:
    """List every entry under `path`, paging past Storage's 100-item default."""
    entries: list[dict] = []
    offset = 0
    limit = page_size

    while True:
        page = list_page(bucket, path, limit, offset)
        if not page:
            break
        entries.extend(page)
        if len(page) < limit:
            break
        offset += len(page)

    return entries


def drain_folder(bucket, folder: str, page_size: int, remove_chunk: int) -> tuple[int, int]:
    """Delete every object in `folder`, always listing from offset 0.

    Paging deep into a folder holding tens of thousands of objects is what
    trips Storage's DatabaseTimeout -- offset=20000 is expensive server-side.
    Since a purge deletes whatever it lists, re-reading the first page after
    each batch keeps every query cheap and terminates naturally.
    """
    deleted = 0
    freed = 0
    while True:
        page = list_page(bucket, folder, page_size, 0)
        names = [f"{folder}/{f['name']}" for f in page if f.get("name")]
        if not names:
            return deleted, freed
        freed += sum(entry_size(f) for f in page if f.get("name"))
        for i in range(0, len(names), remove_chunk):
            bucket.remove(names[i : i + remove_chunk])
            deleted += len(names[i : i + remove_chunk])
        print(f"      {deleted} deleted ({human(freed)})", flush=True)


def entry_size(entry: dict) -> int:
    meta = entry.get("metadata") or {}
    return int(meta.get("size") or 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bucket", default="thumbnails", help="storage bucket (default: thumbnails)")
    parser.add_argument("--days", type=float, default=1.0, help="keep snapshots newer than this many days (default: 1)")
    parser.add_argument("--all", action="store_true", help="delete every timestamped snapshot regardless of age")
    parser.add_argument("--purge", action="store_true", help="delete EVERY object in each folder, including latest.jpg")
    parser.add_argument("--exclude", action="append", default=None, help="folder to leave untouched; repeatable (default: reports)")
    parser.add_argument("--remove-chunk", type=int, default=REMOVE_CHUNK, help=f"objects per delete request (default: {REMOVE_CHUNK})")
    parser.add_argument("--apply", action="store_true", help="actually delete; without this it's a dry run")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help=f"objects per list request (default: {DEFAULT_PAGE_SIZE})")
    parser.add_argument("--timeout", type=int, default=180, help="storage HTTP timeout in seconds (default: 180)")
    parser.add_argument("--folder", action="append", help="only process this folder; repeatable")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY not found in agent/.env or .env", file=sys.stderr)
        return 1

    client = create_client(url, key, options=ClientOptions(storage_client_timeout=args.timeout))
    bucket = client.storage.from_(args.bucket)

    excluded = set(args.exclude if args.exclude is not None else ["reports"])

    cutoff = None if (args.all or args.purge) else datetime.now(timezone.utc) - timedelta(days=args.days)
    if args.purge:
        scope = "EVERY object, including latest.jpg"
    elif args.all:
        scope = "ALL timestamped snapshots"
    else:
        scope = f"snapshots older than {args.days:g} day(s) (before {cutoff:%Y-%m-%d %H:%M} UTC)"
    print(f"Bucket : {args.bucket}")
    print(f"Scope  : {scope}")
    print(f"Exclude: {', '.join(sorted(excluded)) if excluded else '(nothing)'}")
    print(f"Mode   : {'APPLY -- deleting' if args.apply else 'DRY RUN -- nothing will be deleted'}\n")

    if args.folder:
        folders = args.folder
    else:
        folders = [f["name"] for f in page_through(bucket, None, args.page_size) if f.get("name")]
    if not folders:
        print("Bucket is empty.")
        return 0
    print(f"Scanning {len(folders)} folder(s)...\n")

    total_matched = total_kept = total_deleted = 0
    total_bytes = 0
    failures: list[str] = []

    for folder in folders:
        if folder in excluded:
            print(f"  {folder:<44} skipped (excluded)", flush=True)
            continue

        # A purge deletes everything, so drain from the top rather than paging
        # deep -- large offsets are what trip Storage's DatabaseTimeout.
        if args.purge and args.apply:
            print(f"  {folder:<44} draining...", flush=True)
            try:
                deleted, freed = drain_folder(bucket, folder, args.page_size, args.remove_chunk)
            except Exception as exc:  # noqa: BLE001 - report and move to the next folder
                failures.append(f"{folder}: {exc}")
                print(f"  {folder:<44} FAILED: {type(exc).__name__}", file=sys.stderr, flush=True)
                continue
            total_deleted += deleted
            total_matched += deleted
            total_bytes += freed
            continue

        files = page_through(bucket, folder, args.page_size)
        doomed: list[str] = []
        folder_bytes = 0
        kept = 0

        for f in files:
            name = f.get("name", "")
            if not name:
                continue
            match = SNAPSHOT_RE.match(name)
            if not match and not args.purge:
                kept += 1  # latest.jpg and anything unrecognised
                continue
            if cutoff is not None and match:
                try:
                    stamp = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                except ValueError:
                    kept += 1
                    continue
                if stamp >= cutoff:
                    kept += 1
                    continue
            doomed.append(f"{folder}/{name}")
            folder_bytes += entry_size(f)

        total_matched += len(doomed)
        total_kept += kept
        total_bytes += folder_bytes

        if not doomed:
            print(f"  {folder:<44} {len(files):>6} files, nothing to remove", flush=True)
            continue

        print(f"  {folder:<44} {len(doomed):>6} to remove ({human(folder_bytes)}), {kept} kept", flush=True)

        if not args.apply:
            continue

        for i in range(0, len(doomed), args.remove_chunk):
            chunk = doomed[i : i + args.remove_chunk]
            try:
                bucket.remove(chunk)
                total_deleted += len(chunk)
                done = min(i + len(chunk), len(doomed))
                if done % (args.remove_chunk * 10) == 0 or done == len(doomed):
                    print(f"      {done}/{len(doomed)}", flush=True)
            except Exception as exc:  # noqa: BLE001 - keep going, report at the end
                failures.append(f"{folder} [{i}:{i + len(chunk)}]: {exc}")

    print()
    if args.apply:
        print(f"Deleted {total_deleted} of {total_matched} objects, reclaiming ~{human(total_bytes)}.")
        if failures:
            print(f"\n{len(failures)} chunk(s) failed:", file=sys.stderr)
            for msg in failures[:10]:
                print(f"  {msg}", file=sys.stderr)
            return 1
    else:
        print(f"Would delete {total_matched} objects, reclaiming ~{human(total_bytes)}.")
        print(f"Would keep {total_kept} (latest.jpg and in-window snapshots).")
        if total_matched:
            flags = " --all" if args.all else f" --days {args.days:g}"
            print(f"\nRe-run with --apply to delete:\n  python scripts/cleanup-storage.py{flags} --apply")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
