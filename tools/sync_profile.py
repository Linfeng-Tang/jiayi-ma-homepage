#!/usr/bin/env python3
"""Synchronise the public biography, research interests, and activities page.

The Google Sites page remains the editorial source of truth.  This intentionally
copies text only: the local homepage retains its own accessible layout and does
not import remote HTML or scripts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = "https://sites.google.com/site/jiayima2013/jiayi-ma-%E9%A9%AC%E4%BD%B3%E4%B9%89-professor"


class TextBlocks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self.tag: str | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.tag is None and tag in {"h1", "h2", "h3", "p", "li"}:
            self.tag, self.parts = tag, []
        elif self.tag and tag == "br":
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag != self.tag:
            return
        text = re.sub(r"\s+", " ", "".join(self.parts)).strip()
        if text:
            self.blocks.append((tag, text))
        self.tag, self.parts = None, []

    def handle_data(self, data: str) -> None:
        if self.tag:
            self.parts.append(data)


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; JiayiMaHomepageBot/1.0)"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def label(text: str) -> str | None:
    plain = text.lower().strip().rstrip(":")
    if plain in {"short biography", "research interests", "academic activities"}:
        return plain
    return None


def extract(blocks: list[tuple[str, str]]) -> dict[str, list[str]]:
    sections = {"short biography": [], "research interests": [], "academic activities": []}
    active: str | None = None
    for tag, text in blocks:
        section = label(text)
        if section:
            active = section
            continue
        if tag in {"h1", "h2", "h3"}:
            active = None
        elif active and len(text) > 20:
            sections[active].append(text)
    return sections


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="res/profile.json")
    parser.add_argument("--url", default=SOURCE_URL)
    args = parser.parse_args()
    source = fetch(args.url)
    parser_ = TextBlocks()
    parser_.feed(source)
    sections = extract(parser_.blocks)
    if not all(sections.values()):
        raise RuntimeError("Could not extract all required profile sections; keeping the published profile unchanged.")
    output = {
        "source": args.url,
        "syncedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "bio": sections["short biography"],
        "research": sections["research interests"],
        "activities": sections["academic activities"],
    }
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synced Google Sites profile to {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Profile synchronisation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
