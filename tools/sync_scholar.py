#!/usr/bin/env python3
"""Fetch public citation counts from the linked Google Scholar profile.

Google Scholar may return a CAPTCHA or rate-limit automated requests. In that
case the script exits successfully without replacing the last known counts.
This protects the published site from losing data due to a transient block.
"""

from __future__ import annotations

import json
import re
import sys
import argparse
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen


PROFILE_URL = "https://scholar.google.com/citations?user=73trMQkAAAAJ&hl=en"

def normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def load_json(path: Path) -> dict:
    """Read a prior snapshot without letting a transient source error erase it."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def scholar_summary(source: str) -> dict:
    """Extract the public profile totals and yearly citation series."""
    values = re.findall(r'class="gsc_rsb_std"[^>]*>\s*([\d,]+)', source)
    summary: dict = {}
    # Scholar renders two columns (all / since 2021) for each metric.  The
    # first column of the three rows is therefore at offsets 0, 2, and 4.
    if len(values) >= 6:
        summary["citations"] = int(values[0].replace(",", ""))
        summary["hindex"] = int(values[2].replace(",", ""))
        summary["i10index"] = int(values[4].replace(",", ""))

    # The public profile graph has one label and count pair per calendar year.
    years = {}
    graph = re.findall(
        r'class="gsc_g_t"[^>]*>\s*(\d{4})\s*</span>.*?class="gsc_g_al"[^>]*>\s*([\d,]+)',
        source,
        flags=re.DOTALL,
    )
    for year, count in graph:
        years[year] = int(count.replace(",", ""))
    if len(years) >= 3:
        summary["years"] = years
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="docs/data/publications.json")
    parser.add_argument("--summary", default="res/scholar.json")
    args = parser.parse_args()
    path = Path(args.file)
    request = Request(PROFILE_URL, headers={"User-Agent": "Mozilla/5.0 (compatible; JiayiMaHomepageBot/1.0)"})
    try:
        with urlopen(request, timeout=45) as response:
            source = response.read().decode("utf-8", errors="replace")
    except Exception as error:
        print(f"Scholar unavailable; preserving previous citation counts ({error}).")
        return 2
    if "captcha" in source.lower() or "not a robot" in source.lower():
        print("Scholar challenged this run; preserving previous citation counts.")
        return 2

    # The profile's public listing has rows with gsc_a_at (title) and gsc_a_ac
    # (citation count). This intentionally updates only exact-normalised matches.
    matches = re.findall(
        r'class="gsc_a_at"[^>]*>(.*?)</a>.*?class="gsc_a_ac[^>]*>(.*?)</a>',
        source,
        flags=re.DOTALL,
    )
    counts = {}
    for raw_title, raw_count in matches:
        title = re.sub(r"<.*?>", "", unescape(raw_title)).strip()
        count = re.sub(r"\D", "", unescape(raw_count))
        if title and count:
            counts[normalise(title)] = int(count)
    if not counts:
        print("Scholar response contained no publication counts; preserving previous values.")
        return 2

    content = load_json(path)
    if not content.get("publications"):
        print("Publication data is missing; preserving existing Scholar summary.")
        return 0
    updated = 0
    for publication in content["publications"]:
        title_match = re.search(r'"(.+?)"', publication["citation"])
        if not title_match:
            continue
        count = counts.get(normalise(title_match.group(1)))
        if count is not None:
            publication["citations"] = count
            updated += 1
    content["citationSyncedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path = Path(args.summary)
    summary = scholar_summary(source)
    if summary:
        summary["syncedAt"] = content["citationSyncedAt"]
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Updated public Scholar profile summary.")
    else:
        print("Scholar response contained no profile summary; preserving previous summary.")
    print(f"Updated {updated} citation counts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
