#!/usr/bin/env python3
"""Synchronise the publication list from Jiayi Ma's public Google Sites page.

The generated JSON is deliberately kept separate from the layout so the webpage
can remain a static GitHub Pages site while its publication data is refreshed by
GitHub Actions.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = (
    "https://sites.google.com/site/jiayima2013/"
    "jiayi-ma-%E9%A9%AC%E4%BD%B3%E4%B9%89-professor/publications"
)
SELECTED_SOURCE_URL = "https://sites.google.com/site/jiayima2013/jiayi-ma-%E9%A9%AC%E4%BD%B3%E4%B9%89-professor"


class PublicationPageParser(HTMLParser):
    """Extract individual Google Sites list items and year paragraphs."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[dict] = []
        self._capture_tag: str | None = None
        self._parts: list[str] = []
        self._links: list[dict[str, str]] = []
        self._active_link: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag in {"li", "p"} and self._capture_tag is None:
            self._capture_tag = tag
            self._parts = []
            self._links = []
            return
        if self._capture_tag:
            if tag == "a" and attr.get("href"):
                self._active_link = attr["href"]
                self._link_text = []
            elif tag == "br":
                self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if not self._capture_tag:
            return
        if tag == "a" and self._active_link:
            label = "".join(self._link_text).strip()
            if label:
                self._links.append({"label": label, "url": self._active_link})
            self._active_link = None
            self._link_text = []
        if tag == self._capture_tag:
            text = re.sub(r"\s+", " ", "".join(self._parts)).strip()
            if text:
                self.blocks.append({"text": html.unescape(text), "links": self._links})
            self._capture_tag = None

    def handle_data(self, data: str) -> None:
        if self._capture_tag:
            self._parts.append(data)
            if self._active_link:
                self._link_text.append(data)


class SelectedPublicationParser(HTMLParser):
    """Extract the ordered papers beneath the homepage's Selected Publications heading."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.selected_titles: list[str] = []
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._capture_li_depth = 0
        self._li_parts: list[str] = []
        self._selected_section = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._heading_parts = []
        elif self._selected_section and tag == "li":
            self._capture_li_depth += 1
        elif self._capture_li_depth and tag == "br":
            self._li_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == self._heading_tag:
            heading = re.sub(r"\s+", " ", "".join(self._heading_parts)).strip().lower()
            self._selected_section = "selected publication" in heading or "selected paper" in heading
            self._heading_tag = None
            self._heading_parts = []
        elif self._selected_section and tag == "li" and self._capture_li_depth:
            self._capture_li_depth -= 1
            if not self._capture_li_depth:
                text = re.sub(r"\s+", " ", "".join(self._li_parts)).strip()
                match = re.search(r'["“]([^"”]+)["”]', text)
                if match:
                    self.selected_titles.append(match.group(1).strip())
                self._li_parts = []

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading_parts.append(data)
        if self._capture_li_depth:
            self._li_parts.append(data)


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "JiayiMaHomepageBot/1.0 (+GitHub Pages)"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", errors="replace")


def classify_blocks(blocks: list[dict]) -> list[dict]:
    """Turn the source's visual blocks into year-grouped publication records."""
    publications: list[dict] = []
    year: str | None = None
    seen: set[str] = set()
    for block in blocks:
        text = block["text"]
        compact = re.sub(r"\s+", " ", text).strip()
        year_match = re.fullmatch(r"20\s?(\d{2})", compact)
        if year_match:
            year = f"20{year_match.group(1)}"
            continue
        # Publication entries always contain a quoted title; this prevents
        # navigation, sidebar copy, and explanatory text from entering the list.
        if not year or '"' not in compact or len(compact) < 45:
            continue
        key = re.sub(r"\W+", "", compact).lower()
        if key in seen:
            continue
        seen.add(key)
        publications.append({"year": year, "citation": compact, "links": block["links"]})
    return publications


def selected_titles_from_homepage(source: str) -> list[str]:
    parser = SelectedPublicationParser()
    parser.feed(source)
    titles: list[str] = []
    seen: set[str] = set()
    for title in parser.selected_titles:
        key = re.sub(r"\W+", "", title).lower()
        if key and key not in seen:
            titles.append(title)
            seen.add(key)
    if len(titles) < 5:
        raise RuntimeError(f"Only extracted {len(titles)} selected publications; homepage structure may have changed.")
    return titles


def publication_key(publication: dict) -> str | None:
    """Create a stable identity from the quoted title for enrichment reuse."""
    match = re.search(r'"(.+?)"', publication.get("citation", ""))
    if not match:
        return None
    return re.sub(r"\W+", "", match.group(1)).lower()


def retain_verified_metadata(publications: list[dict], destination: Path) -> None:
    """Keep previously verified links/counts through a source refresh.

    The source page is authoritative for bibliographic text, but it does not
    contain every publisher URL, GitHub repository, or Scholar count found by
    the scheduled enrichment steps.  Those fields are retained by exact title.
    """
    if not destination.exists():
        return
    try:
        previous = json.loads(destination.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    prior: dict[str, dict] = {}
    for item in previous.get("publications", []):
        key = publication_key(item)
        if key:
            prior[key] = item
    retained_fields = ("paper", "paperSource", "code", "codeSource", "citations", "esiHighlyCited", "esiHot")
    for publication in publications:
        old = prior.get(publication_key(publication))
        if not old:
            continue
        for field in retained_fields:
            if field in old:
                publication[field] = old[field]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="docs/data/publications.json")
    parser.add_argument("--url", default=SOURCE_URL)
    args = parser.parse_args()

    source = fetch(args.url)
    selected_titles = selected_titles_from_homepage(fetch(SELECTED_SOURCE_URL))
    extractor = PublicationPageParser()
    extractor.feed(source)
    publications = classify_blocks(extractor.blocks)
    if len(publications) < 30:
        raise RuntimeError(
            f"Only extracted {len(publications)} records; source structure may have changed."
        )
    output = {
        "source": args.url,
        "selectedSource": SELECTED_SOURCE_URL,
        "syncedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "selectedTitles": selected_titles,
        "publications": publications,
    }
    destination = Path(args.out)
    retain_verified_metadata(publications, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Synced {len(publications)} publications to {destination}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Publication synchronisation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
