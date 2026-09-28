"""display-flip: mutates a disclosure below threshold; pipeline/rules must catch it, not control."""

import copy
import json
import re
from pathlib import Path
from typing import Any

from ..core.context import Context
from ..core.text import norm
from ..domain.display_check import judge_display
from ..domain.display_check.blocks import display_blocks
from ..domain.display_check.measures import CONTRAST_MIN, CONTRAST_MIN_LARGE
from ..knowledge.rubrics import load_rubric
from .cassette import Cassette

WATCHED = ("E02", "E04")


def mutate(page: dict, text: str, change: dict[str, str]) -> tuple[dict, int]:
    """A copy of the page whose `text` rows carry `change`; also returns the rows-changed count."""
    variant = copy.deepcopy(page)
    target, changed = norm(text), 0
    for snapshot in variant["snapshots"]:
        for row in snapshot.get("styles") or []:
            if norm(row.get("text", "")) == target:
                row.update(change)
                changed += 1
    return variant, changed


def _min_pt(ctx: Context) -> float:
    """The size threshold as judge_display reads it: the number before 포인트 in E02."""
    e02 = next(i for i in load_rubric(ctx.db_path, "card_guardrail_rubric") if i["code"] == "E02")
    match = re.search(r"(\d+)\s*포인트", e02["criterion"])
    return float(match.group(1)) if match else 8.0


def rules_verdicts(page: dict, ctx: Context) -> dict[str, dict]:
    """Code alone: any visible block under the threshold fails the item, whatever the text is."""
    blocks, _ = display_blocks(page)
    visible = [b for b in blocks if b["ever_visible"]]
    small = [b["id"] for b in visible if b["pt"] is not None and b["pt"] < _min_pt(ctx)]
    faint = [
        b["id"]
        for b in visible
        if not b.get("visual_risk")
        and b["contrast"] is not None
        and b["contrast"] < (CONTRAST_MIN_LARGE if b["large_text"] else CONTRAST_MIN)
    ]
    return {
        "E02": {"verdict": "부적합" if small else "적합", "block_ids": small},
        "E04": {"verdict": "부적합" if faint else "적합", "block_ids": faint},
    }


def pipeline_verdicts(page: dict, classification: dict, ctx: Context, cassette: Cassette) -> dict:
    result = judge_display(page, classification, ctx, ask_fn=cassette.ask)
    return {
        row["code"]: {"verdict": row["verdict"], "block_ids": row["block_ids"]}
        for row in result["items"]
    }


def _block_of(page: dict, text: str) -> str | None:
    blocks, _ = display_blocks(page)
    target = norm(text)
    return next((b["id"] for b in blocks if norm(b["text"]) == target), None)


def run_display_flip(
    ctx: Context, cassette: Cassette, config: dict, root: Path, arm: str = "pipeline"
) -> dict:
    rows, bases = [], []
    for spec in config["pages"]:
        fixture = json.loads((root / spec["fixture"]).read_text(encoding="utf-8"))
        page, classification, watch = fixture["page"], fixture["classification"], spec["watch"]

        def judge(p: dict) -> dict:
            if arm == "rules":
                return rules_verdicts(p, ctx)
            return pipeline_verdicts(p, classification, ctx, cassette)

        base = judge(page)
        bases.append(
            {
                "page": spec["id"],
                "url": page["url"],
                "watch": watch,
                "verdict": (base.get(watch) or {}).get("verdict"),
                "block_ids": (base.get(watch) or {}).get("block_ids", []),
                "all": {code: row["verdict"] for code, row in sorted(base.items())},
            }
        )
        for case in spec["cases"]:
            change = config["mutations"][case["kind"]]
            variant, changed = mutate(page, case["text"], change)
            block = _block_of(variant, case["text"])
            row: dict[str, Any] = {
                "case": f"{spec['id']}/{case['id']}",
                "kind": "대조군" if case["rubric"] is None else "결함 주입",
                "rubric": case["rubric"],
                "watch": watch,
                "block": block,
                "landed": bool(changed and block),
                "base_verdict": bases[-1]["verdict"],
            }
            if not row["landed"]:
                row.update(after_verdict=None, cited=None, note="대상 블록을 찾지 못해 제외")
                rows.append(row)
                continue
            after = judge(variant).get(watch) or {}
            cited = block in (after.get("block_ids") or [])
            row.update(
                after_verdict=after.get("verdict"),
                cited=cited,
                # Detection: the item fails and names the block that was made non-compliant.
                # Blame on a control: the item fails because of the block that is not mandatory.
                detected=(after.get("verdict") == "부적합" and cited) if case["rubric"] else None,
                blamed_control=(after.get("verdict") == "부적합" and cited)
                if case["rubric"] is None
                else None,
                note="",
            )
            rows.append(row)
    return {"suite": f"display-flip/{arm}", "arm": arm, "bases": bases, "rows": rows}
