#!/usr/bin/env python3
"""Apply ESI Highly Cited / Hot Paper labels from curator-supplied lists."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HOT_TITLES = [
    "Deep Learning-based Face Super-resolution: A Survey",
    "DIVFusion: Darkness-free infrared and visible image fusion",
    "Rethinking the necessity of image fusion in high-level vision tasks: A practical infrared and visible image fusion network based on progressive semantic injection and scene fidelity",
    "Image fusion in the loop of high-level vision tasks: A semantic-aware real-time infrared and visible image fusion network",
    "SwinFusion: Cross-domain Long-range Learning for General Image Fusion via Swin Transformer",
    "PIAFusion: A progressive infrared and visible image fusion network based on illumination aware",
    "U2Fusion: A Unified Unsupervised Image Fusion Network",
    "SuperFusion: A Versatile Image Registration and Fusion Network with Semantic Awareness",
    "A review of multimodal image matching: Methods and applications",
    "Image Matching from Handcrafted to Deep Features: A Survey",
    "Image fusion meets deep learning: A survey and perspective",
    "Multi-Temporal Ultra Dense Memory Network for Video Super-Resolution",
    "Locality Preserving Matching",
    "FusionGAN: A generative adversarial network for infrared and visible image fusion",
    "Infrared and visible image fusion methods and applications: A survey",
    "Large-Scale Remote Sensing Image Retrieval by Deep Hashing Neural Networks",
    "Guided Locality Preserving Feature Matching for Remote Sensing Image Registration",
    "Facial Image Hallucination Through Coupled-Layer Neighbor Embedding",
    "Non-Rigid Point Set Registration by Preserving Global and Local Structures",
    "Infrared and visible image fusion via gradient transfer and total variation minimization",
    "Non-rigid visible and infrared face registration via regularized Gaussian fields criterion",
    "Robust L2E Estimation of Transformation for Non-Rigid Registration",
    "Robust Feature Matching for Remote Sensing Image Registration via Locally Linear Transforming",
]


def norm(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).lower().replace("plus", "+")
    return re.sub(r"[^a-z0-9]+", "", value)


def title(citation: str) -> str:
    match = re.search(r'["“]([^"”]+)["”]', citation)
    return match.group(1) if match else ""


def matching_titles(records: list[dict], source_text: str) -> set[str]:
    compact = norm(source_text)
    return {norm(title(record.get("citation", ""))) for record in records if norm(title(record.get("citation", ""))) in compact}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--high-list", type=Path, required=True)
    parser.add_argument("--publications", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.publications.read_text(encoding="utf-8"))
    papers = data["publications"]
    high = matching_titles(papers, args.high_list.read_text(encoding="utf-8"))
    hot = {norm(item) for item in HOT_TITLES}
    # When a conference paper and its later journal extension share a title,
    # expose only the newest formal publication for a single ESI record.
    newest_by_title: dict[str, dict] = {}
    for paper in papers:
        key = norm(title(paper.get("citation", "")))
        if key and (key not in newest_by_title or str(paper.get("year", "")) > str(newest_by_title[key].get("year", ""))):
            newest_by_title[key] = paper
    high_papers = {id(newest_by_title[key]) for key in high if key in newest_by_title}
    hot_papers = {id(newest_by_title[key]) for key in hot if key in newest_by_title}
    labeled = {"high": [], "hot": [], "both": []}
    for paper in papers:
        is_high = id(paper) in high_papers
        is_hot = id(paper) in hot_papers
        if is_high:
            paper["esiHighlyCited"] = True
            labeled["high"].append(title(paper["citation"]))
        else:
            paper.pop("esiHighlyCited", None)
        if is_hot:
            paper["esiHot"] = True
            labeled["hot"].append(title(paper["citation"]))
        else:
            paper.pop("esiHot", None)
        if is_high and is_hot:
            labeled["both"].append(title(paper["citation"]))
    args.publications.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {"highlyCitedCount": len(labeled["high"]), "hotCount": len(labeled["hot"]), "bothCount": len(labeled["both"]), "titles": labeled}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("highlyCitedCount", "hotCount", "bothCount")}))


if __name__ == "__main__":
    main()
