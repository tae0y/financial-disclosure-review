"""Text blocks of the final render, joined to the LLM-facing html and measured."""

import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from bs4 import BeautifulSoup

from ...core.color import contrast_ratio
from ...core.text import html_lines, norm
from .measures import PX_TO_PT

ROW_TEXT_LIMIT = 120  # SnapshotIndex.row cuts a row's text here
MARKER = re.compile(r"^\s*(?:[※□■○●◦·•▶▷▪▫*-]|[①-⑳]|\(?\d{1,2}[.)]|[가-힣][.)])")
SENTENCE_END = re.compile(r"[.!?。](?:\s|$)")


def html_text_runs(html: str, longest: int = 3) -> set[str]:
    """Normalized text nodes of the html, plus runs of up to `longest` adjacent nodes joined by a
    space. A snapshot row's own text is one text node or a short run of them."""
    strings = [s for s in (norm(t) for t in BeautifulSoup(html, "html.parser").strings) if s]
    return {
        " ".join(strings[k : k + n]) for n in range(1, longest + 1) for k in range(len(strings))
    }


def compact_block(block: dict) -> str:
    flags = []
    if not block["ever_visible"]:
        flags.append("H")
    elif not block["default_visible"]:
        flags.append("D")
    if block["marker"]:
        flags.append("M")
    if block["own_line"]:
        flags.append("O")
    if block["line_sentences"] > 1:
        flags.append(f"S{block['line_sentences']}")
    pt = f"{block['pt']:.1f}pt" if block["pt"] is not None else "-"
    contrast = (
        "vision-readable"
        if block.get("vision_readable") is True
        else "vision-review"
        if block.get("vision_readable") is False
        else "vision-unknown"
        if block.get("visual_risk")
        else block["contrast"]
        if block["contrast"] is not None
        else "-"
    )
    return "|".join(
        [
            block["id"],
            block["text"][:70],
            pt,
            f"w{block['weight']}",
            str(block["color"]),
            "image-backed" if block.get("visual_risk") else str(block["background"]),
            f"cr{contrast}",
            "".join(flags),
        ]
    )


BLOCK_COLUMNS = "id|글자|크기|굵기|글자색|배경색|대비|flags"


def display_blocks(page: Mapping[str, Any]) -> tuple[list[dict], dict]:
    """Measured text blocks of the final render, joined to the LLM-facing html by text."""
    lines = html_lines(page.get("html") or "")
    runs = html_text_runs(page.get("html") or "")
    long_runs = [r for r in runs if len(r) >= ROW_TEXT_LIMIT - 2]
    groups: dict[str, list[dict]] = defaultdict(list)
    for snap in page.get("snapshots") or []:
        if snap.get("phase") == "render":
            groups[snap["url"]].append(snap)
    blocks: list[dict] = []
    stats: dict[str, float] = {
        "html_lines": len(lines),
        "rows": 0,
        "matched": 0,
        "duplicate_text": 0,
        "states": 0,
    }
    covered = set()
    for url, snaps in groups.items():
        first = max((i for i, s in enumerate(snaps) if s["kind"] == "default"), default=0)
        snaps = snaps[first:]
        stats["states"] += len(snaps)
        found: dict[str, dict] = {}
        for number, snap in enumerate(snaps):
            for row in snap["styles"]:
                text = norm(row["text"])
                if number == 0:
                    stats["rows"] += 1
                if len(text) < 2 or not (
                    text in runs
                    or (
                        len(text) >= ROW_TEXT_LIMIT - 2
                        and any(r.startswith(text) for r in long_runs)
                    )
                ):
                    continue
                entry = found.setdefault(
                    row["path"],
                    {
                        "url": url,
                        "row": row,
                        "default_visible": False,
                        "ever_visible": False,
                        "revealed_by": None,
                        "visual_png": None,
                    },
                )
                if number == 0:
                    entry["default_visible"] = row["visible"]
                if row["visible"]:
                    if not entry["ever_visible"] or number > entry.get("last", 0):
                        entry["row"], entry["last"] = row, number
                        entry["visual_png"] = (
                            snap.get("visual_samples", {}).get(row["path"]) or entry["visual_png"]
                        )
                    if not entry["default_visible"] and entry["revealed_by"] is None:
                        entry["revealed_by"] = snap["note"]
                    entry["ever_visible"] = True
        stats["matched"] += len(found)
        seen_text = set()
        for path, entry in found.items():
            row, text = entry["row"], norm(entry["row"]["text"])
            stats["duplicate_text"] += text in seen_text
            seen_text.add(text)
            covered.add(text)
            px = float(row["font_size"].removesuffix("px")) if row["font_size"] else None
            # Text set below 1px is not drawn at all — the usual image-replacement trick, where
            # the reader sees a picture of the words. Its computed size says nothing about what
            # is on screen, so it is kept out of the size measurements and treated like
            # image-backed text: unmeasured, never a pass and never a failure on its own.
            undrawn = px is not None and px < 1
            visual_risk = [*row.get("visual_risk", []), *(["undrawn_text"] if undrawn else [])]
            weight = int(float(row["font_weight"])) if row["font_weight"] else None
            line = next((candidate for candidate in lines if text in norm(candidate)), "")
            large = px is not None and (px >= 24 or (px >= 18.66 and (weight or 400) >= 700))
            blocks.append(
                {
                    "id": f"b{len(blocks) + 1}",
                    "url": url,
                    "path": path,
                    "text": row["text"],
                    "tag": row["tag"],
                    "px": px,
                    "pt": round(px * PX_TO_PT, 2) if px is not None and not undrawn else None,
                    "size_unmeasured": undrawn,
                    "weight": weight,
                    "color": row["color"],
                    "background": row["background"],
                    "background_source": row["background_source"],
                    "visual_risk": visual_risk,
                    "visual_png": entry["visual_png"],
                    "large_text": large,
                    "contrast": contrast_ratio(row["color"], row["background"]),
                    "bounds": row["bounds"],
                    "default_visible": entry["default_visible"],
                    "ever_visible": entry["ever_visible"],
                    "revealed_by": entry["revealed_by"],
                    "line_sentences": len(SENTENCE_END.findall(line)) or (1 if line else 0),
                    "marker": bool(MARKER.match(line)),
                    "own_line": norm(line) == text,
                }
            )
    reached = " ".join(covered)
    stats["text_coverage"] = round(
        sum(len(r) for r in runs if r in reached and " " not in r)
        / max(1, sum(len(r) for r in runs if " " not in r)),
        2,
    )
    return blocks, stats


def page_images(html: str | None) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    return [
        {"id": f"img{n}", "alt": img.get("alt") or ""}
        for n, img in enumerate(soup.find_all("img"), 1)
    ]
