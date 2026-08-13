#!/usr/bin/env python3
"""Archive the official Wuhan University profile used for mentorship updates.

This is deliberately a source snapshot rather than an unverified text rewrite:
the university page is the authoritative record and its structure may change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://mvp.whu.edu.cn/info/1326/1662.htm"


class ProfileText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._content_depth = 0
        self._paragraph_depth = 0
        self._parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "div" and dict(attrs).get("id") == "vsb_content":
            self._content_depth = 1
            return
        if self._content_depth:
            if tag == "div":
                self._content_depth += 1
            if tag in {"p", "li", "h1", "h2", "h3"}:
                self._paragraph_depth += 1
            if tag == "br":
                self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._content_depth:
            return
        if tag in {"p", "li", "h1", "h2", "h3"} and self._paragraph_depth:
            self._paragraph_depth -= 1
            text = " ".join("".join(self._parts).split())
            if text:
                self.paragraphs.append(text)
            self._parts = []
        if tag == "div":
            self._content_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._content_depth:
            self._parts.append(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", errors="replace")
    extractor = ProfileText()
    extractor.feed(html)
    if len(extractor.paragraphs) < 10:
        raise RuntimeError("Official profile structure changed; source snapshot was not replaced.")
    payload = {
        "source": SOURCE_URL,
        "syncedAt": datetime.now(timezone.utc).isoformat(),
        "contentHash": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "paragraphs": extractor.paragraphs,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
