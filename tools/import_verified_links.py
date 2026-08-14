#!/usr/bin/env python3
"""Import verified paper and code URLs from the student-paper Excel workbook."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships"}


def column_index(cell_ref: str) -> int:
    value = 0
    for char in re.match(r"[A-Z]+", cell_ref).group(0):
        value = value * 26 + ord(char) - 64
    return value - 1


def title_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def citation_title(citation: str) -> str:
    match = re.search(r'["“]([^"”]+)["”]', citation)
    return match.group(1).strip() if match else ""


def load_rows(path: Path):
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", NS):
                shared.append("".join(item.itertext()))
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        for sheet in workbook.findall("a:sheets/a:sheet", NS):
            rid = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_targets[rid].lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            xml = ET.fromstring(book.read(target))
            sheet_rels_path = target.rsplit("/", 1)[0] + "/_rels/" + target.rsplit("/", 1)[1] + ".rels"
            hyperlinks = {}
            if sheet_rels_path in book.namelist():
                sheet_rels = ET.fromstring(book.read(sheet_rels_path))
                sheet_targets = {item.attrib["Id"]: item.attrib.get("Target", "") for item in sheet_rels}
                for link in xml.findall("a:hyperlinks/a:hyperlink", NS):
                    rid = link.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                    if rid and sheet_targets.get(rid):
                        hyperlinks[link.attrib["ref"]] = sheet_targets[rid]
            rows = []
            for row in xml.findall("a:sheetData/a:row", NS):
                values = {}
                for cell in row.findall("a:c", NS):
                    ref = cell.attrib["r"]
                    value_node = cell.find("a:v", NS)
                    value = "" if value_node is None else value_node.text or ""
                    if cell.attrib.get("t") == "s" and value:
                        value = shared[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(cell.itertext())
                    values[column_index(ref)] = value
                    if ref in hyperlinks:
                        values[(column_index(ref), "url")] = hyperlinks[ref]
                if values:
                    rows.append(values)
            yield sheet.attrib["name"], rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, required=True)
    parser.add_argument("--publications", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.publications.read_text(encoding="utf-8"))
    indexed = {title_key(citation_title(p.get("citation", ""))): p for p in payload["publications"]}
    updates, unmatched = [], []
    for sheet_name, rows in load_rows(args.xlsx):
        if sheet_name == "README" or not rows:
            continue
        header = next((row for row in rows if "Paper title" in row.values()), None)
        if not header:
            continue
        headers = {str(value).strip(): idx for idx, value in header.items() if isinstance(idx, int)}
        title_col, paper_col, code_col = headers.get("Paper title"), headers.get("Paper link"), headers.get("Code link")
        if title_col is None:
            continue
        for row in rows:
            title = str(row.get(title_col, "")).strip()
            if not title or title == "Paper title":
                continue
            paper = str(row.get((paper_col, "url"), row.get(paper_col, ""))).strip() if paper_col is not None else ""
            code = str(row.get((code_col, "url"), row.get(code_col, ""))).strip() if code_col is not None else ""
            paper = paper if paper.startswith(("https://", "http://")) else ""
            code = code if code.startswith(("https://", "http://")) else ""
            if not paper and not code:
                continue
            publication = indexed.get(title_key(title))
            if not publication:
                unmatched.append({"sheet": sheet_name, "title": title, "paper": paper, "code": code})
                continue
            changed = []
            if paper and publication.get("paper") != paper:
                publication["paper"] = paper
                publication["paperSource"] = "verified-excel"
                changed.append("paper")
            if code and publication.get("code") != code:
                publication["code"] = code
                publication["codeSource"] = "verified-excel"
                changed.append("code")
            if changed:
                updates.append({"sheet": sheet_name, "title": title, "changed": changed})
    report = {"updated": len(updates), "byField": Counter(item for update in updates for item in update["changed"]), "unmatched": unmatched, "updates": updates}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        args.publications.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"updated": report["updated"], "byField": report["byField"], "unmatched": len(unmatched)}, default=dict))


if __name__ == "__main__":
    main()
